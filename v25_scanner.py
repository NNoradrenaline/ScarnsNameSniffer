#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.5 advanced scanner UI."""
from __future__ import annotations

import os
import shutil
import sys
import time
import webbrowser
from collections import deque
from pathlib import Path

import requests

import roblox_name_gen as base
import v25_engine as eng
import v25_launcher as accounts

APP_VER = "2.5"
base.APP_VER = APP_VER
accounts.APP_VER = APP_VER

_recent_available = deque(maxlen=6)


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


def dashboard(stats, adaptive, target, found, mode, current="", cache_note=""):
    elapsed = eng.format_duration(stats.elapsed)
    print("\r" + " " * 155 + "\r", end="")
    line = (
        f"[{mode}] checked:{stats.checked}  available:{stats.available}  taken:{stats.taken}  "
        f"inappropriate:{stats.inappropriate}  other:{stats.other}  cache:{stats.cache_hits}  "
        f"workers:{adaptive.workers}  speed:{stats.speed:.1f}/s  time:{elapsed}  target:{len(found)}/{target}"
    )
    if current:
        line += f"  | {current}"
    if cache_note:
        line += f" {cache_note}"
    sys.stdout.write(line[:154])
    sys.stdout.flush()


def print_available_live(name):
    _recent_available.appendleft(name)
    sys.stdout.write("\r" + " " * 155 + "\r")
    score = eng.score_username(name)
    print(f"  >>> AVAILABLE  {name:<12} score {score:>3}/100 {eng.score_label(score)}")


def generate_unique(count, generator, filters, banned, seen):
    out = []
    attempts = 0
    max_attempts = max(200, count * 80)
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        name = generator().lower()
        if name in seen:
            continue
        seen.add(name)
        if eng.passes_filters(name, filters, banned):
            out.append(name)
    return out


def check_candidates(candidates, store, stats, adaptive, mode, target=None, found=None):
    """Check a finite candidate list using valid cache entries before network."""
    results = []
    found = found if found is not None else []
    uncached = []

    for name in candidates:
        cached = store.cached_status(name)
        if cached is not None:
            stats.record(cached, cached=True)
            row = eng.result_row(name, cached)
            results.append(row)
            if cached == "available" and name not in found:
                found.append(name)
                print_available_live(name)
            dashboard(stats, adaptive, target or len(candidates), found, mode, name, "[cached]")
        else:
            uncached.append(name)

    if not uncached:
        return results

    with base.ThreadPoolExecutor(max_workers=adaptive.workers) as executor:
        futures = {executor.submit(base.smart_check, name): name for name in uncached}
        statuses = []
        for future in base.as_completed(futures):
            name = futures[future]
            try:
                _, status = future.result()
            except Exception as exc:
                status = f"error({exc})"
            statuses.append(status)
            score = eng.score_username(name)
            store.record(name, status, score, mode)
            stats.record(status, cached=False)
            row = eng.result_row(name, status)
            results.append(row)
            if status == "available" and name not in found:
                found.append(name)
                print_available_live(name)
            dashboard(stats, adaptive, target or len(candidates), found, mode, name)

    before = adaptive.workers
    adaptive.observe(statuses)
    if "ratelimited" in statuses:
        sys.stdout.write("\n  Roblox rate limiting detected. Backing off and cooling down.\n")
        time.sleep(2.0)
    elif adaptive.workers < before:
        time.sleep(0.5)
    return results


def checkpoint_payload(mode, length, target, max_checks, found, stats, filters, charset_mode, aesthetic):
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
        "elapsed": stats.elapsed,
        "filters": vars(filters),
        "charset_mode": charset_mode,
        "aesthetic": bool(aesthetic),
    }


def run_target_scan(length, target, max_checks, filters, charset_mode="m", aesthetic=False, resume=None, label="scan"):
    store = eng.HistoryStore()
    banned = eng.load_banned_patterns()
    adaptive = eng.AdaptiveWorkers()
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
    seen = set(found)
    rows = []

    chars = charset_for(charset_mode, filters)
    generator = (lambda: base.generate_aesthetic(length)) if aesthetic else (lambda: base.generate_random(length, chars))

    print(f"\nStarting {label}. Cache: {eng.db_path()}")
    print(f"Workers adapt conservatively between {eng.MIN_WORKERS} and {eng.MAX_WORKERS}; rate limits cause backoff.\n")

    try:
        while len(found) < target and stats.checked < max_checks:
            batch_size = min(adaptive.workers, max_checks - stats.checked)
            candidates = generate_unique(batch_size, generator, filters, banned, seen)
            if not candidates:
                print("\nNo more candidates passed the current filters.")
                break
            batch_rows = check_candidates(candidates, store, stats, adaptive, label, target, found)
            rows.extend(batch_rows)
            eng.save_checkpoint(checkpoint_payload(label, length, target, max_checks, found, stats, filters, charset_mode, aesthetic))
    except KeyboardInterrupt:
        print("\n\nScan interrupted. Resume checkpoint saved.")
        eng.save_checkpoint(checkpoint_payload(label, length, target, max_checks, found, stats, filters, charset_mode, aesthetic))
        store.close()
        return

    eng.clear_checkpoint()
    store.close()
    finish_scan(rows, found, stats, label)


def finish_scan(rows, found, stats, label):
    print("\n\n" + "=" * 74)
    print(f"{label.upper()} COMPLETE")
    print("=" * 74)
    print(f"Checked:           {stats.checked}")
    print(f"Network checks:    {stats.network_checks}")
    print(f"Cache hits:        {stats.cache_hits}")
    print(f"Available users:   {stats.available}")
    print(f"Taken users:       {stats.taken}")
    print(f"Inappropriate:     {stats.inappropriate}")
    print(f"Other/errors:      {stats.other}")
    print(f"Availability rate: {(stats.available / max(1, stats.checked)) * 100:.2f}%")
    print(f"Average speed:     {stats.speed:.1f}/s")
    print(f"Runtime:           {eng.format_duration(stats.elapsed)}")
    if found:
        ranked = sorted(found, key=lambda n: (-eng.score_username(n), n))
        print(f"Best result:       {ranked[0]} ({eng.score_username(ranked[0])}/100)")
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
    generator = (lambda: base.generate_aesthetic(length)) if aesthetic else (lambda: base.generate_random(length, chars))
    banned = eng.load_banned_patterns()
    names = generate_unique(count, generator, filters, banned, set())
    store = eng.HistoryStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers()
    found, rows = [], []
    offset = 0
    while offset < len(names):
        size = adaptive.workers
        rows.extend(check_candidates(names[offset:offset+size], store, stats, adaptive, "generate", len(names), found))
        offset += size
    store.close()
    finish_scan(rows, found, stats, "generate")


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
    found, rows = [], []
    offset = 0
    while offset < len(candidates):
        size = adaptive.workers
        rows.extend(check_candidates(candidates[offset:offset+size], store, stats, adaptive, "wordlist", len(candidates), found))
        offset += size
    store.close()
    finish_scan(rows, found, stats, "wordlist")


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
    found, rows = [], []
    offset = 0
    while offset < len(candidates):
        size = adaptive.workers
        rows.extend(check_candidates(candidates[offset:offset+size], store, stats, adaptive, "mutation", len(candidates), found))
        offset += size
    store.close()
    finish_scan(rows, found, stats, "mutation")


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
    print("\nFetching CSRF token...", end=" ")
    token = base.get_csrf_token()
    print("OK" if token else "FAILED (scanner will report request errors)")
    check_for_update(silent=True)
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
