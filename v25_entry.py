#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.5 executable entrypoint."""

import webbrowser

import roblox_name_gen as base
import v25_launcher as launcher
import v25_scanner as scanner

APP_VER = "2.5"
base.APP_VER = APP_VER
launcher.APP_VER = APP_VER
scanner.APP_VER = APP_VER


def open_registration_page_v25(name=None):
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
        print("    Companion v2.5 will fill the form and clear the clipboard handoff.")
        print("    When the form is ready, press Enter to use Roblox's normal Create Account button.")
    except Exception as exc:
        print(f"    Could not open browser: {exc}")


base.open_registration_page = open_registration_page_v25


if __name__ == "__main__":
    scanner.run_main()
