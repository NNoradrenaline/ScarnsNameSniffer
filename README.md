<div align="center">

# 🔎 Scarn's Name Sniffer

### A fast Roblox username generator and availability checker for Windows.

![Version](https://img.shields.io/badge/version-2.4-blue)
![Python](https://img.shields.io/badge/Python-3.x-yellow?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success)

Generate names, check Roblox username availability, filter for more word-like results, scan custom wordlists, and save your finds without digging through a browser one name at a time.

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
- **Browser companion** — Optional Chrome/Edge extension can fill birthday, username, and password on Roblox Create Account.
- **Save results** — Export available usernames to timestamped text files on your Desktop without storing passwords in plaintext.
- **Registration helper** — Opens Roblox Create Account for the exact username you selected.
- **Safe tab limit** — Choose how many signup tabs to open, with a default of 10 instead of launching every result at once.
- **Concurrent checks** — Uses multiple workers to check batches faster.
- **Rate-limit/error reporting** — Reports Roblox rate limiting, CSRF failures, invalid names, and other request errors.

---

## 🖥️ Example

```text
                 Scarn's Name Sniffer v2.4
       (Roblox username generator + availability checker)

Fetching CSRF token... OK

Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist?
```

### Modes

| Key | Mode | What it does |
|---|---|---|
| `s` | Scan | Randomly generates usernames until it finds the requested number available. |
| `g` | Generate | Generates a batch and checks all names. |
| `a` | Aesthetic | Searches specifically for more word-like generated names. |
| `m` | Manual | Checks usernames you type yourself. |
| `w` | Wordlist | Generates/checks variations from a custom text file. |

---

## 🆕 What's New in v2.4

- Generates a strong password when you claim a single available username.
- Saves the username/password pair securely in **Windows Credential Manager**.
- Hands the same credentials to the Chrome/Edge companion for autofill.
- Clears the one-time clipboard handoff after the companion reads it.
- Keeps passwords out of plaintext result files and extension history.
- Birthday autofill remains configurable in the companion extension.
- The final **Create Account** click is always left to you.

## 🚀 Download

The easiest way to use Name Sniffer is the Windows executable.

1. Open the **Releases** section of this repository.
2. Download the latest `ScarnsNameSniffer.exe`.
3. Run it.
4. Choose a mode and start sniffing names.

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. If you publish releases, include the source code and checksums so users can verify what they downloaded.

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

Run it:

```powershell
python roblox_name_gen.py
```

---

## 📦 Build the Windows EXE

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build:

```powershell
python -m PyInstaller --onefile --name "ScarnsNameSniffer" --icon "icon.ico" --noconfirm roblox_name_gen.py
```

The executable will be created here:

```text
dist\ScarnsNameSniffer.exe
```

---

## 📃 Wordlist Mode

Create a text file with one word per line:

```text
valor
nova
rift
zero
blade
phase
drift
cobra
```

Start the program, select `w`, choose a username length, and paste the path to your wordlist.

Name Sniffer will create variations, remove duplicates, check them, and separate available results into aesthetic and random groups.

---

## 💾 Saved Results

Available usernames can be saved to your Desktop in timestamped files such as:

```text
sniff_2026-08-23_03-55-00.txt
```

Saved result files contain usernames and scan information, but **not generated account passwords**.

---

## 🌐 Claiming a Username

After a scan, Name Sniffer shows a numbered **Claim a Name** menu. In v2.4, choosing one username generates a strong password, saves the username/password pair in Windows Credential Manager, prepares a one-time autofill handoff for the companion extension, and opens Roblox Create Account.

Bulk-open is still available by entering `b` in the claim menu. You choose the maximum number of tabs, the default remains **10**, and `0` skips opening tabs entirely. Bulk mode does not generate or save account passwords.

Roblox controls its own registration routing and can change it at any time. The companion never submits the form automatically; review the birthday, username, and generated password before creating the account.

---

## ⚡ Aesthetic Scoring

Aesthetic mode favors names that look more pronounceable or word-like. The score considers things such as:

- common letter pairs
- vowel balance
- useful starting and ending combinations
- alternating consonant/vowel patterns
- awkward letter combinations
- excessive digits

It is intentionally a heuristic, not an English dictionary check, so sometimes it produces strange little linguistic goblins. That's part of the hunt.

---

## ⚠️ Rate Limits

Name Sniffer uses Roblox's username-validation service. Large or repeated scans may be rate-limited.

If you receive a `ratelimited` result, stop the scan and try again later. Do not use the tool to bypass Roblox limits or platform protections.

---

## 🔐 Secure account saving

In v2.4, single-name claim mode generates the signup password in the Windows app and saves the username/password pair as a **Generic Credential in Windows Credential Manager** before Roblox opens.

Windows Credential Manager entries use names such as:

```text
ScarnsNameSniffer:exampleuser
```

The browser companion receives the credentials through a one-time clipboard handoff, fills Roblox, and clears that handoff after reading it. The extension keeps only non-secret history such as username, birthday, credential location, and timestamp.

Passwords are not stored in extension history or plaintext result files.

Bulk-open mode does not securely save passwords. Use the numbered single-name claim flow when you want automatic credential saving.

---

## 🌐 Autofill Companion

The optional Chrome/Edge companion can fill the saved birthday, selected username, and the exact password generated by the v2.4 Windows app. It clears the one-time clipboard handoff after reading it and stores only non-secret history. It never presses **Create Account** for you.

The extension source is in `browser-extension/`.

---

## 🔐 Privacy

Name Sniffer does **not** require your Roblox password, `.ROBLOSECURITY` cookie, or existing Roblox authentication token.

Generated signup credentials are stored locally under your Windows account when secure saving succeeds. Do not enter account cookies, existing passwords, authentication tokens, or other private credentials into third-party builds of this project.

---

## 🛠️ Roadmap

Possible future additions:

- Better syllable-based name generation
- Adjustable minimum aesthetic score
- Multi-length scanning in one run
- GUI version
- Persistent settings/config file
- Duplicate-history prevention
- Cleaner result sorting and ranking

---

## 🤝 Contributing

Ideas, bug reports, and pull requests are welcome.

If you find a bug, include:

- what mode you were using
- the options you selected
- the error/status shown
- your Python and Windows version if running from source

---

## ⚖️ Disclaimer

Scarn's Name Sniffer is an unofficial community tool and is **not affiliated with, endorsed by, or sponsored by Roblox Corporation**.

Username availability can change at any time. A name reported as available is not guaranteed to remain available or to be claimable.

Use the project responsibly and follow Roblox's Terms of Use and applicable API/service limits.

---

<div align="center">

### 🔎 Find the name before somebody else does.

**Scarn's Name Sniffer v2.4**

</div>
