#!/usr/bin/env python3
"""High-throughput, rate-limit-respecting Roblox username network helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter

BULK_URL = "https://users.roblox.com/v1/usernames/users"
BULK_BATCH_SIZE = 100
POOL_SIZE = 64

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
