#!/usr/bin/env python3
"""High-throughput, rate-limit-respecting Roblox username network helpers."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter

BULK_URL = "https://users.roblox.com/v1/usernames/users"
BULK_BATCH_SIZE = 100
POOL_SIZE = 64
BULK_INITIAL_CONCURRENCY = 4
BULK_MAX_CONCURRENCY = 8

_session = requests.Session()
_adapter = HTTPAdapter(
    pool_connections=POOL_SIZE,
    pool_maxsize=POOL_SIZE,
    max_retries=0,
    pool_block=False,
)
_session.mount("https://", _adapter)
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
)


@dataclass
class BulkLookupResult:
    requested: list[str]
    existing: set[str]
    ok: bool
    status_code: int = 0
    elapsed: float = 0.0
    retry_after: float | None = None
    rate_limit: int | None = None
    rate_remaining: int | None = None
    rate_reset: float | None = None
    error: str = ""


def chunks(values: Iterable[str], size: int = BULK_BATCH_SIZE):
    batch = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _number_header(headers, name, cast=float):
    raw = headers.get(name)
    if raw is None:
        return None
    try:
        # Some Roblox rate-limit headers can expose comma-separated windows.
        token = str(raw).split(",", 1)[0].split(";", 1)[0].strip()
        return cast(float(token))
    except (TypeError, ValueError):
        return None


def bulk_existing(usernames, timeout=(3.05, 8.0)):
    """Return usernames that already resolve to Roblox users.

    This is a first-stage existence lookup only. Names not returned by this
    endpoint still need signup validation because they can be available,
    inappropriate, reserved, or otherwise invalid.
    """
    requested = list(dict.fromkeys(str(n).strip().lower() for n in usernames if n))
    if not requested:
        return BulkLookupResult([], set(), True)

    if len(requested) > BULK_BATCH_SIZE:
        raise ValueError(f"bulk_existing accepts at most {BULK_BATCH_SIZE} usernames")

    started = time.perf_counter()
    try:
        response = _session.post(
            BULK_URL,
            json={"usernames": requested, "excludeBannedUsers": False},
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        headers = response.headers

        common = dict(
            requested=requested,
            status_code=response.status_code,
            elapsed=elapsed,
            retry_after=_number_header(headers, "retry-after"),
            rate_limit=_number_header(headers, "x-ratelimit-limit", int),
            rate_remaining=_number_header(headers, "x-ratelimit-remaining", int),
            rate_reset=_number_header(headers, "x-ratelimit-reset"),
        )

        if response.status_code != 200:
            return BulkLookupResult(
                existing=set(),
                ok=False,
                error=f"http_{response.status_code}",
                **common,
            )

        payload = response.json()
        existing = set()
        requested_set = set(requested)

        for item in payload.get("data", []):
            requested_name = str(item.get("requestedUsername") or "").lower()
            canonical_name = str(item.get("name") or "").lower()

            if requested_name in requested_set:
                existing.add(requested_name)
            elif canonical_name in requested_set:
                # Compatibility fallback for responses that omit requestedUsername.
                existing.add(canonical_name)

        return BulkLookupResult(existing=existing, ok=True, **common)

    except requests.RequestException as exc:
        return BulkLookupResult(
            requested=requested,
            existing=set(),
            ok=False,
            elapsed=time.perf_counter() - started,
            error=f"error({exc})",
        )
    except (ValueError, TypeError) as exc:
        return BulkLookupResult(
            requested=requested,
            existing=set(),
            ok=False,
            elapsed=time.perf_counter() - started,
            error=f"decode_error({exc})",
        )



class BulkConcurrencyController:
    """AIMD controller for official bulk lookups.

    It increases concurrency after healthy rounds and halves it on 429.
    Rate-limit headers are used to avoid launching another full round when
    the server reports that the current quota is exhausted.
    """

    def __init__(self, workers=BULK_INITIAL_CONCURRENCY, minimum=1, maximum=BULK_MAX_CONCURRENCY):
        self.minimum = minimum
        self.maximum = maximum
        self.workers = max(minimum, min(maximum, int(workers)))
        self.healthy_streak = 0

    def observe(self, results):
        results = list(results)
        if not results:
            return self.workers

        if any(r.status_code == 429 for r in results):
            self.workers = max(self.minimum, max(1, self.workers // 2))
            self.healthy_streak = 0
            return self.workers

        if any(not r.ok for r in results):
            self.workers = max(self.minimum, self.workers - 1)
            self.healthy_streak = 0
            return self.workers

        self.healthy_streak += 1
        if self.healthy_streak >= 2:
            self.workers = min(self.maximum, self.workers + 1)
            self.healthy_streak = 0
        return self.workers

    @staticmethod
    def cooldown_seconds(results):
        waits = []
        for result in results:
            if result.status_code == 429:
                if result.retry_after is not None:
                    waits.append(float(result.retry_after))
                elif result.rate_reset is not None:
                    waits.append(float(result.rate_reset))
            elif result.rate_remaining == 0 and result.rate_reset is not None:
                waits.append(float(result.rate_reset))
        if not waits:
            return 0.0
        return min(60.0, max(0.0, max(waits)))


class BulkScheduler:
    """Persistent bulk worker pool for an entire scan session."""

    def __init__(self, controller=None):
        self.controller = controller or BulkConcurrencyController()
        self.executor = ThreadPoolExecutor(max_workers=self.controller.maximum)
        self.closed = False
        self.submitted_requests = 0

    def iter_lookup_many(self, usernames):
        """Yield bulk results as soon as each request completes.

        This lets the scanner validate survivors from the first completed
        batch while sibling bulk requests are still in flight.
        """
        batches = list(chunks(usernames))
        offset = 0

        while offset < len(batches):
            round_size = self.controller.workers
            round_batches = batches[offset:offset + round_size]
            offset += len(round_batches)

            futures = [
                self.executor.submit(bulk_existing, batch)
                for batch in round_batches
            ]
            self.submitted_requests += len(futures)
            round_results = []

            try:
                for future in as_completed(futures):
                    result = future.result()
                    round_results.append(result)
                    yield result
            finally:
                # If the caller reached its target and closes this generator,
                # avoid starting any queued work that has not begun yet.
                for future in futures:
                    if not future.done():
                        future.cancel()

            self.controller.observe(round_results)
            cooldown = self.controller.cooldown_seconds(round_results)
            if cooldown > 0:
                time.sleep(cooldown)

    def lookup_many(self, usernames):
        return list(self.iter_lookup_many(usernames))

    def close(self):
        if not self.closed:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def bulk_existing_many(usernames, controller=None):
    """Compatibility helper using a temporary scheduler."""
    scheduler = BulkScheduler(controller)
    try:
        return scheduler.lookup_many(usernames), scheduler.controller
    finally:
        scheduler.close()

def tune_requests_session(session, pool_size=POOL_SIZE):
    """Increase requests/urllib3 connection pools for concurrent validators."""
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=0,
        pool_block=False,
    )
    session.mount("https://", adapter)
    return session
