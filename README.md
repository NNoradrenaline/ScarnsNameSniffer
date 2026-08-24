<div align="center">

# 🔎 Scarn's Name Sniffer

### A fast Roblox username generator and availability checker for Windows.

![Version](https://img.shields.io/badge/version-2.0-blue)
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
- **Automatic clipboard copy** — Available usernames found in manual lookup are copied for quick pasting.
- **Save results** — Export available usernames to timestamped text files on your Desktop.
- **Browser helper** — Can open Roblox after a scan, while keeping the username ready to copy/paste manually.
- **Safe tab limit** — Choose how many signup tabs to open, with a default of 10 instead of launching every result at once.
- **Concurrent checks** — Uses multiple workers to check batches faster.
- **Rate-limit/error reporting** — Reports Roblox rate limiting, CSRF failures, invalid names, and other request errors.

---

## 🖥️ Example

```text
                 Scarn's Name Sniffer v2.0
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

## 🚀 Download

The easiest way to use Name Sniffer is the Windows executable.

Download `ScarnsNameSniffer.exe` from this repository after the Windows build is uploaded.

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. The source code is included in this repository so you can inspect or build it yourself.

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

## 🌐 Browser Behavior

Roblox currently may redirect signup links back to the Roblox home page, including links opened from the terminal. This is a Roblox-side routing behavior, so **v2.0 does not guarantee that clicking an available username will land on a working signup form**.

Manual lookup still copies an available username to the clipboard, and scan results can be saved to a text file for easy copy/paste. When the browser helper is used, the program asks how many tabs to launch. The default is **10**, and `0` skips opening tabs entirely.

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

**Scarn's Name Sniffer v2.0**

</div>
