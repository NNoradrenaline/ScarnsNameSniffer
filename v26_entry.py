#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.6 executable entrypoint."""

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


if __name__ == "__main__":
    engine.run_main()
