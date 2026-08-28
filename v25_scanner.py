#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.5 advanced scanner UI."""
from __future__ import annotations

import os
import shutil
import sys
import time
import webbrowser
from collections import Counter, deque
from pathlib import Path

import requests

import roblox_name_gen as base
import v25_engine as eng
import v25_fastnet as fastnet
import v25_launcher as accounts

APP_VER = "2.5"
base.APP_VER = APP_VER
accounts.APP_VER = APP_VER

_recent_available = deque(maxlen=6)
_last_dashboard_at = 0.0
DASHBOARD_INTERVAL = 0.25
TURBO_CANDIDATE_BATCH = fastnet.BULK_BATCH_SIZE
TURBO_WINDOW_SIZE = 1000
CHECKPOINT_INTERVAL = 2.0
CHECKPOINT_EVERY = 5000

# The legacy validator uses requests.Session. Its default pool is only 10,
# which becomes a hidden bottleneck once adaptive concurrency climbs higher.
fastnet.tune_requests_session(base.SESH)


def yesno(prompt, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    value = input(prompt + suffix).strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def choose_charset_mode():
    print("Charset: [L] letters  [M] letters+digits  [N] numbers  [U] letters+digits+underscore")
    choice = input("Choose [M]: ").strip().lower()
    return choice if choice in {"l", "n", "u"} else "m"


def charset_for(mode, filters):
    if mode == "l":
        chars = base.LETTERS
    elif mode == "n":
        chars = base.NUMBERS_ONLY
    elif mode == "u":
        chars = base.CHARSET + "_"
    else:
        chars = base.CHARSET
    if not filters.allow_digits:
        chars = "".join(c for c in chars if not c.isdigit())
    if not filters.allow_underscores:
        chars = chars.replace("_", "")
    return chars or base.LETTERS



def build_unique_generator(length, chars, filters, resume_state=None):
    """Build a duplicate-free normal-scan generator.

    Cheap structural constraints are encoded directly into per-position
    alphabets so invalid shapes never enter the scan pipeline.
    """
    if resume_state:
        return eng.UniqueSpaceGenerator.from_snapshot(resume_state)

    first = chars
    if filters.must_start_letter:
        first = "".join(c for c in chars if c.isalpha()) or base.LETTERS

    middle = chars
    last = chars

    # Roblox usernames cannot use a leading/trailing underscore in normal
    # signup validation, so avoid generating those shapes entirely.
    first = first.replace("_", "")
    last = last.replace("_", "")

    alphabets = [first]
    if length > 2:
        alphabets.extend([middle] * (length - 2))
    if length > 1:
        alphabets.append(last)
    return eng.UniqueSpaceGenerator(alphabets)

def configure_filters(seed=None):
    cfg = eng.FilterConfig.from_dict(seed)
    print("\nAdvanced filters (Enter keeps the shown default)")
    cfg.allow_digits = yesno("Allow digits?", cfg.allow_digits)
    cfg.allow_underscores = yesno("Allow underscores?", cfg.allow_underscores)
    if cfg.allow_digits:
        raw = input(f"Max digits [{cfg.max_digits if cfg.max_digits < 99 else 'any'}]: ").strip()
        if raw.isdigit():
            cfg.max_digits = max(0, int(raw))
    else:
        cfg.max_digits = 0
    cfg.must_start_letter = yesno("Must start with a letter?", cfg.must_start_letter)
    cfg.must_contain_vowel = yesno("Must contain a vowel?", cfg.must_contain_vowel)
    cfg.avoid_repeats = yesno("Avoid adjacent repeated characters?", cfg.avoid_repeats)
    return cfg


def dashboard(stats, adaptive, target, found, mode, current="", cache_note="", force=False):
    global _last_dashboard_at
    now = time.perf_counter()
    if not force and now - _last_dashboard_at < DASHBOARD_INTERVAL:
        return
    _last_dashboard_at = now
    elapsed = eng.format_duration(stats.elapsed)
    line = (
        f"[{mode}] checked:{stats.checked}  available:{stats.available}  taken:{stats.taken}  "
        f"inappropriate:{stats.inappropriate}  other:{stats.other}  cache:{stats.cache_hits}  "
        f"http:{stats.http_requests}  bulk:{stats.bulk_requests}  validators:{stats.individual_validations}  "
        f"workers:{adaptive.workers}  speed:{stats.speed:.1f}/s  time:{elapsed}  target:{len(found)}/{target}"
    )
    if current:
        line += f"  | {current}"
    if cache_note:
        line += f" {cache_note}"
    sys.stdout.write("\r" + " " * 175 + "\r" + line[:174])
    sys.stdout.flush()

def print_available_live(name):
    _recent_available.appendleft(name)
    sys.stdout.write("\r" + " " * 155 + "\r")
    score = eng.score_username(name)
    print(f"  >>> AVAILABLE  {name:<12} score {score:>3}/100 {eng.score_label(score)}")


def generate_unique(count, generator, filters, banned, seen=None, source_unique=False):
    out = []
    attempts = 0
    max_attempts = max(200, count * 80)
    if seen is None:
        seen = set()
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            name = generator().lower()
        except StopIteration:
            break
        if not source_unique:
            if name in seen:
                continue
            seen.add(name)
        if eng.passes_filters(name, filters, banned):
            out.append(name)
    return out


def check_candidates(
    candidates,
    store,
    stats,
    adaptive,
    mode,
    target=None,
    found=None,
    stop_after_available=None,
    bulk_controller=None,
    bulk_scheduler=None,
    validator_executor=None,
    collect_rows=True,
    candidates_unique=False,
):
    """Pipeline cache -> streaming bulk lookup -> immediate survivor validation."""
    results = []
    found = found if found is not None else []
    bulk_controller = bulk_controller or fastnet.BulkConcurrencyController()

    owns_bulk_scheduler = bulk_scheduler is None
    scheduler = bulk_scheduler or fastnet.BulkScheduler(bulk_controller)
    bulk_controller = scheduler.controller

    if candidates_unique:
        candidates = [name.lower() for name in candidates]
    else:
        candidates = list(dict.fromkeys(name.lower() for name in candidates))
    if not candidates:
        if owns_bulk_scheduler:
            scheduler.close()
        return results

    cached_map = store.cached_status_many(candidates)
    uncached = [name for name in candidates if name not in cached_map]

    if cached_map:
        counts = Counter(cached_map.values())
        stats.checked += len(cached_map)
        stats.cache_hits += len(cached_map)
        stats.available += counts.get("available", 0)
        stats.taken += counts.get("taken", 0)
        stats.inappropriate += counts.get("inappropriate", 0)
        stats.other += (
            len(cached_map)
            - counts.get("available", 0)
            - counts.get("taken", 0)
            - counts.get("inappropriate", 0)
        )

        for name, cached in cached_map.items():
            if collect_rows:
                score = eng.score_username(name) if cached == "available" else 0
                results.append(
                    {
                        "username": name,
                        "status": cached,
                        "score": score,
                        "length": len(name),
                        "checked_at": eng.utc_iso(),
                    }
                )
            if cached == "available" and name not in found:
                found.append(name)
                print_available_live(name)

        dashboard(
            stats,
            adaptive,
            target or len(candidates),
            found,
            mode,
            f"{len(cached_map)} cache hits",
            "[one DB query]",
            force=True,
        )

    if stop_after_available is not None and len(found) >= stop_after_available:
        if owns_bulk_scheduler:
            scheduler.close(wait=False)
        return results
    if not uncached:
        if owns_bulk_scheduler:
            scheduler.close()
        return results

    owns_validator_executor = validator_executor is None
    executor = validator_executor or base.ThreadPoolExecutor(max_workers=adaptive.maximum)

    pending_records = []
    validation_records = []
    bulk_status_signals = []
    bulk_taken_total = 0
    bulk_survivor_total = 0

    def validate_names(names):
        """Validate one bulk result's survivors immediately."""
        nonlocal validation_records
        offset = 0

        while offset < len(names):
            if stop_after_available is not None and len(found) >= stop_after_available:
                return True

            wave_size = min(adaptive.workers, len(names) - offset)
            wave = names[offset:offset + wave_size]
            offset += wave_size

            futures = {executor.submit(base.smart_check, name): name for name in wave}
            wave_statuses = []

            for future in base.as_completed(futures):
                name = futures[future]
                try:
                    _, status = future.result()
                except Exception as exc:
                    status = f"error({exc})"

                stats.http_requests += 1
                stats.individual_validations += 1
                stats.record(status, cached=False)
                wave_statuses.append(status)

                score = eng.score_username(name) if status == "available" else 0
                validation_records.append((name, status, score, mode))

                if collect_rows:
                    results.append(
                        {
                            "username": name,
                            "status": status,
                            "score": score,
                            "length": len(name),
                            "checked_at": eng.utc_iso(),
                        }
                    )

                if status == "available" and name not in found:
                    found.append(name)
                    print_available_live(name)

                dashboard(
                    stats,
                    adaptive,
                    target or len(candidates),
                    found,
                    mode,
                    name,
                )

            before = adaptive.workers
            adaptive.observe(wave_statuses + bulk_status_signals)

            if "ratelimited" in wave_statuses:
                print("\n  Signup validator rate-limited. Cooling down before continuing.")
                time.sleep(2.0)
            elif adaptive.workers < before:
                time.sleep(0.15)

        return stop_after_available is not None and len(found) >= stop_after_available

    submitted_before = scheduler.submitted_requests
    submitted_accounted = submitted_before
    lookup_iter = scheduler.iter_lookup_many(uncached)

    try:
        for lookup in lookup_iter:
            # iter_lookup_many submits a whole concurrency round before yielding
            # its first result. Count every launched request, including siblings
            # that are still in flight while this result is being validated.
            if scheduler.submitted_requests > submitted_accounted:
                launched = scheduler.submitted_requests - submitted_accounted
                stats.bulk_requests += launched
                stats.http_requests += launched
                submitted_accounted = scheduler.submitted_requests

            chunk = lookup.requested

            if lookup.ok:
                existing = lookup.existing
                taken_count = len(existing)

                if taken_count:
                    stats.checked += taken_count
                    stats.network_checks += taken_count
                    stats.taken += taken_count
                    stats.bulk_resolved += taken_count
                    pending_records.extend((name, "taken", 0, mode) for name in existing)

                    if collect_rows:
                        checked_at = eng.utc_iso()
                        results.extend(
                            {
                                "username": name,
                                "status": "taken",
                                "score": 0,
                                "length": len(name),
                                "checked_at": checked_at,
                            }
                            for name in existing
                        )

                survivors = [name for name in chunk if name not in existing]
                bulk_taken_total += taken_count
                bulk_survivor_total += len(survivors)

            else:
                # Bulk failures fall through to the signup validator so the
                # result remains correct. The bulk scheduler itself handles
                # server-directed cooldown before launching another round.
                survivors = list(chunk)
                bulk_status_signals.append(
                    "ratelimited"
                    if lookup.status_code == 429
                    else (lookup.error or "bulk_error")
                )

            # Critical latency optimization: do not wait for sibling bulk
            # requests. They continue in the bulk executor while these
            # survivors are validated right now.
            if survivors and validate_names(survivors):
                break

    finally:
        # Closing the generator cancels bulk futures that have not started.
        try:
            lookup_iter.close()
        except Exception:
            pass

        if scheduler.submitted_requests > submitted_accounted:
            launched = scheduler.submitted_requests - submitted_accounted
            stats.bulk_requests += launched
            stats.http_requests += launched

        if owns_validator_executor:
            executor.shutdown(wait=True, cancel_futures=True)

        if owns_bulk_scheduler:
            scheduler.close(
                wait=not (
                    stop_after_available is not None
                    and len(found) >= stop_after_available
                )
            )

    all_records = pending_records + validation_records
    if all_records:
        store.record_many(all_records)

    dashboard(
        stats,
        adaptive,
        target or len(candidates),
        found,
        mode,
        f"pipeline: {bulk_taken_total} bulk-taken / {bulk_survivor_total} survivors",
        f"[bulk x{bulk_controller.workers}]",
        force=True,
    )
    return results

def checkpoint_payload(
    mode,
    length,
    target,
    max_checks,
    found,
    stats,
    filters,
    charset_mode,
    aesthetic,
    generator_state=None,
):
    return {
        "mode": mode,
        "length": length,
        "target": target,
        "max_checks": max_checks,
        "found": list(found),
        "checked": stats.checked,
        "network_checks": stats.network_checks,
        "cache_hits": stats.cache_hits,
        "available": stats.available,
        "taken": stats.taken,
        "inappropriate": stats.inappropriate,
        "other": stats.other,
        "http_requests": stats.http_requests,
        "bulk_requests": stats.bulk_requests,
        "bulk_resolved": stats.bulk_resolved,
        "individual_validations": stats.individual_validations,
        "elapsed": stats.elapsed,
        "filters": vars(filters),
        "charset_mode": charset_mode,
        "aesthetic": bool(aesthetic),
        "generator_state": generator_state,
    }

def run_target_scan(length, target, max_checks, filters, charset_mode="m", aesthetic=False, resume=None, label="scan"):
    store = eng.HistoryStore()
    banned = eng.load_banned_patterns()
    adaptive = eng.AdaptiveWorkers()
    bulk_controller = fastnet.BulkConcurrencyController()
    bulk_scheduler = fastnet.BulkScheduler(bulk_controller)
    validator_executor = base.ThreadPoolExecutor(max_workers=adaptive.maximum)
    resume = resume or {}

    stats = eng.ScanStats(time.time() - float(resume.get("elapsed", 0)))
    found = list(resume.get("found", []))
    stats.checked = int(resume.get("checked", 0))
    stats.network_checks = int(resume.get("network_checks", 0))
    stats.cache_hits = int(resume.get("cache_hits", 0))
    stats.available = int(resume.get("available", len(found)))
    stats.taken = int(resume.get("taken", 0))
    stats.inappropriate = int(resume.get("inappropriate", 0))
    stats.other = int(resume.get("other", 0))
    stats.http_requests = int(resume.get("http_requests", 0))
    stats.bulk_requests = int(resume.get("bulk_requests", 0))
    stats.bulk_resolved = int(resume.get("bulk_resolved", 0))
    stats.individual_validations = int(resume.get("individual_validations", 0))

    seen = set(found)
    chars = charset_for(charset_mode, filters)

    if aesthetic:
        source = None
        generator = lambda: base.generate_aesthetic(length)
    else:
        source = build_unique_generator(
            length,
            chars,
            filters,
            resume_state=resume.get("generator_state"),
        )
        generator = source.__next__

    print(f"\nStarting MAX-SPEED {label}. Cache: {eng.db_path()}")
    print(
        f"Window: up to {TURBO_WINDOW_SIZE} candidates | bulk request: {TURBO_CANDIDATE_BATCH} names | "
        f"bulk concurrency: {bulk_controller.workers}->{bulk_controller.maximum}"
    )
    print(
        f"Survivor validators: {adaptive.workers}->{adaptive.maximum} workers | "
        "429 responses reduce concurrency and trigger cooldowns.\n"
    )

    last_checkpoint_at = time.monotonic()
    last_checkpoint_checked = stats.checked

    def checkpoint(force=False):
        nonlocal last_checkpoint_at, last_checkpoint_checked
        now = time.monotonic()
        if not force:
            if (
                now - last_checkpoint_at < CHECKPOINT_INTERVAL
                and stats.checked - last_checkpoint_checked < CHECKPOINT_EVERY
            ):
                return
        generator_state = source.snapshot() if source is not None else None
        eng.save_checkpoint(
            checkpoint_payload(
                label,
                length,
                target,
                max_checks,
                found,
                stats,
                filters,
                charset_mode,
                aesthetic,
                generator_state,
            )
        )
        last_checkpoint_at = now
        last_checkpoint_checked = stats.checked

    try:
        while len(found) < target and stats.checked < max_checks:
            batch_size = min(TURBO_WINDOW_SIZE, max_checks - stats.checked)
            candidates = generate_unique(
                batch_size,
                generator,
                filters,
                banned,
                seen if aesthetic else None,
                source_unique=not aesthetic,
            )
            if not candidates:
                print("\nUsername space exhausted or no more candidates passed the filters.")
                break

            check_candidates(
                candidates,
                store,
                stats,
                adaptive,
                label,
                target,
                found,
                stop_after_available=target,
                bulk_controller=bulk_controller,
                bulk_scheduler=bulk_scheduler,
                validator_executor=validator_executor,
                collect_rows=False,
                candidates_unique=not aesthetic,
            )
            checkpoint(False)

    except KeyboardInterrupt:
        print("\n\nScan interrupted. Resume checkpoint saved.")
        checkpoint(True)
        store.close()
        return
    finally:
        bulk_scheduler.close(wait=not (len(found) >= target))
        validator_executor.shutdown(wait=True, cancel_futures=True)

    eng.clear_checkpoint()
    store.close()
    finish_scan([], found, stats, label)

def finish_scan(rows, found, stats, label):
    print("\n\n" + "=" * 78)
    print(f"{label.upper()} COMPLETE")
    print("=" * 78)
    print(f"Usernames classified: {stats.checked}")
    print(f"Cache hits:           {stats.cache_hits}")
    print(f"Network usernames:    {stats.network_checks}")
    print(f"Actual HTTP requests: {stats.http_requests}")
    print(f"Bulk lookup requests: {stats.bulk_requests}")
    print(f"Resolved by bulk:     {stats.bulk_resolved}")
    print(f"Individual validators:{stats.individual_validations:>10}")
    print(f"Available users:      {stats.available}")
    print(f"Taken users:          {stats.taken}")
    print(f"Inappropriate:        {stats.inappropriate}")
    print(f"Other/errors:         {stats.other}")
    print(f"Availability rate:    {(stats.available / max(1, stats.checked)) * 100:.2f}%")
    print(f"Average throughput:   {stats.speed:.1f} usernames/s")
    if stats.http_requests:
        print(f"Effective density:    {stats.network_checks / stats.http_requests:.1f} usernames/HTTP request")
    print(f"Runtime:              {eng.format_duration(stats.elapsed)}")
    if found:
        ranked = sorted(found, key=lambda n: (-eng.score_username(n), n))
        print(f"Best result:          {ranked[0]} ({eng.score_username(ranked[0])}/100)")
        browse_results(ranked)
    else:
        print("\nNo available names found.")

def browse_results(names):
    order = list(dict.fromkeys(names))
    while order:
        print("\nAVAILABLE RESULT BROWSER")
        print("-" * 74)
        for i, name in enumerate(order[:60], 1):
            score = eng.score_username(name)
            print(f"[{i:>2}] {name:<14} score {score:>3}/100  {eng.score_label(score):<10} digits:{sum(c.isdigit() for c in name)}")
        if len(order) > 60:
            print(f"... {len(order)-60} more results not shown")
        choice = input("\n[s] score  [a] alphabetical  [d] digit count  [c] claim  [e] export TXT/CSV/JSON  [Enter] back: ").strip().lower()
        if not choice:
            return
        if choice == "s":
            order.sort(key=lambda n: (-eng.score_username(n), n))
        elif choice == "a":
            order.sort()
        elif choice == "d":
            order.sort(key=lambda n: (sum(c.isdigit() for c in n), -eng.score_username(n), n))
        elif choice == "c":
            base.claim_available_name(order)
        elif choice == "e":
            rows = [eng.result_row(n, "available") for n in order]
            paths = eng.export_results(rows, "available")
            print("Exported:")
            for kind, path in paths.items():
                print(f"  {kind.upper()}: {path}")


def maybe_save_preset(length, target, max_checks, aesthetic, filters):
    if not yesno("Save these settings as a preset?", False):
        return
    name = input("Preset name: ").strip().lower().replace(" ", "-")
    if not name:
        return
    presets = eng.load_presets()
    presets[name] = {
        "description": input("Short description: ").strip() or "Custom preset",
        "length": length,
        "target": target,
        "max_checks": max_checks,
        "aesthetic": aesthetic,
        "filters": vars(filters),
    }
    eng.save_presets(presets)
    print(f"Saved preset '{name}'.")


def scan_mode(aesthetic=False):
    length = base.pick_length()
    target = max(1, int(input("How many available names to find? ") or "10"))
    max_checks = max(target, int(input("Max checks? ") or "1000"))
    filters = configure_filters({"must_contain_vowel": aesthetic, "allow_digits": not aesthetic, "max_digits": 1 if not aesthetic else 0})
    charset_mode = "l" if aesthetic and not filters.allow_digits else choose_charset_mode()
    maybe_save_preset(length, target, max_checks, aesthetic, filters)
    run_target_scan(length, target, max_checks, filters, charset_mode, aesthetic, label="aesthetic" if aesthetic else "scan")


def generate_mode():
    length = base.pick_length()
    count = max(1, int(input("How many names to check? ") or "100"))
    aesthetic = yesno("Aesthetic/word-like generation?", False)
    filters = configure_filters({"must_contain_vowel": aesthetic})
    charset_mode = choose_charset_mode()
    chars = charset_for(charset_mode, filters)
    if aesthetic:
        generator = lambda: base.generate_aesthetic(length)
    else:
        generator = build_unique_generator(length, chars, filters).__next__
    banned = eng.load_banned_patterns()
    names = generate_unique(
        count,
        generator,
        filters,
        banned,
        set() if aesthetic else None,
        source_unique=not aesthetic,
    )
    store = eng.HistoryStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers()
    bulk_controller = fastnet.BulkConcurrencyController()
    bulk_scheduler = fastnet.BulkScheduler(bulk_controller)
    validator_executor = base.ThreadPoolExecutor(max_workers=adaptive.maximum)
    found = []
    offset = 0
    try:
        while offset < len(names):
            size = TURBO_WINDOW_SIZE
            check_candidates(
                names[offset:offset+size], store, stats, adaptive, "generate",
                len(names), found, bulk_controller=bulk_controller,
                bulk_scheduler=bulk_scheduler,
                validator_executor=validator_executor,
                collect_rows=False,
                candidates_unique=True,
            )
            offset += size
    finally:
        bulk_scheduler.close()
        validator_executor.shutdown(wait=True, cancel_futures=True)
    store.close()
    finish_scan([], found, stats, "generate")


def manual_mode():
    store = eng.HistoryStore()
    print("\nManual lookup. Type 'done' to return.")
    while True:
        name = input("Check name: ").strip().lower()
        if not name or name == "done":
            break
        cached = store.cached_status(name)
        if cached is not None:
            status, suffix = cached, " (cached)"
        else:
            _, status = base.smart_check(name)
            store.record(name, status, eng.score_username(name), "manual")
            suffix = ""
        print(f"  {name}: {status.upper()}{suffix} | score {eng.score_username(name)}/100")
        if status == "available" and yesno("Add to watchlist?", False):
            store.add_watch(name)
    store.close()


def wordlist_mode():
    path = input("Path to wordlist file: ").strip().replace('"', "")
    p = Path(path)
    if not p.exists():
        print("File not found.")
        return
    length = base.pick_length()
    filters = configure_filters()
    banned = eng.load_banned_patterns()
    words = [x.strip() for x in p.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    candidates, seen = [], set()
    for word in words:
        name = base.generate_from_word(word, length)
        if name and name not in seen and eng.passes_filters(name, filters, banned):
            seen.add(name)
            candidates.append(name)
    store = eng.HistoryStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers()
    bulk_controller = fastnet.BulkConcurrencyController()
    bulk_scheduler = fastnet.BulkScheduler(bulk_controller)
    validator_executor = base.ThreadPoolExecutor(max_workers=adaptive.maximum)
    found = []
    offset = 0
    try:
        while offset < len(candidates):
            size = TURBO_WINDOW_SIZE
            check_candidates(
                candidates[offset:offset+size], store, stats, adaptive, "wordlist",
                len(candidates), found, bulk_controller=bulk_controller,
                bulk_scheduler=bulk_scheduler,
                validator_executor=validator_executor,
                collect_rows=False,
                candidates_unique=True,
            )
            offset += size
    finally:
        bulk_scheduler.close()
        validator_executor.shutdown(wait=True, cancel_futures=True)
    store.close()
    finish_scan([], found, stats, "wordlist")


def mutation_mode():
    word = input("Base word/name: ").strip()
    if not word:
        return
    raw = input("Target length [4/5/6 or Enter = flexible]: ").strip()
    length = int(raw) if raw in {"4", "5", "6"} else None
    limit = max(1, min(500, int(input("Max mutations to check [100]: ") or "100")))
    filters = configure_filters()
    banned = eng.load_banned_patterns()
    candidates = [n for n in eng.mutate_word(word, length, limit * 3) if eng.passes_filters(n, filters, banned)][:limit]
    print(f"Generated {len(candidates)} filtered mutations.")
    store = eng.HistoryStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers()
    bulk_controller = fastnet.BulkConcurrencyController()
    bulk_scheduler = fastnet.BulkScheduler(bulk_controller)
    validator_executor = base.ThreadPoolExecutor(max_workers=adaptive.maximum)
    found = []
    offset = 0
    try:
        while offset < len(candidates):
            size = TURBO_WINDOW_SIZE
            check_candidates(
                candidates[offset:offset+size], store, stats, adaptive, "mutation",
                len(candidates), found, bulk_controller=bulk_controller,
                bulk_scheduler=bulk_scheduler,
                validator_executor=validator_executor,
                collect_rows=False,
                candidates_unique=True,
            )
            offset += size
    finally:
        bulk_scheduler.close()
        validator_executor.shutdown(wait=True, cancel_futures=True)
    store.close()
    finish_scan([], found, stats, "mutation")


def watchlist_mode():
    store = eng.HistoryStore()
    while True:
        items = store.watch_items()
        print("\nWATCHLIST\n" + "-" * 60)
        if items:
            for i, row in enumerate(items, 1):
                print(f"[{i:>2}] {row['username']:<16} {row['status'] or 'never checked':<16} score:{row['score'] or 0}")
        else:
            print("(empty)")
        choice = input("\n[a] add  [r] remove  [c] recheck all once  [Enter] back: ").strip().lower()
        if not choice:
            break
        if choice == "a":
            name = input("Username: ").strip().lower()
            if name:
                store.add_watch(name, input("Note (optional): ").strip())
        elif choice == "r":
            store.remove_watch(input("Username to remove: ").strip().lower())
        elif choice == "c":
            for row in list(store.watch_items()):
                name = row["username"]
                _, status = base.smart_check(name)
                store.record(name, status, eng.score_username(name), "watchlist")
                print(f"  {name:<16} {status}")
    store.close()


def presets_mode():
    presets = eng.load_presets()
    keys = list(presets)
    print("\nSCAN PRESETS\n" + "-" * 70)
    for i, key in enumerate(keys, 1):
        print(f"[{i:>2}] {key:<16} {presets[key].get('description','')}")
    choice = input("Choose preset number, [d] delete custom preset, or Enter: ").strip().lower()
    if not choice:
        return
    if choice == "d":
        name = input("Preset name to delete: ").strip()
        if name in presets and name not in eng.BUILTIN_PRESETS:
            del presets[name]
            eng.save_presets(presets)
            print("Deleted.")
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(keys)):
        return
    key = keys[int(choice)-1]
    preset = presets[key]
    filters = eng.FilterConfig.from_dict(preset.get("filters"))
    aesthetic = bool(preset.get("aesthetic"))
    charset = "l" if not filters.allow_digits else "m"
    run_target_scan(int(preset["length"]), int(preset["target"]), int(preset["max_checks"]), filters, charset, aesthetic, label=f"preset:{key}")


def resume_mode():
    cp = eng.load_checkpoint()
    if not cp:
        print("No unfinished scan checkpoint found.")
        return
    print(f"Resume {cp.get('mode')} scan: checked {cp.get('checked',0)}/{cp.get('max_checks')} with {len(cp.get('found',[]))}/{cp.get('target')} available?")
    if not yesno("Resume it?", True):
        if yesno("Discard checkpoint?", False):
            eng.clear_checkpoint()
        return
    filters = eng.FilterConfig.from_dict(cp.get("filters"))
    run_target_scan(int(cp["length"]), int(cp["target"]), int(cp["max_checks"]), filters, cp.get("charset_mode","m"), bool(cp.get("aesthetic")), resume=cp, label=cp.get("mode","resume"))


def banned_patterns_mode():
    path = eng.excluded_patterns_path()
    while True:
        patterns = eng.load_banned_patterns()
        print(f"\nEXCLUDED PATTERNS: {path}")
        for i, pattern in enumerate(patterns, 1):
            print(f"[{i}] {pattern}")
        if not patterns:
            print("(none)")
        choice = input("[a] add  [r] remove  [o] open file  [Enter] back: ").strip().lower()
        if not choice:
            return
        if choice == "a":
            pattern = input("Substring or regex: ").strip()
            if pattern:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(pattern + "\n")
        elif choice == "r" and patterns:
            raw = input("Number: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(patterns):
                path.write_text("# Excluded username patterns\n" + "\n".join(p for i, p in enumerate(patterns, 1) if i != int(raw)) + "\n", encoding="utf-8")
        elif choice == "o":
            try:
                if os.name == "nt":
                    os.startfile(path)
                else:
                    print(path)
            except Exception as exc:
                print(f"Could not open file: {exc}")


def diagnostics_mode():
    print("\nDIAGNOSTICS\n" + "=" * 64)
    checks = []
    try:
        store = eng.HistoryStore()
        summary = store.summary()
        store.close()
        checks.append(("SQLite history", True, f"{summary['total']} cached names, {summary['watchlist']} watched"))
    except Exception as exc:
        checks.append(("SQLite history", False, str(exc)))
    checks.append(("State directory", eng.state_dir().exists(), str(eng.state_dir())))
    checks.append(("Portable mode", True, "ON" if eng.portable_mode() else "OFF (create portable.flag beside the EXE to enable)"))
    try:
        response = requests.get("https://www.roblox.com/", timeout=5)
        checks.append(("Roblox connectivity", response.status_code < 500, f"HTTP {response.status_code}"))
    except Exception as exc:
        checks.append(("Roblox connectivity", False, str(exc)))
    try:
        token = base.ensure_token()
        checks.append(("CSRF token", bool(token), "available" if token else "not available"))
    except Exception as exc:
        checks.append(("CSRF token", False, str(exc)))
    checks.append(("Windows clipboard helper", bool(shutil.which("clip.exe")) if os.name == "nt" else True, "clip.exe" if os.name == "nt" else "not Windows"))
    ext = eng.app_root() / "browser-extension"
    checks.append(("Bundled browser extension", ext.exists(), str(ext)))
    for name, ok, detail in checks:
        print(f"  {'OK' if ok else 'FAIL':<4} {name:<27} {detail}")
    print("\nHistory status summary:")
    try:
        store = eng.HistoryStore()
        print(store.summary())
        store.close()
    except Exception:
        pass


def check_for_update(silent=False):
    try:
        response = requests.get(eng.GITHUB_LATEST_RELEASE, headers={"Accept":"application/vnd.github+json"}, timeout=3)
        response.raise_for_status()
        data = response.json()
        latest = data.get("tag_name") or ""
        url = data.get("html_url") or f"https://github.com/{eng.REPO}/releases"
        if eng.is_newer_version(APP_VER, latest):
            print(f"\nUpdate available: {latest} (current v{APP_VER})")
            if not silent and yesno("Open Releases page?", False):
                webbrowser.open_new_tab(url)
            return True
        if not silent:
            print(f"Latest release: {latest or 'unknown'}; current: v{APP_VER}")
    except Exception as exc:
        if not silent:
            print(f"Update check unavailable: {exc}")
    return False


def print_paths():
    print(f"State:   {eng.state_dir()}")
    print(f"Exports: {eng.exports_dir()}")
    print(f"DB:      {eng.db_path()}")
    print(f"Filters: {eng.excluded_patterns_path()}")


def run_main():
    print(f"{base.APP_NAME} v{APP_VER}".center(74))
    print("(Roblox username search engine + availability checker)".center(74))
    print_paths()
    print("\nCSRF token: lazy-loaded only if a bulk survivor needs signup validation.")
    if eng.load_checkpoint():
        print("\nUnfinished scan found. Choose [r] to resume it.")

    while True:
        print("\n" + "=" * 74)
        print(" [s] scan      [a] aesthetic   [g] generate   [m] manual   [w] wordlist")
        print(" [x] mutate    [p] presets     [v] watchlist  [r] resume   [c] credentials")
        print(" [b] exclusions [d] diagnostics [u] updates    [q] quit")
        mode = input("Mode: ").strip().lower()
        try:
            if mode == "s":
                scan_mode(False)
            elif mode == "a":
                scan_mode(True)
            elif mode == "g":
                generate_mode()
            elif mode == "m":
                manual_mode()
            elif mode == "w":
                wordlist_mode()
            elif mode == "x":
                mutation_mode()
            elif mode == "p":
                presets_mode()
            elif mode == "v":
                watchlist_mode()
            elif mode == "r":
                resume_mode()
            elif mode == "c":
                accounts.saved_accounts_mode()
            elif mode == "b":
                banned_patterns_mode()
            elif mode == "d":
                diagnostics_mode()
            elif mode == "u":
                check_for_update(False)
            elif mode in {"q","quit","exit"}:
                print("\n--- made by scarn ---")
                return
            elif not mode:
                continue
            else:
                print("Unknown mode.")
        except KeyboardInterrupt:
            print("\nOperation cancelled. Returning to menu.")
        except ValueError:
            print("Invalid number entered. Returning to menu.")
        except Exception as exc:
            print(f"\nUnexpected error: {exc}\nReturning to menu.")


if __name__ == "__main__":
    run_main()
