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
- **Browser companion included** — The Windows release includes the Chrome/Edge autofill extension.
- **Birthday + username + password autofill** — The companion fills the Roblox Create Account form using your saved birthday and the credentials prepared by Name Sniffer.
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

[s] scan  [a] aesthetic  [g] generate  [m] manual  [w] wordlist\n[x] mutate [p] presets [v] watchlist [r] resume [c] credentials\n[b] exclusions [d] diagnostics [u] updates [q] quit
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
- The included browser companion lets you press **Enter** to activate Roblox's normal Create Account / Sign Up button after the form is filled.
- The Enter shortcut does **not** bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox protections.
- The Windows release includes both the EXE and the browser extension.

---

## 🧠 Advanced Scanner Features

The v2.5 scanner now includes a local search-engine layer around the existing Roblox availability checker:

- **SQLite scan history + smart caching** — fresh results are reused locally instead of wasting another request. Available names expire quickly; taken and inappropriate results live longer; errors and rate-limit responses are never cached.
- **Adaptive concurrency** — starts conservatively and slowly increases workers after healthy batches. Rate limiting and elevated request errors reduce concurrency and trigger cooldowns.
- **Advanced filters** — control digits, underscores, maximum digit count, starting character, vowel requirement, adjacent repeats, and custom excluded patterns.
- **Username ranking** — every available result gets a 0–100 cleanliness/word-likeness score and a label such as Excellent, Great, or Good.
- **Persistent duplicate prevention** — previously checked names live in the SQLite history so repeated scans can reuse valid cached knowledge.
- **Scan presets** — built-in Rare 4, Clean 5, and Mixed 6 presets, plus custom presets saved from your own scan settings.
- **Watchlist** — save interesting usernames and manually recheck the whole watchlist once when you choose.
- **Resume checkpoints** — interrupted target scans save their progress, counts, filters, and settings for later resumption.
- **Live terminal dashboard** — checked, available, taken, inappropriate, other/errors, cache hits, worker count, speed, runtime, and target progress update during scans.
- **TXT + CSV + JSON export** — ranked available results can be exported in all three formats.
- **Scan statistics** — completion summaries include network checks, cache hits, availability rate, average speed, runtime, and best-ranked result.
- **Diagnostics** — checks the SQLite database, state path, Roblox connectivity, CSRF token, clipboard helper, and bundled browser-extension folder.
- **Result browser** — sort available names by score, alphabetically, or digit count before claiming/exporting.
- **Mutation engine** — provide a seed word and generate/check useful substitutions, leetspeak variants, prefixes, suffixes, and length-normalized mutations.
- **Excluded-pattern list** — maintain local substring/regex rules that reject unwanted generated names before any network request.
- **Portable mode** — rename `portable.flag.example` to `portable.flag` beside the EXE. Scanner state and exports then live under a local `data/` directory beside the app.
- **Update checker** — checks the GitHub Releases API and can open the Releases page when a newer version is available. It never silently self-updates.
- **Automated tests** — GitHub Actions compiles all v2.5 Python entrypoints and runs the pytest suite before building the Windows EXE.

### Advanced menu

```text
[s] scan       [a] aesthetic    [g] generate    [m] manual    [w] wordlist
[x] mutate     [p] presets      [v] watchlist   [r] resume    [c] credentials
[b] exclusions [d] diagnostics  [u] updates     [q] quit
```

### Local scanner data

Normal Windows mode stores persistent scanner data under:

```text
%LOCALAPPDATA%\ScarnsNameSniffer
```

This contains the SQLite history database, presets, excluded patterns, and resume checkpoint. Passwords for prepared Roblox signup credentials remain handled separately by Windows Credential Manager.

---

## 🚀 Download

**Most users should download Name Sniffer from the GitHub Releases page. You do not need Python, PyInstaller, or any build tools.**

1. Open the repository's **Releases** section.
2. Open the latest release, currently **v2.5**.
3. Download the Windows package or the files attached to the release.
4. Extract the download.
5. Run `ScarnsNameSniffer.exe`.

The v2.5 release includes the Windows app and the browser autofill companion.

Typical release files include:

```text
ScarnsNameSniffer.exe
ScarnsNameSniffer-Autofill-v2.5.zip
```

If you only want the browser companion, download `ScarnsNameSniffer-Autofill-v2.5.zip` from the release.

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. The source code is public in this repository for inspection.

---

## 🌐 Install the Autofill Extension

### Chrome

1. Download `ScarnsNameSniffer-Autofill-v2.5.zip` from the latest GitHub Release.
2. Extract the ZIP to a folder.
3. Open `chrome://extensions`.
4. Turn on **Developer mode**.
5. Click **Load unpacked**.
6. Select the extracted extension folder containing `manifest.json`.
7. Pin **Scarn's Name Sniffer Autofill** if you want quick access to birthday settings.

### Edge

1. Download and extract `ScarnsNameSniffer-Autofill-v2.5.zip` from the latest GitHub Release.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted extension folder containing `manifest.json`.

Click the extension icon once, save the account holder's birthday, and leave **Press Enter to submit signup** enabled if you want the keyboard shortcut.

---

## 🧑‍💻 Developers / Run From Source

Regular users should use the prebuilt files from **Releases**. This section is only for developers who want to inspect or modify the source.

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

Run v2.5 from source:

```powershell
python v25_entry.py
```

You do **not** need to build the EXE yourself for normal use. Download the ready-to-run executable from **GitHub Releases** instead.

---

## 🔐 Saved Accounts / Credentials

Choose `[c]redentials` from the main menu to browse credentials created by single-name claim mode. Entries are stored as Windows Generic Credentials using names such as `ScarnsNameSniffer:exampleuser`.

For a selected username, v2.5 can copy the username, copy or reveal the saved password, open Roblox login, delete the credential after confirmation, or export a usernames-only list.

Credentials are saved **before** Roblox signup finishes, so a saved entry means Name Sniffer prepared credentials for that username. It does not guarantee the Roblox account was successfully created.

---

## ⚠️ Rate Limits

Name Sniffer uses Roblox's username-validation service. Large or repeated scans may be rate-limited. If you receive a `ratelimited` result, stop the scan and try again later. Do not use the tool to bypass Roblox limits or platform protections.

---

## 🔐 Privacy

Name Sniffer does **not** require an existing Roblox password, `.ROBLOSECURITY` cookie, or Roblox authentication token. Generated signup credentials are stored locally under your Windows account when secure saving succeeds. Passwords are not stored in extension history or plaintext scan-result files.

---

## ⚖️ Disclaimer

Scarn's Name Sniffer is an unofficial community tool and is **not affiliated with, endorsed by, or sponsored by Roblox Corporation**.

Username availability can change at any time. Use the project responsibly and follow Roblox's Terms of Use and applicable API/service limits.

---

<div align="center">

### 🔎 Find the name before somebody else does.

**Scarn's Name Sniffer v2.5**

</div>
