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
- **Browser companion included** — The Windows download also contains the Chrome/Edge autofill extension; no separate download is required.
- **Standalone extension download** — GitHub Actions also publishes the autofill companion by itself for users who already have the EXE.
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
- The included browser companion lets you press **Enter** to activate Roblox's normal Create Account / Sign Up button after the form is filled.
- The Enter shortcut does **not** bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox protections.
- The downloadable GitHub Actions bundle contains both the Windows EXE and the `browser-extension` folder.

## 🚀 Download

Open **Actions → Build Windows EXE** and choose the newest successful v2.5 run. You will see two artifacts:

```text
ScarnsNameSniffer-v2.5-Windows
ScarnsNameSniffer-v2.5-Autofill-Extension
```

### Full package

Download **`ScarnsNameSniffer-v2.5-Windows`** if you want everything. After extracting it you will get:

```text
ScarnsNameSniffer.exe
browser-extension/
```

### Extension only

Download **`ScarnsNameSniffer-v2.5-Autofill-Extension`** if you already have Name Sniffer and only need the Chrome/Edge companion.

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. Source is included in this repository for inspection.

---

## 🌐 Install the Autofill Extension

### Chrome

1. Extract the download.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the `browser-extension` folder, or the extracted extension-only artifact folder.
6. Pin **Scarn's Name Sniffer Autofill** if you want quick access to birthday settings.

### Edge

1. Extract the download.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extension folder.

Click the extension icon once, save the account holder's birthday, and leave **Press Enter to submit signup** enabled if you want the keyboard shortcut.

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
python v25_entry.py
```

---

## 📦 Build the Windows EXE

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --name "ScarnsNameSniffer" --noconfirm v25_entry.py
```

The repository's GitHub Actions workflow automatically packages the EXE and extension together and also publishes the extension separately.

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
