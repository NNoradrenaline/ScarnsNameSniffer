<div align="center">

# 🔎 Scarn's Name Sniffer

### A fast Roblox username generator and availability checker for Windows.

![Version](https://img.shields.io/badge/version-2.5-blue)
![Python](https://img.shields.io/badge/Python-3.x-yellow?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success)

Generate names, check Roblox username availability, filter for more word-like results, scan custom wordlists, save finds, and securely manage generated signup credentials.

**Made by scarn.**

</div>

---

## ✨ Features

- **Username scanning** — Generate random usernames and check whether they are available.
- **Aesthetic mode** — Generate more pronounceable, word-like names using consonant/vowel patterns and a scoring system.
- **Manual lookup** — Type a specific username and check it immediately.
- **Custom wordlists** — Feed the program a `.txt` file and generate/check variations of your own words.
- **4, 5, and 6 character generation** — Quickly target short usernames.
- **Multiple character sets** — Letters only, letters + numbers, or numbers only.
- **Availability highlighting** — Available names are easy to spot in the terminal.
- **Claim menu** — Pick an available name from a numbered list after a scan.
- **Secure credential saving** — Single-name claims generate a strong password and save the username/password pair in Windows Credential Manager.
- **Saved Accounts menu** — Browse saved usernames, copy or reveal one password on demand, open Roblox login, delete a saved credential, or export usernames only.
- **Browser companion** — Optional Chrome/Edge extension fills birthday, username, and password on Roblox Create Account.
- **Enter-to-submit** — Once the signup form is filled, pressing Enter activates Roblox's normal Create Account / Sign Up button.
- **Save results** — Export available usernames to timestamped text files on your Desktop without storing passwords in plaintext.
- **Safe tab limit** — Bulk-open remains optional with a configurable cap.
- **Concurrent checks** — Uses multiple workers to check batches faster.
- **Rate-limit/error reporting** — Reports Roblox rate limiting, CSRF failures, invalid names, and other request errors.

---

## 🖥️ Example

```text
                 Scarn's Name Sniffer v2.5
       (Roblox username generator + availability checker)

Fetching CSRF token... OK

Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist [c]redentials?
```

### Modes

| Key | Mode | What it does |
|---|---|---|
| `s` | Scan | Randomly generates usernames until it finds the requested number available. |
| `g` | Generate | Generates a batch and checks all names. |
| `a` | Aesthetic | Searches specifically for more word-like generated names. |
| `m` | Manual | Checks usernames you type yourself. |
| `w` | Wordlist | Generates/checks variations from a custom text file. |
| `c` | Credentials | Opens the Saved Accounts menu for Name Sniffer credentials stored in Windows Credential Manager. |

---

## 🆕 What's New in v2.5

- Added a **Saved Accounts / Credentials** menu directly inside the Windows app.
- Saved usernames are listed without dumping passwords onto the screen.
- For one selected credential you can copy the username, copy the password, reveal the password, open Roblox login, or delete the credential.
- Deleting a credential requires typing the username as confirmation.
- Added a usernames-only export option for saved credentials.
- The browser companion now lets you press **Enter** to activate Roblox's normal Create Account / Sign Up button after the form is filled.
- The Enter shortcut does **not** bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox protections.
- The v2.5 Windows build uses `v25_launcher.py` on top of the stable v2.4 scanner core.

## 🚀 Download

The easiest way to use Name Sniffer is the Windows executable.

1. Open the **Releases** section of this repository, or download the latest successful GitHub Actions artifact.
2. Download `ScarnsNameSniffer.exe`.
3. Keep the included `browser-extension` folder if you want signup autofill.
4. Run the EXE and choose a mode.

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. Source is included in this repository for inspection.

---

## 🐍 Run From Source

### Requirements

- Windows 10 or 11
- Python 3
- `requests`

Clone the repository:

```powershell
git clone https://github.com/NNoradrenaline/ScarnsNameSniffer.git
cd ScarnsNameSniffer
```

Install the dependency:

```powershell
python -m pip install requests
```

Run v2.5:

```powershell
python v25_launcher.py
```

The launcher imports the existing `roblox_name_gen.py` scanner core and adds v2.5 account-management features.

---

## 📦 Build the Windows EXE

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build:

```powershell
python -m PyInstaller --onefile --name "ScarnsNameSniffer" --noconfirm v25_launcher.py
```

The executable will be created here:

```text
dist\ScarnsNameSniffer.exe
```

The repository's GitHub Actions workflow builds the EXE automatically and packages the `browser-extension` folder beside it.

---

## 💾 Saved Results

Available usernames can be saved to your Desktop in timestamped files such as:

```text
sniff_2026-08-23_03-55-00.txt
```

Saved scan files contain usernames and scan information, but **not generated account passwords**.

---

## 🔐 Saved Accounts / Credentials

Choose `[c]redentials` from the main menu to browse credentials created by single-name claim mode.

Entries are stored as Windows Generic Credentials using names such as:

```text
ScarnsNameSniffer:exampleuser
```

For a selected username, v2.5 can:

- copy the username
- copy the saved password
- reveal the password on demand
- open Roblox login with the username copied
- delete the saved credential after confirmation
- export the list of usernames without passwords

Credentials are saved **before** Roblox signup finishes, so a saved entry means Name Sniffer prepared credentials for that username. It does not guarantee the Roblox account was successfully created.

---

## 🌐 Claiming a Username

After a scan, Name Sniffer shows a numbered **Claim a Name** menu. Choosing one username generates a strong password, saves the username/password pair in Windows Credential Manager, prepares a one-time autofill handoff for the companion extension, and opens Roblox Create Account.

Bulk-open remains available by entering `b` in the claim menu. Bulk mode does not generate or save account passwords.

---

## 🌐 Autofill Companion

The optional Chrome/Edge companion fills your configured birthday, selected username, and the exact password generated by the Windows app. It clears the one-time credential handoff from the clipboard after reading it and stores only non-secret history.

Once the normal Roblox signup form is filled, press **Enter** to activate the visible Create Account / Sign Up button. If Roblox requires CAPTCHA or another verification step, that protection still works normally and must be completed normally.

The extension source is in `browser-extension/`.

---

## ⚡ Aesthetic Scoring

Aesthetic mode favors names that look more pronounceable or word-like. The score considers common letter pairs, vowel balance, useful starts/endings, consonant/vowel patterns, awkward combinations, and excessive digits.

It is intentionally a heuristic, not an English dictionary check, so sometimes it produces strange little linguistic goblins. That's part of the hunt.

---

## ⚠️ Rate Limits

Name Sniffer uses Roblox's username-validation service. Large or repeated scans may be rate-limited.

If you receive a `ratelimited` result, stop the scan and try again later. Do not use the tool to bypass Roblox limits or platform protections.

---

## 🔐 Privacy

Name Sniffer does **not** require an existing Roblox password, `.ROBLOSECURITY` cookie, or Roblox authentication token.

Generated signup credentials are stored locally under your Windows account when secure saving succeeds. Passwords are not stored in extension history or plaintext scan-result files.

---

## 🛠️ Roadmap

Possible future additions:

- **Favorites / starred names** before claiming one
- **Multi-length scanning** in one run, such as 4 + 5 + 6 characters together
- **Adjustable aesthetic score** and better syllable-based generation
- **Search/filter inside Saved Accounts** for larger credential lists
- **Account status marker** so prepared credentials can later be marked as successfully created
- **Extension health check** that reports whether autofill is installed and responding
- **GUI version** with tabs for Scan, Results, and Saved Accounts
- **Persistent scan presets** for favorite length/charset/aesthetic settings
- Cleaner result ranking and duplicate-history cleanup

---

## ⚖️ Disclaimer

Scarn's Name Sniffer is an unofficial community tool and is **not affiliated with, endorsed by, or sponsored by Roblox Corporation**.

Username availability can change at any time. A name reported as available is not guaranteed to remain available or to be claimable.

Use the project responsibly and follow Roblox's Terms of Use and applicable API/service limits.

---

<div align="center">

### 🔎 Find the name before somebody else does.

**Scarn's Name Sniffer v2.5**

</div>
