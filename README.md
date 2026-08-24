<div align="center">

# 🔎 Scarn's Name Sniffer

### A fast Roblox username generator and verified availability checker for Windows.

![Version](https://img.shields.io/badge/version-2.6-blue)
![Python](https://img.shields.io/badge/Python-3.x-yellow?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-active-success)

Generate, rank, verify, cache, resume, and watch Roblox username candidates without keeping passwords in plaintext.

**Made by scarn.**

</div>

---

## ⚡ What's New in v2.6

v2.6 replaces the old fixed scanner loop with a more serious scanning engine:

- **Two-stage availability verification** — a candidate must pass Roblox username validation and a second username lookup before it is labeled `VERIFIED AVAILABLE`.
- **Adaptive concurrency** — starts conservatively and changes worker count based on latency and rate-limit responses instead of hammering at a fixed thread count.
- **SQLite cache** — recent checks are cached locally for 15 minutes so repeated names do not waste requests.
- **Resume interrupted scans** — Ctrl+C pauses safely and writes a checkpoint. Choose `[r]esume` later to continue.
- **Live performance metrics** — throughput, ETA, worker count, average API latency, verified count, unverified count, and cache hits are shown while scanning.
- **Watchlist** — save taken names with High / Normal / Low priority and re-check them later for status changes.
- **Multi-length scanning** — scan 4, 5, and 6 character candidates together, such as `4,5,6`.
- **Ranked candidate generation** — generates multiple candidates and spends checks on the strongest-scoring option instead of blindly using the first random string.
- **0–100 name quality score** — verified results are sorted by a cleaner ranking score.
- **Built-in diagnostics** — checks the local database, Windows Credential Manager API, clipboard helper, browser companion files, and Roblox username API connectivity.
- **Structured exports** — v2.6 sessions can export TXT, CSV, and JSON.

The database lives under your Windows user profile in `ScarnsNameSniffer/sniffer.db`. It stores username checks, scan checkpoints, watchlist entries, and non-secret scan metadata. **Passwords are never stored in SQLite.**

---

## 🖥️ v2.6 Menu

```text
                     Scarn's Name Sniffer v2.6
                    Verified username scanning engine

  [s] smart scan     [g] generated batch   [a] aesthetic scan
  [m] manual lookup  [w] watchlist         [r] resume scan
  [c] credentials    [d] diagnostics       [l] legacy wordlist
  [q] quit
```

### Verified results

v2.6 deliberately distinguishes these states:

```text
VERIFIED AVAILABLE ✓   Both checks agree the name is available.
POSSIBLY AVAILABLE ⚠   Primary validation passed, but verification could not finish.
taken                   Roblox resolves the username as already used.
ratelimited             Roblox asked the scanner to slow down.
```

Only `VERIFIED AVAILABLE` names count toward the scan target.

---

## 🚀 Download

**Normal users should download Name Sniffer from GitHub Releases. You do not need Python, PyInstaller, or build tools.**

1. Open the repository's **Releases** section.
2. Open the newest v2.6 release once published.
3. Download the Windows package or attached release files.
4. Extract the download.
5. Run `ScarnsNameSniffer.exe`.

Typical v2.6 release files:

```text
ScarnsNameSniffer.exe
ScarnsNameSniffer-Autofill-v2.6.zip
```

The GitHub Actions package is also built as:

```text
ScarnsNameSniffer-v2.6-Windows
ScarnsNameSniffer-v2.6-Autofill-Extension
```

> Windows SmartScreen may warn about independently distributed executables that are not code-signed. The source is public in this repository for inspection.

---

## 🔎 Smart / Aesthetic Scanning

Choose one or several lengths:

```text
Lengths [4/5/6 or comma list, default 5]: 4,5,6
```

Then choose the number of **verified** names you want and a maximum number of checks. During a scan you will see live stats similar to:

```text
  1842/5000  verified:7  maybe:1  18.4/s  ETA 2m 51s  workers:9  lat:188ms  cache:213
```

If Roblox begins returning rate-limit responses, v2.6 automatically reduces concurrency and cools down before continuing. It does not attempt to bypass Roblox rate limits.

---

## ⏯ Resume Interrupted Scans

Press `Ctrl+C` during a v2.6 smart/aesthetic scan. Name Sniffer saves:

- scan configuration
- number checked
- verified names already found
- unverified candidates
- checkpoint timestamp

Return to the main menu later and choose `[r]esume`.

---

## ★ Watchlist

Choose `[w]atchlist` to track names you care about.

Priorities:

```text
1 = HIGH
2 = NORMAL
3 = LOW
```

Use **Check all** to run the current list through the same cache and adaptive verification engine. If a result changed since the previous check, Name Sniffer marks it `CHANGED!`.

The watchlist does not run hidden background checks. Re-checks happen when you request them.

---

## 🩺 Diagnostics

Choose `[d]iagnostics` to inspect:

- SQLite database access
- Windows Credential Manager API
- Windows clipboard helper
- bundled browser-extension manifest
- Roblox username API response and latency

This makes it much easier to tell whether a problem is the scanner, Windows, the browser companion, or Roblox itself.

---

## 🔐 Saved Accounts / Credentials

The v2.5 secure credential system remains in v2.6.

Choose `[c]redentials` to list credentials created by single-name claim mode. Entries are Windows Generic Credentials such as:

```text
ScarnsNameSniffer:exampleuser
```

For one selected account you can copy the username, copy or reveal the password, open Roblox login, delete the credential after confirmation, or export usernames only.

Credentials are saved before signup finishes, so a saved credential means Name Sniffer prepared that username/password pair. It does not prove the Roblox account was successfully created.

---

## 🌐 Autofill Companion v2.6

The optional Chrome/Edge extension fills the saved birthday, selected username, and generated password on Roblox Create Account.

### Chrome

1. Download `ScarnsNameSniffer-Autofill-v2.6.zip` from Releases.
2. Extract it.
3. Open `chrome://extensions`.
4. Enable **Developer mode**.
5. Click **Load unpacked**.
6. Select the folder containing `manifest.json`.

### Edge

Use the same process from `edge://extensions`.

The **Press Enter to submit signup** option is enabled by default. It activates Roblox's normal visible signup button only after the form is filled. It does not bypass CAPTCHA, verification, disabled buttons, or rate limits.

---

## 🧑‍💻 Developers / Run From Source

Regular users should use **Releases**.

```powershell
git clone https://github.com/NNoradrenaline/ScarnsNameSniffer.git
cd ScarnsNameSniffer
python -m pip install -r requirements.txt
python v26_entry.py
```

v2.6 uses Python's built-in `sqlite3`; no separate database dependency is required.

---

## 🔐 Privacy

Name Sniffer does **not** require an existing Roblox password, `.ROBLOSECURITY` cookie, or Roblox authentication token.

- Generated signup passwords stay in **Windows Credential Manager** when secure saving succeeds.
- SQLite stores username/check metadata, not passwords.
- Scan exports contain check results and scores, not saved account passwords.
- Extension history remains non-secret metadata only.

---

## ⚠️ Rate Limits

Name Sniffer uses Roblox services to validate usernames. v2.6 reduces concurrency and pauses when rate limiting is detected. Do not use the project to evade Roblox limits or other platform protections.

---

## ⚖️ Disclaimer

Scarn's Name Sniffer is an unofficial community tool and is **not affiliated with, endorsed by, or sponsored by Roblox Corporation**.

Username availability can change at any time. A verified result is a stronger check, not a guarantee that a username will remain claimable.

Use the project responsibly and follow Roblox's Terms of Use and applicable service limits.

---

<div align="center">

### 🔎 Find the name before somebody else does.

**Scarn's Name Sniffer v2.6**

</div>
