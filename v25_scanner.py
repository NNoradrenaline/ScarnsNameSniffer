#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.5 scanner launcher.

Keeps the v2.5 credential/browser behavior while improving the interactive
scanner loop, live scan counters, and healthy-request throughput.
"""

import sys
import time
from collections import Counter

import roblox_name_gen as base
import v25_launcher as accounts

APP_VER = "2.5"
base.APP_VER = APP_VER
accounts.APP_VER = APP_VER

# A modest bump over the legacy 10-worker scanner. Healthy batches run without
# an artificial sleep; Roblox rate-limit responses still trigger a cooldown.
SCAN_WORKERS = 16
RATE_LIMIT_COOLDOWN = 1.0

_live_counts = Counter()
_live_seen_available = set()


def reset_live_progress():
    _live_counts.clear()
    _live_seen_available.clear()


def live_progress(name, status, found, total):
    """Render cumulative scan counts and surface available names immediately."""
    normalized = status or "unknown"
    _live_counts[normalized] += 1

    if normalized == "available" and name not in _live_seen_available:
        _live_seen_available.add(name)
        sys.stdout.write("\r" + (" " * 120) + "\r")
        sys.stdout.flush()
        print(f"  >>> AVAILABLE: {name}")

    other = max(
        0,
        total
        - _live_counts.get("available", 0)
        - _live_counts.get("taken", 0)
        - _live_counts.get("inappropriate", 0),
    )
    line = (
        f"\r  checked:{total:<6} "
        f"available:{_live_counts.get('available', 0):<5} "
        f"taken:{_live_counts.get('taken', 0):<6} "
        f"inappropriate:{_live_counts.get('inappropriate', 0):<5} "
        f"other:{other:<5} "
        f"| {name:<8} -> {normalized[:20]}"
    )
    sys.stdout.write(line[:150])
    sys.stdout.flush()


# Make legacy wordlist mode use the same live counter display.
base.p_prog = live_progress


def choose_charset():
    print("Charset options:")
    print("  [L] Letters only (a-z)")
    print("  [M] Mixed letters+digits (default)")
    print("  [N] Numbers only (0-9)")
    choice = input("Choose: ").strip().lower()
    if choice == "l":
        return base.LETTERS
    if choice == "n":
        return base.NUMBERS_ONLY
    return base.CHARSET


def unique_generated_batch(count, generator):
    names = []
    seen = set()
    attempts = 0
    max_attempts = max(100, count * 20)
    while len(names) < count and attempts < max_attempts:
        attempts += 1
        name = generator()
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def maybe_cool_down(statuses):
    rate_limited = sum(1 for status in statuses if status == "ratelimited")
    if not rate_limited:
        return
    cooldown = RATE_LIMIT_COOLDOWN if rate_limited < max(2, len(statuses) // 2) else 2.0
    print(
        f"\n  Roblox rate limiting detected ({rate_limited} responses). "
        f"Cooling down {cooldown:.1f}s."
    )
    time.sleep(cooldown)


def run_until_target(length, target, max_checks, generator, label):
    found = []
    total = 0
    reset_live_progress()

    print(
        f"\n  Fast scan started with up to {SCAN_WORKERS} workers. "
        "Healthy batches do not use the old fixed delay."
    )
    print("  Roblox rate-limit responses still trigger a cooldown.\n")

    with base.ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
        while len(found) < target and total < max_checks:
            batch_size = min(SCAN_WORKERS, max_checks - total)
            names = unique_generated_batch(batch_size, generator)
            if not names:
                break

            futures = {executor.submit(base.smart_check, name): name for name in names}
            batch_statuses = []
            for future in base.as_completed(futures):
                try:
                    name, status = future.result()
                except Exception as exc:
                    name = futures[future]
                    status = f"error({exc})"

                total += 1
                batch_statuses.append(status)
                if status == "available" and name not in found:
                    found.append(name)
                live_progress(name, status, len(found), total)

            maybe_cool_down(batch_statuses)

    print("\n\n" + "=" * 66)
    print(f"  {label} - Checked {total}, Available {len(found)} ({length} chars)")
    print("=" * 66)
    print(
        f"  Available users:     {_live_counts.get('available', 0)}\n"
        f"  Taken users:         {_live_counts.get('taken', 0)}\n"
        f"  Inappropriate users: {_live_counts.get('inappropriate', 0)}"
    )
    for name in found:
        base.print_available(name)
    if not found:
        print("    (none found)")

    if found:
        base.claim_available_name(found)
        if input("  Save to desktop? [Y/n]: ").strip().lower() != "n":
            base.save_results(found, f"{label.lower().replace(' ', '-')}-{length}char")
    print("\n--- made by scarn ---\n")


def scan_mode():
    length = base.pick_length()
    target = max(1, int(input("How many names to find? ") or "5"))
    charset = choose_charset()
    max_checks = max(target, int(input("Max checks? ") or "500"))
    run_until_target(
        length,
        target,
        max_checks,
        lambda: base.generate_random(length, charset),
        "SCAN DONE",
    )


def aesthetic_mode():
    length = base.pick_length()
    target = max(1, int(input("How many aesthetic names to find? ") or "5"))
    max_checks = max(target, int(input("Max checks? ") or "500"))
    run_until_target(
        length,
        target,
        max_checks,
        lambda: base.generate_aesthetic(length),
        "AESTHETIC SCAN DONE",
    )


def generate_mode():
    length = base.pick_length()
    batch = max(1, int(input("How many names? ") or "100"))
    aesthetic = input("Aesthetic/word-like? [y/N]: ").strip().lower() == "y"
    charset = choose_charset()

    if aesthetic:
        generator = lambda: base.generate_aesthetic(length)
    else:
        generator = lambda: base.generate_random(length, charset)

    names = unique_generated_batch(batch, generator)
    results = []
    reset_live_progress()

    print(
        f"\n  Checking {len(names)} unique names with up to {SCAN_WORKERS} workers...\n"
    )

    with base.ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
        futures = {executor.submit(base.smart_check, name): name for name in names}
        batch_statuses = []
        for future in base.as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                name = futures[future]
                result = (name, f"error({exc})")
            results.append(result)
            name, status = result
            batch_statuses.append(status)
            live_progress(
                name,
                status,
                _live_counts.get("available", 0),
                len(results),
            )

        maybe_cool_down(batch_statuses)

    available = [name for name, status in results if status == "available"]
    aesthetic_names = [name for name in available if base.is_aesthetic(name)]
    random_names = [name for name in available if not base.is_aesthetic(name)]

    print("\n\n" + "=" * 66)
    print(f"  RESULTS ({length} chars) - Available: {len(available)}/{len(results)}")
    print("=" * 66)
    print(
        f"  Available users:     {_live_counts.get('available', 0)}\n"
        f"  Taken users:         {_live_counts.get('taken', 0)}\n"
        f"  Inappropriate users: {_live_counts.get('inappropriate', 0)}"
    )

    if aesthetic_names:
        print(f"\n  AESTHETIC ({len(aesthetic_names)}):")
        for name in aesthetic_names:
            base.print_available(name, f"({base.is_wordlike(name)}/10)")
    if random_names:
        print(f"\n  RANDOM ({len(random_names)}):")
        for name in random_names:
            base.print_available(name)

    other = [
        result
        for result in results
        if result[1] not in ("available", "taken", "inappropriate")
    ]
    if other:
        print("\n  OTHER:")
        for status, count in Counter(status for _, status in other).most_common(5):
            print(f"    {status}: {count}")

    if available:
        base.claim_available_name(available)
        if input("  Save to desktop? [Y/n]: ").strip().lower() != "n":
            base.save_results(available, f"batch-{length}char")
    print("\n--- made by scarn ---\n")


def wordlist_mode():
    reset_live_progress()
    base.wordlist_mode(base.pick_length())


def run_main():
    print(f"{base.APP_NAME} v{APP_VER}".center(66))
    print("(Roblox username generator + availability checker)".center(66))
    print()
    print("Fetching CSRF token...", end=" ")
    token = base.get_csrf_token()
    print(f"{'OK' if token else 'FAILED'}")

    while True:
        print(
            "\n"
            "  [s] scan   [g] generate   [a] aesthetic-only   [m] manual\n"
            "  [w] wordlist   [c] credentials   [q] quit"
        )
        mode = input("\nMode: ").strip().lower()

        try:
            if mode == "s":
                scan_mode()
            elif mode == "g":
                generate_mode()
            elif mode == "a":
                aesthetic_mode()
            elif mode == "m":
                base.manual_lookup_mode()
            elif mode == "w":
                wordlist_mode()
            elif mode == "c":
                accounts.saved_accounts_mode()
            elif mode in {"q", "quit", "exit"}:
                print("\n--- made by scarn ---")
                return
            elif not mode:
                continue
            else:
                print("  Unknown mode. Choose s, g, a, m, w, c, or q.")
                continue

            print("  Ready for another scan.")
        except KeyboardInterrupt:
            print("\n  Current operation cancelled. Returning to main menu.")


if __name__ == "__main__":
    run_main()
