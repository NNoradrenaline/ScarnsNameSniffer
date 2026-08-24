#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.6 executable entrypoint."""

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

if __name__ == "__main__":
    engine.run_main()
