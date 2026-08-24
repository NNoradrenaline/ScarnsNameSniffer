#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.5 launcher.

Adds Saved Accounts management on top of the v2.4 scanner while keeping the
existing generator/checker implementation in roblox_name_gen.py.
"""

import ctypes
import os
import subprocess
import webbrowser
from datetime import datetime

import roblox_name_gen as base

APP_VER = "2.5"
CREDENTIAL_PREFIX = "ScarnsNameSniffer:"
ROBLOX_LOGIN_URL = "https://www.roblox.com/login"

# Keep version-sensitive messages and credential comments in the imported core
# aligned with the launcher build.
base.APP_VER = APP_VER


def _credential_types():
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.c_void_p),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    return wintypes, CREDENTIALW


def list_saved_usernames():
    """Return Name Sniffer Generic Credentials without exposing passwords."""
    if os.name != "nt":
        return []
    try:
        wintypes, CREDENTIALW = _credential_types()
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        enumerate_credentials = advapi32.CredEnumerateW
        enumerate_credentials.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(CREDENTIALW))),
        ]
        enumerate_credentials.restype = wintypes.BOOL
        cred_free = advapi32.CredFree
        cred_free.argtypes = [ctypes.c_void_p]
        cred_free.restype = None

        count = wintypes.DWORD(0)
        credentials = ctypes.POINTER(ctypes.POINTER(CREDENTIALW))()
        ok = enumerate_credentials(
            f"{CREDENTIAL_PREFIX}*",
            0,
            ctypes.byref(count),
            ctypes.byref(credentials),
        )
        if not ok:
            return []

        usernames = []
        try:
            for i in range(count.value):
                cred = credentials[i].contents
                target = cred.TargetName or ""
                username = cred.UserName or (
                    target[len(CREDENTIAL_PREFIX):]
                    if target.startswith(CREDENTIAL_PREFIX)
                    else target
                )
                if username and username not in usernames:
                    usernames.append(username)
        finally:
            cred_free(credentials)
        return sorted(usernames, key=str.lower)
    except Exception:
        return []


def read_saved_credential(username):
    """Return (username, password) for one Name Sniffer credential."""
    if os.name != "nt":
        return None
    try:
        wintypes, CREDENTIALW = _credential_types()
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        cred_read = advapi32.CredReadW
        cred_read.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
        ]
        cred_read.restype = wintypes.BOOL
        cred_free = advapi32.CredFree
        cred_free.argtypes = [ctypes.c_void_p]
        cred_free.restype = None

        pointer = ctypes.POINTER(CREDENTIALW)()
        if not cred_read(
            f"{CREDENTIAL_PREFIX}{username}", 1, 0, ctypes.byref(pointer)
        ):
            return None

        try:
            cred = pointer.contents
            raw = (
                ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
                if cred.CredentialBlobSize
                else b""
            )
            return cred.UserName or username, raw.decode("utf-16-le")
        finally:
            cred_free(pointer)
    except Exception:
        return None


def delete_saved_credential(username):
    if os.name != "nt":
        return False
    try:
        wintypes, _ = _credential_types()
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        cred_delete = advapi32.CredDeleteW
        cred_delete.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        cred_delete.restype = wintypes.BOOL
        return bool(cred_delete(f"{CREDENTIAL_PREFIX}{username}", 1, 0))
    except Exception:
        return False


def open_credential_manager():
    if os.name != "nt":
        return False
    try:
        subprocess.Popen(
            ["control.exe", "/name", "Microsoft.CredentialManager"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception:
        return False


def saved_accounts_mode():
    print("\n--- Saved Accounts ---")
    print("Credentials here are saved before signup finishes, so an entry is not proof the Roblox account was successfully created.")

    if os.name != "nt":
        print("  Saved Accounts is available on Windows only.\n")
        return

    while True:
        accounts = list_saved_usernames()
        print("\n  SAVED CREDENTIALS")
        print("  " + "-" * 44)
        if accounts:
            for i, username in enumerate(accounts, 1):
                print(f"  [{i:>2}] {username}")
        else:
            print("  (none found)")

        choice = input(
            "\n  Choose account, [o] open Credential Manager, [e] export usernames, or Enter to go back: "
        ).strip().lower()

        if not choice:
            return
        if choice == "o":
            print(
                "  Credential Manager opened."
                if open_credential_manager()
                else "  Could not open Credential Manager."
            )
            continue
        if choice == "e":
            if not accounts:
                print("  No usernames to export.")
                continue
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = os.path.join(base.SAVE_DIR, f"sniffer_saved_usernames_{stamp}.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(accounts) + "\n")
            print(f"  Exported usernames only, no passwords: {path}")
            continue
        if not choice.isdigit() or not (1 <= int(choice) <= len(accounts)):
            print("  Invalid selection.")
            continue

        username = accounts[int(choice) - 1]
        while True:
            action = input(
                f"\n  {username}: [u] copy username [p] copy password [r] reveal password "
                "[l] open login [d] delete [b] back: "
            ).strip().lower()

            if action in ("", "b"):
                break
            if action == "u":
                print(
                    "  Username copied."
                    if base.copy_to_clipboard(username)
                    else "  Clipboard copy failed."
                )
                continue
            if action in ("p", "r"):
                credential = read_saved_credential(username)
                if not credential:
                    print("  Could not read that credential.")
                    continue
                _, password = credential
                if action == "p":
                    print(
                        "  Password copied."
                        if base.copy_to_clipboard(password)
                        else "  Clipboard copy failed."
                    )
                else:
                    print(f"  Password: {password}")
                continue
            if action == "l":
                base.copy_to_clipboard(username)
                try:
                    webbrowser.open_new_tab(ROBLOX_LOGIN_URL)
                    print("  Roblox login opened; username copied.")
                except Exception as exc:
                    print(f"  Could not open browser: {exc}")
                continue
            if action == "d":
                confirm = input(f"  Type '{username}' to delete this saved credential: ").strip()
                if confirm != username:
                    print("  Delete cancelled.")
                    continue
                if delete_saved_credential(username):
                    print("  Deleted from Windows Credential Manager.")
                    break
                print("  Delete failed.")
                continue
            print("  Choose u, p, r, l, d, or b.")


def run_main():
    try:
        print(f"{base.APP_NAME} v{APP_VER}".center(55))
        print("(Roblox username generator + availability checker)".center(55))
        print()
        print("Fetching CSRF token...", end=" ")
        tok = base.get_csrf_token()
        print(f"{'OK' if tok else 'FAILED'}\n")

        mode = input(
            "Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist [c]redentials? "
        ).strip().lower()

        if mode == "c":
            saved_accounts_mode()

        elif mode == "m":
            base.manual_lookup_mode()

        elif mode == "w":
            base.wordlist_mode(base.pick_length())

        elif mode == "a":
            length = base.pick_length()
            target = int(input("How many aesthetic names to find? ") or "5")
            max_c = int(input("Max checks? ") or "500")
            found, total = [], 0
            with base.ThreadPoolExecutor(max_workers=base.MAX_WORKERS) as ex:
                while len(found) < target and total < max_c:
                    bs = min(base.MAX_WORKERS, max_c - total)
                    names = [base.generate_aesthetic(length) for _ in range(bs)]
                    for future in base.as_completed({ex.submit(base.smart_check, n): n for n in names}):
                        n, status = future.result()
                        total += 1
                        if status == "available":
                            found.append(n)
                        base.p_prog(n, status, len(found), total)
                    base.time.sleep(base.REQUEST_DELAY)
            print(f"\n\n{'=' * 55}")
            print(f"  AESTHETIC AVAILABLE ({length} chars): {len(found)}")
            print(f"{'=' * 55}")
            for n in found:
                base.print_available(n)
            if found:
                base.claim_available_name(found)
                ans2 = input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != "n":
                    base.save_results(found, f"aesthetic-{length}char")
            print("\n--- made by scarn ---\n")

        elif mode == "s":
            length = base.pick_length()
            target = int(input("How many names to find? ") or "5")
            print("Charset options:")
            print("  [L] Letters only (a-z)")
            print("  [M] Mixed letters+digits (default)")
            print("  [N] Numbers only (0-9)")
            cs_in = input("Choose: ").strip().lower()
            if cs_in == "l":
                charset = base.LETTERS
            elif cs_in == "n":
                charset = base.NUMBERS_ONLY
            else:
                charset = base.CHARSET
            max_c = int(input("Max checks? ") or "500")
            found, total = [], 0
            with base.ThreadPoolExecutor(max_workers=base.MAX_WORKERS) as ex:
                while len(found) < target and total < max_c:
                    bs = min(base.MAX_WORKERS, max_c - total)
                    names = [base.generate_random(length, charset) for _ in range(bs)]
                    for future in base.as_completed({ex.submit(base.smart_check, n): n for n in names}):
                        n, status = future.result()
                        total += 1
                        if status == "available":
                            found.append(n)
                        base.p_prog(n, status, len(found), total)
                    base.time.sleep(base.REQUEST_DELAY)
            print(f"\n\n{'=' * 55}")
            print(f"  SCAN DONE - Checked {total}, found {len(found)} available ({length} chars)")
            print(f"{'=' * 55}")
            for n in found:
                base.print_available(n)
            if not found:
                print("    (none found)")
            if found:
                base.claim_available_name(found)
                ans2 = input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != "n":
                    base.save_results(found, f"scan-{length}char")
            print("\n--- made by scarn ---\n")

        else:
            length = base.pick_length()
            batch = int(input("How many names? ") or "100")
            aesthetic = input("Aesthetic/word-like? [y/N]: ").strip().lower() == "y"
            print("Charset options:")
            print("  [L] Letters only (a-z)")
            print("  [M] Mixed letters+digits (default)")
            print("  [N] Numbers only (0-9)")
            cs_in = input("Choose: ").strip().lower()
            if cs_in == "l":
                charset = base.LETTERS
            elif cs_in == "n":
                charset = base.NUMBERS_ONLY
            else:
                charset = base.CHARSET

            names = [
                base.generate_aesthetic(length)
                if aesthetic
                else base.generate_random(length, charset)
                for _ in range(batch)
            ]
            results = []
            with base.ThreadPoolExecutor(max_workers=base.MAX_WORKERS) as ex:
                for i, future in enumerate(
                    base.as_completed({ex.submit(base.smart_check, n): n for n in names})
                ):
                    results.append(future.result())
                    n, status = results[-1]
                    base.p_prog(
                        n,
                        status,
                        len([r for r in results if r[1] == "available"]),
                        i + 1,
                    )
                    if (i + 1) % base.MAX_WORKERS == 0:
                        base.time.sleep(base.REQUEST_DELAY)

            available = [n for n, status in results if status == "available"]
            aesthetic_names = [n for n in available if base.is_aesthetic(n)]
            random_names = [n for n in available if not base.is_aesthetic(n)]
            print(f"\n\n{'=' * 55}")
            print(f"  RESULTS ({length} chars) - Available: {len(available)}/{batch}")
            print(f"{'=' * 55}")
            if aesthetic_names:
                print(f"\n  AESTHETIC ({len(aesthetic_names)}):")
                for n in aesthetic_names:
                    base.print_available(n, f"({base.is_wordlike(n)}/10)")
            if random_names:
                print(f"\n  RANDOM ({len(random_names)}):")
                for n in random_names:
                    base.print_available(n)
            print(f"\n  TAKEN: {len([r for r in results if r[1] == 'taken'])}")
            other = [r for r in results if r[1] not in ("available", "taken")]
            if other:
                print("  OTHER:")
                for status, count in base.Counter(status for _, status in other).most_common(5):
                    print(f"    {status}: {count}")
            if available:
                base.claim_available_name(available)
                ans2 = input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != "n":
                    base.save_results(available, f"batch-{length}char")
            print("\n--- made by scarn ---\n")

        input("Press Enter to exit...")

    except KeyboardInterrupt:
        print("\n\nExiting.")
        print("--- made by scarn ---")
        input("Press Enter to exit...")


if __name__ == "__main__":
    run_main()
