#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.6 executable entrypoint."""

import random
import sys
import webbrowser

import roblox_name_gen as base
import v25_launcher as accounts
import v26_engine as engine

APP_VER = "2.6"
base.APP_VER = APP_VER
accounts.APP_VER = APP_VER


def open_registration_page_v26(name=None):
    """Prepare one secure signup handoff and open Roblox Create Account."""
    if not name:
        try:
            webbrowser.open_new_tab(base.ROBLOX_REGISTRATION_URL)
            print("    Opening Roblox Create Account...")
        except Exception as exc:
            print(f"    Could not open browser: {exc}")
        return

    password = base.generate_account_password()
    saved = base.save_windows_credential(name, password)
    payload = base.make_autofill_payload(name, password, saved)
    copied = base.copy_to_clipboard(payload)

    if saved:
        print(f"    Saved '{name}' securely in Windows Credential Manager.")
    else:
        print("    Warning: Windows Credential Manager save failed.")

    if copied:
        print("    Prepared one-time autofill handoff for the browser companion.")
    else:
        print("    Clipboard handoff failed; browser autofill may need manual input.")

    try:
        webbrowser.open_new_tab(base.ROBLOX_REGISTRATION_URL)
        print("    Opening Roblox Create Account...")
        print("    Companion will fill the signup form and clear the clipboard handoff.")
        print("    Review the form, then press Enter to use Roblox's normal signup button.")
    except Exception as exc:
        print(f"    Could not open browser: {exc}")


base.open_registration_page = open_registration_page_v26


# Candidate-generation hotfix.
# In v2.6 aesthetic + mixed mode, the original best-of-N ranking strongly
# preferred all-letter candidates because score_name rewards zero digits.
# That made "mixed" behave almost like letters-only. For short Roblox names,
# deliberately using one clean digit greatly expands the candidate space while
# preserving a pronounceable stem.
_original_generate_ranked = engine.generate_ranked


def _aesthetic_letters(length):
    candidate = base.generate_aesthetic(length)
    letters = "".join(ch for ch in candidate.lower() if ch.isalpha())
    while len(letters) < length:
        letters += random.choice(base.LETTERS)
    return letters[:length]


def generate_ranked_mixed_fix(length, charset=None, aesthetic=True):
    charset = charset or base.CHARSET

    # Preserve every existing generator path except aesthetic + mixed.
    if not aesthetic or charset != base.CHARSET:
        return _original_generate_ranked(length, charset, aesthetic)

    pool = []
    for _ in range(14):
        stem = _aesthetic_letters(length)
        digit = random.choice(base.DIGITS)

        # Keep exactly one digit. Most candidates put it at an edge so the
        # pronounceable portion remains intact, with some internal variants.
        style = random.randrange(5)
        if style in (0, 1):
            candidate = stem[:-1] + digit
        elif style == 2:
            candidate = digit + stem[1:]
        else:
            pos = random.randrange(1, max(2, length - 1))
            chars = list(stem)
            chars[min(pos, length - 2)] = digit
            candidate = "".join(chars)

        pool.append(candidate[:length])

    return max(pool, key=engine.score_name)


engine.generate_ranked = generate_ranked_mixed_fix


# Display hotfix: surface available usernames while scans are still running.
_original_progress_line = engine.progress_line
_original_print_scan_summary = engine.print_scan_summary
_seen_verified = set()
_seen_unverified = set()


def _clear_progress_line():
    sys.stdout.write("\r" + (" " * 170) + "\r")
    sys.stdout.flush()


def progress_line_with_available(checked, max_checks, found, unverified, scanner):
    new_verified = [name for name in found if name not in _seen_verified]
    new_unverified = [name for name in unverified if name not in _seen_unverified]

    if new_verified or new_unverified:
        _clear_progress_line()
        for name in new_verified:
            _seen_verified.add(name)
            print(
                f"  >>> AVAILABLE ✓ VERIFIED: {name:<20} "
                f"score {engine.score_name(name):>3}/100"
            )
        for name in new_unverified:
            _seen_unverified.add(name)
            print(
                f"  >>> AVAILABLE ⚠ NEEDS RECHECK: {name:<20} "
                f"score {engine.score_name(name):>3}/100"
            )

    _original_progress_line(checked, max_checks, found, unverified, scanner)


def print_scan_summary_with_available(results, scanner):
    _original_print_scan_summary(results, scanner)

    available = [
        result
        for result in results
        if result["status"] in {"verified_available", "available_unverified"}
    ]
    if not available:
        print("\n  AVAILABLE NAMES: none found in this session")
        return

    print("\n  ALL AVAILABLE NAMES")
    print("  " + "-" * 60)
    for result in sorted(
        available,
        key=lambda item: (
            item["status"] != "verified_available",
            -item["score"],
            item["name"],
        ),
    ):
        badge = (
            "AVAILABLE ✓ VERIFIED"
            if result["status"] == "verified_available"
            else "AVAILABLE ⚠ RECHECK"
        )
        print(
            f"    {result['name']:<20} score {result['score']:>3}/100  {badge}"
        )


engine.progress_line = progress_line_with_available
engine.print_scan_summary = print_scan_summary_with_available


# Better scan-budget UX. Asking for 500 available names with only 500 total
# checks requires a 100% hit rate, so v2.6 now recommends a realistic search
# budget while still respecting an explicitly smaller value.
def scan_mode_with_budget_hint(aesthetic_default=True):
    _seen_verified.clear()
    _seen_unverified.clear()

    lengths = engine.choose_lengths()
    target = max(1, int(input("How many VERIFIED available names to find? ") or "5"))
    recommended = max(500, target * 20)
    raw_max = input(f"Max checks? (recommended {recommended}): ").strip()
    max_checks = max(target, int(raw_max or str(recommended)))

    if max_checks < target * 5:
        print(
            f"  Note: {target} finds in {max_checks} checks is a very aggressive target. "
            f"For short names, {recommended}+ checks is more realistic."
        )

    charset = engine.choose_charset()
    if aesthetic_default and charset == "mixed":
        print("  Mixed aesthetic mode: clean one-digit candidates enabled.")

    config = {
        "lengths": lengths,
        "target": target,
        "max_checks": max_checks,
        "charset": charset,
        "aesthetic": aesthetic_default,
    }
    engine.run_scan(config)


engine.scan_mode = scan_mode_with_budget_hint


if __name__ == "__main__":
    engine.run_main()
