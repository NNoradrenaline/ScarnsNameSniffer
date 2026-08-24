<div align="center">

# 🔎 Scarn's Name Sniffer

### A fast Roblox username generator and availability checker for Windows.

![Version](https://img.shields.io/badge/version-2.1-blue)
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
- **Automatic clipboard copy** — The selected username is copied for quick pasting into Roblox.
- **Save results** — Export available usernames to timestamped text files on your Desktop.
- **Registration helper** — Opens Roblox registration after copying the exact username you selected.
- **Safe tab limit** — Choose how many signup tabs to open, with a default of 10 instead of launching every result at once.
- **Concurrent checks** — Uses multiple workers to check batches faster.
- **Rate-limit/error reporting** — Reports Roblox rate limiting, CSRF failures, invalid names, and other request errors.

---

## 🖥️ Example

```text
                 Scarn's Name Sniffer v2.1
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

## 🆕 What's New in v2.1

- Replaced broken clickable signup links with a numbered claim menu.
- Select one available username and copy it automatically.
- Opens Roblox's registration route for the selected name.
- Keeps bulk-open as an optional fallback instead of the default workflow.
- Keeps the configurable 10-tab safety limit.

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

Saved files include the app version, scan mode, date, results, and the `made by scarn` signature.

---

## 🌐 Claiming a Username

v2.1 removes the old clickable terminal username links that could bounce back to the Roblox homepage. After a scan, Name Sniffer now shows a numbered **Claim a Name** menu. Pick a result and the tool copies that exact username to your clipboard, then opens Roblox's registration route so you can paste it with `Ctrl+V`.

Bulk-open is still available by entering `b` in the claim menu. You choose the maximum number of tabs, the default remains **10**, and `0` skips opening tabs entirely.

Roblox controls its own registration routing and can change it at any time. If the registration page changes or redirects, the selected username is still copied to your clipboard so the availability result is not lost.

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

## 🔐 Privacy

Name Sniffer does **not** require your Roblox password or `.ROBLOSECURITY` cookie.

Do not enter account cookies, passwords, authentication tokens, or other private credentials into third-party builds of this project.

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

**Scarn's Name Sniffer v2.1**

</div>
