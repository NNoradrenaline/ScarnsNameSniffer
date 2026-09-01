# SCARN'S NAME SNIFFER — COMPLETE SOURCE + AI/DEVELOPER HANDOFF

> Repository: `NNoradrenaline/ScarnsNameSniffer`
> Branch snapshot: `main`
> Tree SHA at handoff creation: `2e4e0a39a76723549804b3f77dd75923fe0b6c7a`
>
> This is intentionally one self-contained handoff file. Give this file to
> another AI or developer and tell them to read it before editing the project.

---

# 1. WHAT THE PROJECT IS

Scarn's Name Sniffer is a Windows-oriented Roblox username search engine plus a
credential/signup companion and Chrome/Edge autofill extension.

The project has four main layers:

1. **Scanner/search engine**
   - generates username candidates
   - filters candidates locally
   - uses persistent cache/history
   - classifies usernames through Roblox lookup/validation paths
   - ranks available names
   - supports presets, watchlist, resume, mutation, wordlists, exports, and diagnostics

2. **High-throughput networking**
   - first-stage multi-username lookup in batches up to 100
   - unresolved survivors go to the single-name signup validator
   - connection pooling
   - adaptive concurrency
   - streaming/pipelining so survivor validation begins as soon as a bulk result completes
   - early stop when the requested number of available names is reached
   - 429/rate-limit backoff rather than evasion

3. **Windows prepared-account helper**
   - generates credentials
   - stores prepared account passwords in Windows Credential Manager
   - stores non-secret metadata separately
   - opens/hands off to normal Roblox signup

4. **Manifest V3 browser extension**
   - fills the Roblox signup form
   - optionally invokes the normal signup control after filling
   - saves one recovery email
   - after signup can confirm the expected username, open Account Info, use Add Email,
     fill the email/password if requested, request the verification email, then stop
   - email verification itself remains manual
   - refuses to replace/change an existing email
   - temporary signup password for the Add Email dialog is kept in background-owned
     chrome.storage.session, not persistent extension local storage

---

# 2. CORE FILE MAP

## v25_entry.py
Packaged EXE entrypoint. Imports the v2.5 scanner and calls its main entry.

## v25_scanner.py
Primary interactive UI and orchestration layer.

Main modes:
- scan
- aesthetic scan
- generate/check
- manual lookup
- wordlist
- mutation
- presets
- watchlist
- resume
- credentials
- exclusions
- diagnostics
- update check

This file coordinates `v25_engine.py`, `v25_fastnet.py`,
`roblox_name_gen.py`, and `v25_launcher.py`.

## v25_fastnet.py
High-throughput network layer.

Important behavior:
- <=100 usernames per bulk request
- persistent HTTP session
- enlarged connection pool
- adaptive bulk concurrency
- yields results as soon as each batch finishes
- exposes Retry-After/rate-limit metadata
- does not rotate proxies or evade rate limits

## v25_engine.py
Local engine/persistence layer.

Contains:
- app paths / portable mode
- SQLite history
- WAL/cache/mmap tuning
- batched reads/writes
- status-aware cache TTLs
- filters and exclusions
- scoring/ranking
- mutation engine
- presets
- watchlist
- resume checkpoints
- TXT/CSV/JSON export
- adaptive validator worker controller
- duplicate-free finite username-space permutation generator

## roblox_name_gen.py
Original generator + Roblox request primitives.

Still used by the v2.5 scanner for:
- character sets/generators
- CSRF handling
- authoritative survivor validation
- several helper routines

## v25_launcher.py
Prepared-account and Windows integration layer.

Contains:
- password generation
- Windows Credential Manager integration
- prepared account metadata
- browser/signup handoff
- saved credential viewer/copy/delete behavior

---

# 3. MAX-SPEED SCAN PIPELINE

```text
generate candidates
        |
        v
local filters / structural pruning
        |
        v
batched SQLite cache lookup
        |
        +--> fresh cache -> classify with zero HTTP requests
        |
        v
uncached names -> <=100-name bulk lookup batches
        |
        v
several bulk requests may be in flight
        |
        v
FIRST completed bulk response
        |
        +--> returned usernames -> TAKEN
        |
        +--> unresolved survivors
                    |
                    v
          single-name signup validator
                    |
              available / invalid / inappropriate / etc.
```

Critical latency behavior:
- survivor validation begins immediately when a bulk batch completes
- it does not wait for the entire large scan window
- once the requested available-name target is reached, later work is not launched
  and queued work can be cancelled

**Correctness invariant:** a username missing from the bulk response is NOT
automatically available. It must still pass the single-name signup validator.

---

# 4. CACHE / SQLITE

Normal state location:

```text
%LOCALAPPDATA%\ScarnsNameSniffer
```

Portable mode is enabled with a `portable.flag` beside the app and moves scanner
state under a local `data/` directory.

The history database stores username status/metadata. It does not store prepared
account passwords.

Cache TTLs are status-aware:
- taken/stable results can persist longer
- available results expire sooner
- transient errors/429/unknown states should not become long-lived cached truth

SQLite optimizations are deliberate:
- WAL
- synchronous NORMAL
- memory temp storage
- mmap/cache tuning
- batched SELECTs
- batched commits

---

# 5. DUPLICATE-FREE GENERATION

Normal high-volume scans can use `UniqueSpaceGenerator`.

It walks a randomized permutation of the finite candidate space. Every generated
candidate is unique by construction, avoiding:
- repeated random candidates
- a giant growing duplicate set
- wasted network work

Its state can be snapshotted for resume.

Do not casually replace this with naive repeated random generation for large scans.

---

# 6. ADAPTIVE CONCURRENCY

There are separate controllers for:

1. bulk lookup concurrency in `v25_fastnet.py`
2. individual survivor-validator concurrency in `v25_engine.py`

Healthy rounds ramp concurrency upward. 429/rate-limit or elevated errors reduce it.

The goal is shortest sustainable wall-clock time while honoring service rate controls.

---

# 7. TERMINAL PERFORMANCE

The dashboard is intentionally throttled. Printing/redrawing once per classified
username becomes a real bottleneck at high throughput.

Available usernames can still be surfaced immediately while the full dashboard
refresh is bounded.

---

# 8. FILTERS / RANKING / MUTATION

The engine supports filters for:
- digits
- underscores
- max digit count
- starting letter
- vowel requirement
- adjacent repeated characters

Excluded patterns are applied locally before network work.

Username scoring is presentation/ranking metadata. The fast path avoids wasting
score calculations on dead-end results when the score will never be shown.

Mutation mode generates variations of a seed word/name and ranks/checks them.

---

# 9. PRESETS / WATCHLIST / RESUME / EXPORT

Presets:
- built-in scan configurations
- user-saved configurations

Watchlist:
- persistent interesting names
- manually requested rechecks

Resume:
- periodically saves target-scan progress
- saves counters, elapsed time, settings, found names, and generator state
- checkpoint writes are intentionally throttled to reduce disk chatter

Exports:
- TXT
- CSV
- JSON

---

# 10. PASSWORD / CREDENTIAL STORAGE

Prepared Roblox account passwords belong in Windows Credential Manager.

Do not move them into:
- scanner SQLite
- plaintext JSON/JSONL
- normal logs
- persistent browser extension local storage

The browser extension may temporarily need the current generated password after
signup to satisfy Roblox's Add Email dialog. That temporary copy is stored only in
extension session storage owned by the background worker and is cleared/expired.

---

# 11. BROWSER EXTENSION

## manifest.json
Manifest V3 wiring, permissions, host permissions, popup, service worker, and
content scripts.

## popup.html / popup.js
Stores UI settings:
- birthday
- recovery email
- auto-add-email toggle
- enter-to-submit toggle

## content.js
Runs on Roblox Create Account.

Responsibilities:
- credential handoff/autofill
- birthday fill
- helper panel
- non-secret account history
- arm optional post-signup email job

## background.js
Owns:
- authenticated-user request
- temporary signup secret in chrome.storage.session
- temporary secret retrieval/clear

## enter-submit.js
Optional normal signup submission helper after autofill.

It should not bypass disabled controls, CAPTCHA, verification gates, or rate limits.

## email.js
Post-signup email helper:

```text
pending email job
     |
     v
confirm logged-in Roblox username == expected username
     |
     +--> mismatch -> pause/stop
     |
     v
open Account Info
     |
     v
find Add Email
     |
     +--> Update/Change/Remove Email -> STOP
     |
     v
fill saved email
     |
     v
fill temporary password if Roblox asks
     |
     v
normal Add Email / Send Verification action
     |
     v
tell user to check inbox
     |
     v
STOP
```

It does not read the inbox or complete email verification.

---

# 12. BUILD / TEST

Primary workflow:
`.github/workflows/build-windows.yml`

It validates Python, validates extension JavaScript/manifest, runs pytest, builds
the Windows EXE with PyInstaller, stages the Windows package, and stages/zips the
extension.

Typical source setup:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python v25_entry.py
```

Tests:

```bat
python -m pip install pytest
python -m pytest -q
```

Focused:

```bat
python -m pytest tests/test_v25_engine.py tests/test_v25_fastnet.py tests/test_v25_scanner.py -q
python -m pytest tests/test_extension_email.py -q
```

Extension syntax when Node is installed:

```bat
node --check browser-extension/background.js
node --check browser-extension/content.js
node --check browser-extension/email.js
node --check browser-extension/enter-submit.js
node --check browser-extension/popup.js
```

---

# 13. EDIT MAP

Scanner speed:
- v25_scanner.py
- v25_fastnet.py
- v25_engine.py
- roblox_name_gen.py
- corresponding scanner/fastnet tests

Generation:
- v25_engine.py
- roblox_name_gen.py
- generation helpers in v25_scanner.py

Ranking:
- score_username() and related engine code

Cache/database:
- HistoryStore + TTL helpers in v25_engine.py

Main menu:
- run_main() and mode functions in v25_scanner.py

Prepared credentials:
- v25_launcher.py

Browser signup autofill:
- browser-extension/content.js
- browser-extension/enter-submit.js
- browser-extension/manifest.json

Post-signup email:
- browser-extension/email.js
- browser-extension/background.js
- browser-extension/popup.js
- browser-extension/popup.html
- browser-extension/manifest.json

Build/release:
- .github/workflows/build-windows.yml

---

# 14. INVARIANTS AN EDITOR SHOULD PRESERVE

1. Bulk lookup misses still require individual validation.
2. Prepared passwords do not go into scanner history/database.
3. Extension temporary password remains session-only/background-owned.
4. Existing account email is not automatically replaced.
5. Email verification remains a manual inbox action.
6. Speed work should preserve 429/rate-limit backoff.
7. Normal large scans should retain duplicate-free generation.
8. Dashboard throttling is a performance feature.
9. Transient network failures should not become sticky cache truth.
10. DOM selectors should be semantic/defensive, not screen coordinates.
11. Early-stop/time-to-target behavior is part of scanner performance.
12. Changes should update/add regression tests.

---

# 15. FILES EMBEDDED IN THIS HANDOFF

- `.github/workflows/build-windows.yml`
- `.gitignore`
- `README.md`
- `browser-extension/README.md`
- `browser-extension/background.js`
- `browser-extension/content.js`
- `browser-extension/email.js`
- `browser-extension/enter-submit.js`
- `browser-extension/manifest.json`
- `browser-extension/popup.html`
- `browser-extension/popup.js`
- `docs/index.html`
- `portable.flag.example`
- `requirements.txt`
- `roblox_name_gen.py`
- `tests/test_extension_email.py`
- `tests/test_v25_engine.py`
- `tests/test_v25_fastnet.py`
- `tests/test_v25_scanner.py`
- `v25_engine.py`
- `v25_entry.py`
- `v25_fastnet.py`
- `v25_launcher.py`
- `v25_scanner.py`

---

# 16. COMPLETE VERBATIM SOURCE SNAPSHOT

The following sections are appended verbatim from the repository snapshot above.


---

## FILE: `.github/workflows/build-windows.yml`

Blob SHA: `f116cefe1c4163978c7e5a2e0155f6b362936454`

~~~~~yaml
name: Build Windows EXE

# v2.5 clean build: never commits or pushes from inside GitHub Actions.
on:
  push:
    branches: [main]
    paths:
      - "roblox_name_gen.py"
      - "v25_launcher.py"
      - "v25_scanner.py"
      - "v25_engine.py"
      - "v25_fastnet.py"
      - "tests/**"
      - "portable.flag.example"
      - "v25_entry.py"
      - "requirements.txt"
      - "icon.ico"
      - "browser-extension/**"
      - ".github/workflows/build-windows.yml"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Verify source
        shell: pwsh
        run: |
          python -m py_compile roblox_name_gen.py
          python -m py_compile v25_launcher.py
          python -m py_compile v25_scanner.py
          python -m py_compile v25_engine.py
          python -m py_compile v25_fastnet.py
          python -m py_compile v25_entry.py
          node --check browser-extension/background.js
          node --check browser-extension/content.js
          node --check browser-extension/email.js
          node --check browser-extension/enter-submit.js
          node --check browser-extension/popup.js
          python -c "import json; json.load(open('browser-extension/manifest.json', encoding='utf-8'))"

      - name: Install dependencies
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m pip install pyinstaller
          python -m pip install pytest

      - name: Run test suite
        shell: pwsh
        run: |
          python -m pytest -q

      - name: Build Scarn's Name Sniffer v2.5
        shell: pwsh
        run: |
          if (Test-Path "icon.ico") {
            python -m PyInstaller --onefile --clean --noconfirm --name "ScarnsNameSniffer" --icon "icon.ico" v25_entry.py
          } else {
            python -m PyInstaller --onefile --clean --noconfirm --name "ScarnsNameSniffer" v25_entry.py
          }

      - name: Stage v2.5 package
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path package | Out-Null
          Copy-Item dist/ScarnsNameSniffer.exe package/ScarnsNameSniffer.exe
          Copy-Item browser-extension package/browser-extension -Recurse
          Copy-Item portable.flag.example package/portable.flag.example
          Compress-Archive -Path browser-extension\* -DestinationPath package\ScarnsNameSniffer-Autofill-v2.5.zip -Force
          Compress-Archive -Path browser-extension\* -DestinationPath ScarnsNameSniffer-Autofill-v2.5.zip -Force

      - name: Upload full Windows + extension bundle
        uses: actions/upload-artifact@v4
        with:
          name: ScarnsNameSniffer-v2.5-Windows
          path: package
          if-no-files-found: error

      - name: Upload release-ready extension ZIP
        uses: actions/upload-artifact@v4
        with:
          name: ScarnsNameSniffer-v2.5-Autofill-Extension
          path: ScarnsNameSniffer-Autofill-v2.5.zip
          if-no-files-found: error
~~~~~


---

## FILE: `.gitignore`

Blob SHA: `fa9abd56bde89b545bb925c36fb288672c0e5c5d`

~~~~~text
__pycache__/
*.py[cod]
build/
dist/
*.spec
*.log
.env
.venv/
venv/
*.pyc
.pytest_cache/
data/
portable.flag
~~~~~


---

## FILE: `README.md`

Blob SHA: `8b98f42978ea118fed3a7026294779891d8dc49d`

~~~~~markdown
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

## ⚡ Turbo scanning pipeline

Name Sniffer v2.5 now uses a two-stage network pipeline designed to maximize useful throughput without evading Roblox limits:

1. **Batch cache lookup** — up to 100 candidates are checked against the local SQLite history in one query.
2. **Official bulk existence lookup** — uncached candidates are sent to Roblox's `users.roblox.com/v1/usernames/users` endpoint in batches of up to 100. Names returned by that endpoint are immediately classified as taken.
3. **Survivor validation** — only names not resolved as existing users are sent through the signup username validator to distinguish available, inappropriate, reserved, or invalid names.
4. **Batch database commit** — results are written to SQLite in groups instead of committing once per username.
5. **AIMD validator concurrency** — individual validation starts aggressively, ramps after healthy waves, and cuts concurrency sharply after rate-limit responses.
6. **Connection pooling** — the validator HTTP pool is expanded beyond the default Requests pool size.
7. **Throttled terminal rendering** — the live dashboard refreshes at a bounded rate so console output does not become the scanner's bottleneck.

For taken-heavy scans, this can dramatically increase **usernames classified per actual HTTP request**. The completion screen reports:

```text
Usernames classified
Network usernames
Actual HTTP requests
Bulk lookup requests
Resolved by bulk
Individual validators
Effective density (usernames / HTTP request)
Average throughput (usernames / second)
```

The bulk lookup is only an existence prefilter. A name missing from the bulk response is **never assumed available**; it still goes through signup validation before being shown as available.

Roblox `429 Too Many Requests` responses are respected. Name Sniffer uses cooldown/backoff behavior and does not use proxies, IP rotation, or other rate-limit-evasion techniques.

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
~~~~~


---

## FILE: `browser-extension/README.md`

Blob SHA: `1c02e85279168f6001934fa2ad333c1ec5cf93b1`

~~~~~markdown
# Scarn's Name Sniffer Autofill Companion v2.5.1

This optional Chrome/Edge extension works with the Name Sniffer v2.5 Windows EXE.

When you choose a single name in Name Sniffer, the Windows app generates a strong password, saves the username/password pair in Windows Credential Manager, prepares a one-time clipboard handoff, and opens Roblox Create Account. The companion then:

- reads the one-time username/password handoff from the clipboard
- fills the Roblox username field automatically
- fills the exact password already saved by the Windows app
- clears the one-time clipboard handoff after reading it
- fills your saved birthday automatically
- records only non-secret account history locally (username, birthday, timestamp, and credential location)
- shows a small panel where you can reveal or copy the generated password
- lets you press **Enter** to activate Roblox's normal **Create Account / Sign Up** button once the form is filled

Enter-to-submit defaults to **on**. Click the extension icon and uncheck **Press Enter to submit signup** if you want to disable it.

The Enter shortcut does not bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox checks. It only performs the same normal button activation you could do with the mouse.

Passwords are not stored in extension history or plaintext files. When secure saving succeeds, the password is stored by Windows Credential Manager under the current Windows account.

## Auto-add recovery email

The extension can optionally add one recovery email after a newly created account signs in.

1. Click the extension icon.
2. Enter your recovery email.
3. Enable **Automatically add email after signup**.
4. Save settings.
5. Use Name Sniffer normally.

After signup, the helper:

- waits until Roblox reports that the newly prepared username is the account currently logged in
- opens **Settings > Account Info**
- uses the normal **Add Email** control
- fills the saved email address
- fills the temporary signup password only if Roblox asks for it
- activates Roblox's normal **Add Email / Send Verification** button
- stops and tells you to check your inbox

The extension **does not read your inbox, click the verification link, enter an emailed code, or bypass any Roblox verification step**. You complete verification manually from your email.

The helper also refuses to use **Update Email / Change Email / Remove Email**. If an account already appears to have an email, it stops instead of replacing it.

The saved email is stored in Chrome/Edge extension local storage. A signup password needed by the Add Email dialog is kept only in extension **session** storage behind the background service worker, expires after 15 minutes, and is cleared after the verification request.

## Install from Releases

Download `ScarnsNameSniffer-Autofill-v2.5.zip` from the project's GitHub Releases page and extract it before loading the extension.

## Set your birthday

1. Click the **Scarn's Name Sniffer Autofill** extension icon in Chrome or Edge.
2. Choose the account holder's actual birthday.
3. Optionally enter a recovery email and enable **Automatically add email after signup**.
4. Click **Save settings**.
5. Leave **Press Enter to submit signup** enabled if you want the Enter shortcut.
6. Run Name Sniffer normally.

## Install in Chrome

1. Extract the extension ZIP to a folder.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

## Install in Edge

1. Extract the extension ZIP to a folder.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

After installation, click the extension icon once to save the birthday. Then choose an available name in Name Sniffer. Roblox Create Account should open with the username, password, and birthday filled in. Press **Enter** when you are ready to submit the normal Roblox form.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.

## Secure account storage

For single-name claim mode, passwords are saved by the Windows app in Windows Credential Manager under names such as:

```text
ScarnsNameSniffer:exampleuser
```

Name Sniffer v2.5 adds a **[c]redentials** menu where you can list saved usernames, copy or reveal a password on demand, open Roblox login, delete a saved credential, or export a usernames-only list.

The extension stores only non-secret account history. Bulk-open mode does not generate or save account passwords.
~~~~~


---

## FILE: `browser-extension/background.js`

Blob SHA: `411128f45d53b7bd4969d129ad0bcd708180bddb`

~~~~~javascript
(() => {
  "use strict";

  function replyAsync(sendResponse, task) {
    Promise.resolve()
      .then(task)
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          ok: false,
          error: String(error?.message || error || "unknown error")
        });
      });
    return true;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "scarn:getAuthenticatedUser") {
      return replyAsync(sendResponse, async () => {
        const response = await fetch(
          "https://users.roblox.com/v1/users/authenticated",
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: { Accept: "application/json" }
          }
        );

        if (!response.ok) {
          return { ok: false, status: response.status };
        }

        const data = await response.json();
        return {
          ok: true,
          user: {
            id: data.id ?? null,
            name: data.name || "",
            displayName: data.displayName || ""
          }
        };
      });
    }

    if (message?.type === "scarn:storePendingSecret") {
      return replyAsync(sendResponse, async () => {
        const secret = message.secret || {};
        if (
          !secret.username ||
          !secret.password ||
          !secret.expiresAt
        ) {
          return { ok: false, error: "invalid secret payload" };
        }

        await chrome.storage.session.set({
          pendingSignupSecret: {
            username: String(secret.username),
            password: String(secret.password),
            armedAt: Number(secret.armedAt || Date.now()),
            expiresAt: Number(secret.expiresAt)
          }
        });
        return { ok: true };
      });
    }

    if (message?.type === "scarn:getPendingSecret") {
      return replyAsync(sendResponse, async () => {
        const { pendingSignupSecret } =
          await chrome.storage.session.get({
            pendingSignupSecret: null
          });

        if (!pendingSignupSecret) {
          return { ok: false, error: "no pending secret" };
        }

        if (Date.now() > Number(pendingSignupSecret.expiresAt || 0)) {
          await chrome.storage.session.remove("pendingSignupSecret");
          return { ok: false, error: "pending secret expired" };
        }

        if (
          message.username &&
          String(pendingSignupSecret.username).toLowerCase() !==
            String(message.username).toLowerCase()
        ) {
          return { ok: false, error: "pending username mismatch" };
        }

        return {
          ok: true,
          secret: pendingSignupSecret
        };
      });
    }

    if (message?.type === "scarn:clearPendingSecret") {
      return replyAsync(sendResponse, async () => {
        await chrome.storage.session.remove("pendingSignupSecret");
        return { ok: true };
      });
    }

    return false;
  });
})();
~~~~~


---

## FILE: `browser-extension/content.js`

Blob SHA: `b362e21f4022bf9a620831e43f2ce19c27399f84`

~~~~~javascript
(() => {
  "use strict";

  const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const PAYLOAD_PREFIX = "SCARN_AUTOFILL_V2|";
  const LOWER = "abcdefghijkmnopqrstuvwxyz";
  const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const DIGITS = "23456789";
  const SYMBOLS = "!@#$%";
  const ALL = LOWER + UPPER + DIGITS + SYMBOLS;
  const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const MONTH_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  let generatedPassword = null;
  let mainFieldsFilled = false;
  let birthdayFilled = false;
  let lastUsername = null;

  function randomIndex(max) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    return buf[0] % max;
  }

  function pick(chars) {
    return chars[randomIndex(chars.length)];
  }

  function makePassword(length = 16) {
    const chars = [pick(LOWER), pick(UPPER), pick(DIGITS), pick(SYMBOLS)];
    while (chars.length < length) chars.push(pick(ALL));
    for (let i = chars.length - 1; i > 0; i--) {
      const j = randomIndex(i + 1);
      [chars[i], chars[j]] = [chars[j], chars[i]];
    }
    return chars.join("");
  }

  function isVisible(el) {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function firstVisible(selectors) {
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        if (isVisible(el)) return el;
      }
    }
    return null;
  }

  function fromLabel(text, tag = "input") {
    const target = text.toLowerCase();
    for (const label of document.querySelectorAll("label")) {
      if (!label.textContent.toLowerCase().includes(target)) continue;
      if (label.htmlFor) {
        const field = document.getElementById(label.htmlFor);
        if (field && isVisible(field)) return field;
      }
      const nested = label.querySelector(tag);
      if (nested && isVisible(nested)) return nested;
    }
    return null;
  }

  function findFields() {
    const username = firstVisible([
      'input[name="username"]',
      'input[autocomplete="username"]',
      'input[id*="username" i]',
      'input[placeholder*="username" i]'
    ]) || fromLabel("username");

    const password = firstVisible([
      'input[autocomplete="new-password"]',
      'input[name="password"]',
      'input[id*="password" i]',
      'input[placeholder*="password" i]',
      'input[type="password"]'
    ]) || fromLabel("password");

    return { username, password };
  }

  function findBirthdayFields() {
    const dateInput = firstVisible([
      'input[type="date"][name*="birth" i]',
      'input[type="date"][id*="birth" i]',
      'input[type="date"][autocomplete="bday"]'
    ]);

    const month = firstVisible([
      '#MonthDropdown',
      'select[name="birthdayMonth"]',
      'select[name*="month" i]',
      'select[id*="month" i]',
      'select[aria-label*="month" i]'
    ]) || fromLabel("month", "select");

    const day = firstVisible([
      '#DayDropdown',
      'select[name="birthdayDay"]',
      'select[name*="day" i]',
      'select[id*="day" i]',
      'select[aria-label*="day" i]'
    ]) || fromLabel("day", "select");

    const year = firstVisible([
      '#YearDropdown',
      'select[name="birthdayYear"]',
      'select[name*="year" i]',
      'select[id*="year" i]',
      'select[aria-label*="year" i]'
    ]) || fromLabel("year", "select");

    return { dateInput, month, day, year };
  }

  function setNativeValue(input, value) {
    const proto = input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    if (descriptor?.set) descriptor.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function normalize(value) {
    return String(value ?? "").trim().toLowerCase();
  }

  function selectOption(select, candidates) {
    if (!select) return false;
    const wanted = new Set(candidates.map(normalize));
    const option = [...select.options].find(opt => wanted.has(normalize(opt.value)) || wanted.has(normalize(opt.textContent)));
    if (!option) return false;
    setNativeValue(select, option.value);
    return true;
  }

  async function getEmailSettings() {
    return new Promise(resolve => {
      chrome.storage.local.get(
        { emailAddress: "", autoAddEmail: false },
        ({ emailAddress, autoAddEmail }) => {
          resolve({
            emailAddress: String(emailAddress || "").trim(),
            autoAddEmail: autoAddEmail === true
          });
        }
      );
    });
  }

  async function armEmailSetup(username, password) {
    const settings = await getEmailSettings();
    if (!settings.autoAddEmail || !EMAIL_RE.test(settings.emailAddress)) {
      return false;
    }

    const now = Date.now();
    const pending = {
      username,
      email: settings.emailAddress,
      armedAt: now,
      expiresAt: now + 15 * 60 * 1000,
      status: "waiting-for-signup"
    };

    await new Promise(resolve => {
      chrome.storage.local.set(
        {
          emailSetupPending: pending,
          emailSetupStatus: `Waiting for ${username} to finish signup before adding ${settings.emailAddress}.`
        },
        resolve
      );
    });

    if (password) {
      await new Promise(resolve => {
        chrome.runtime.sendMessage(
          {
            type: "scarn:storePendingSecret",
            secret: {
              username,
              password,
              armedAt: now,
              expiresAt: pending.expiresAt
            }
          },
          () => resolve()
        );
      });
    }

    return true;
  }

  async function getBirthday() {
    return new Promise(resolve => {
      chrome.storage.local.get({ birthday: "" }, ({ birthday }) => resolve(birthday || ""));
    });
  }

  function fillBirthday(birthday) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(birthday)) return false;
    const [year, month, day] = birthday.split("-").map(Number);
    const fields = findBirthdayFields();

    if (fields.dateInput) {
      setNativeValue(fields.dateInput, birthday);
      return true;
    }

    if (!fields.month || !fields.day || !fields.year) return false;

    const monthOk = selectOption(fields.month, [
      month,
      String(month).padStart(2, "0"),
      month - 1,
      MONTH_SHORT[month - 1],
      MONTH_LONG[month - 1]
    ]);
    const dayOk = selectOption(fields.day, [day, String(day).padStart(2, "0")]);
    const yearOk = selectOption(fields.year, [year]);
    return monthOk && dayOk && yearOk;
  }

  async function readClipboardData() {
    try {
      const text = (await navigator.clipboard.readText()).trim();
      if (text.startsWith(PAYLOAD_PREFIX)) {
        const parts = text.split("|");
        const username = parts[1] || "";
        const password = parts[2] || "";
        const saved = parts[3] === "1";
        if (USERNAME_RE.test(username) && password.length >= 12) {
          try { await navigator.clipboard.writeText(""); } catch (_) {}
          return { username, password, saved, secureHandoff: true };
        }
      }
      if (USERNAME_RE.test(text)) {
        return { username: text, password: null, saved: false, secureHandoff: false };
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;opacity:0;pointer-events:none";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    }
  }

  function rememberAccount(username, birthday, saved) {
    chrome.storage.local.get({ accountHistory: [] }, ({ accountHistory }) => {
      const history = Array.isArray(accountHistory) ? accountHistory : [];
      const entry = {
        username,
        birthday: birthday || "",
        passwordLocation: saved ? "Windows Credential Manager" : "Not saved by Name Sniffer",
        createdAt: new Date().toISOString()
      };
      const withoutDuplicate = history.filter(item => item.username !== username);
      withoutDuplicate.unshift(entry);
      chrome.storage.local.set({ accountHistory: withoutDuplicate.slice(0, 100) });
    });
  }

  function makePanel(username, password, birthday, birthdayStatus, saved) {
    document.getElementById("scarn-sniffer-autofill")?.remove();
    const box = document.createElement("div");
    box.id = "scarn-sniffer-autofill";
    box.style.cssText = [
      "position:fixed", "right:18px", "top:18px", "z-index:2147483647",
      "width:340px", "padding:16px", "border-radius:12px",
      "background:#0f141c", "color:#eef4ff", "border:1px solid #314052",
      "box-shadow:0 18px 50px rgba(0,0,0,.45)",
      "font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif"
    ].join(";");

    const birthdayLine = birthday
      ? `<div style="color:${birthdayStatus ? "#53f59a" : "#f6c85f"};margin-bottom:10px">Birthday: <b data-bday></b> ${birthdayStatus ? "✓" : "(couldn't fill)"}</div>`
      : `<div style="color:#f6c85f;margin-bottom:10px">Birthday not configured. Click the extension icon to set it.</div>`;

    box.innerHTML = `
      <div style="font-weight:800;font-size:15px;margin-bottom:10px">🔎 Scarn's Name Sniffer</div>
      <div style="color:#9fb0c2;margin-bottom:8px">Autofilled <b data-user style="color:#53f59a"></b></div>
      ${birthdayLine}
      <div style="color:${saved ? "#53f59a" : "#f6c85f"};margin-bottom:10px">Password storage: <b>${saved ? "Windows Credential Manager ✓" : "not securely saved"}</b></div>
      <div style="font-size:12px;color:#7f93a8;margin-bottom:4px">Generated password</div>
      <code data-pw style="display:block;padding:9px 10px;background:#080b10;border-radius:8px;color:#65d9ff;word-break:break-all">••••••••••••••••</code>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button data-show style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Show</button>
        <button data-copy style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Copy password</button>
      </div>
      <div style="margin-top:10px;color:#8fa1b3;font-size:12px">${saved ? "This password is already saved in Windows Credential Manager." : "Save this password before creating the account."} The companion never presses Create Account for you.</div>
    `;

    box.querySelector("[data-user]").textContent = username;
    if (birthday) box.querySelector("[data-bday]").textContent = birthday;

    const pw = box.querySelector("[data-pw]");
    const show = box.querySelector("[data-show]");
    const copy = box.querySelector("[data-copy]");
    let visible = false;

    show.addEventListener("click", () => {
      visible = !visible;
      pw.textContent = visible ? password : "••••••••••••••••";
      show.textContent = visible ? "Hide" : "Show";
    });

    copy.addEventListener("click", async () => {
      const ok = await writeClipboard(password);
      copy.textContent = ok ? "Copied ✓" : "Copy failed";
      setTimeout(() => { copy.textContent = "Copy password"; }, 1600);
    });

    document.documentElement.appendChild(box);
  }

  function makeRetryPanel() {
    if (document.getElementById("scarn-sniffer-autofill")) return;
    const box = document.createElement("div");
    box.id = "scarn-sniffer-autofill";
    box.style.cssText = "position:fixed;right:18px;top:18px;z-index:2147483647;width:300px;padding:15px;border-radius:12px;background:#0f141c;color:#eef4ff;border:1px solid #314052;font:14px system-ui;box-shadow:0 18px 50px rgba(0,0,0,.45)";
    box.innerHTML = `<b>🔎 Scarn's Name Sniffer</b><div style="margin:9px 0;color:#9fb0c2">I couldn't read the username/password handoff from the clipboard automatically.</div><button style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:8px 11px;cursor:pointer;font-weight:700">Autofill now</button>`;
    box.querySelector("button").addEventListener("click", async () => {
      const account = await readClipboardData();
      if (account) await startFill(account, true);
      else box.querySelector("div").textContent = "Clipboard doesn't contain a Name Sniffer handoff. Choose the name in Name Sniffer again.";
    });
    document.documentElement.appendChild(box);
  }

  async function attemptFill(account) {
    const username = account.username;
    lastUsername = username;
    const fields = findFields();
    if (fields.username && fields.password) {
      generatedPassword ||= account.password || makePassword();
      setNativeValue(fields.username, username);
      setNativeValue(fields.password, generatedPassword);
      mainFieldsFilled = true;
    }

    const birthday = await getBirthday();
    if (birthday && !birthdayFilled) birthdayFilled = fillBirthday(birthday);

    return { birthday };
  }

  async function startFill(account, userGesture = false) {
    if (!account || !USERNAME_RE.test(account.username)) return false;
    let birthday = "";

    for (let attempt = 0; attempt < 40; attempt++) {
      const result = await attemptFill(account);
      birthday = result.birthday;
      if (mainFieldsFilled && (!birthday || birthdayFilled)) {
        rememberAccount(account.username, birthday, account.saved);
        await armEmailSetup(account.username, generatedPassword);
        makePanel(account.username, generatedPassword, birthday, birthdayFilled, account.saved);
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    if (mainFieldsFilled) {
      rememberAccount(account.username, birthday, account.saved);
      await armEmailSetup(account.username, generatedPassword);
      makePanel(account.username, generatedPassword, birthday, birthdayFilled, account.saved);
      return true;
    }

    if (userGesture) makeRetryPanel();
    return false;
  }

  async function start() {
    let account = await readClipboardData();

    for (let attempt = 0; attempt < 40; attempt++) {
      if (!account) account = await readClipboardData();
      if (account && await startFill(account)) return;
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    makeRetryPanel();
  }

  start();
})();
~~~~~


---

## FILE: `browser-extension/email.js`

Blob SHA: `58da035605bad957218fb99b9e4f51c457aa69b5`

~~~~~javascript
(() => {
  "use strict";

  const SETTINGS_URL = "https://www.roblox.com/my/account#!/info";
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const POLL_MS = 250;
  const POLL_ATTEMPTS = 80;

  function visible(element) {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      rect.width > 0 &&
      rect.height > 0;
  }

  function textOf(element) {
    return String(
      element?.innerText ||
      element?.textContent ||
      element?.value ||
      element?.getAttribute?.("aria-label") ||
      ""
    ).trim().replace(/\s+/g, " ").toLowerCase();
  }

  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function localGet(defaults) {
    return new Promise(resolve => chrome.storage.local.get(defaults, resolve));
  }

  function localSet(values) {
    return new Promise(resolve => chrome.storage.local.set(values, resolve));
  }

  function localRemove(keys) {
    return new Promise(resolve => chrome.storage.local.remove(keys, resolve));
  }

  function getPendingSecret(username) {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:getPendingSecret", username },
        response => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false });
        }
      );
    });
  }

  function clearPendingSecret() {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:clearPendingSecret" },
        () => resolve()
      );
    });
  }

  function getAuthenticatedUser() {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:getAuthenticatedUser" },
        response => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false });
        }
      );
    });
  }

  function setNativeValue(input, value) {
    const prototype = input instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
    if (descriptor?.set) descriptor.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function findButtons() {
    return [
      ...document.querySelectorAll(
        'button, input[type="button"], input[type="submit"], [role="button"]'
      )
    ].filter(visible);
  }

  function findAddEmailButton() {
    const exact = new Set([
      "add email",
      "add email address",
      "add an email",
      "add an email address"
    ]);
    return findButtons().find(button => exact.has(textOf(button))) || null;
  }

  function findExistingEmailControl() {
    return findButtons().find(button => {
      const text = textOf(button);
      return (
        text.includes("update email") ||
        text.includes("change email") ||
        text.includes("edit email") ||
        text.includes("remove email")
      );
    }) || null;
  }

  function findEmailInput() {
    const selectors = [
      'input[type="email"]',
      'input[name*="email" i]',
      'input[id*="email" i]',
      'input[placeholder*="email" i]',
      'input[autocomplete="email"]'
    ];
    for (const selector of selectors) {
      for (const input of document.querySelectorAll(selector)) {
        if (visible(input)) return input;
      }
    }
    return null;
  }

  function findPasswordInput() {
    const selectors = [
      'input[type="password"]',
      'input[name*="password" i]',
      'input[id*="password" i]',
      'input[autocomplete="current-password"]'
    ];
    for (const selector of selectors) {
      for (const input of document.querySelectorAll(selector)) {
        if (visible(input)) return input;
      }
    }
    return null;
  }

  function findSubmitButton(emailInput) {
    const container =
      emailInput?.closest('[role="dialog"]') ||
      emailInput?.closest("form") ||
      document;

    const allowed = [
      "add email",
      "add email address",
      "send verification",
      "send verification email",
      "send email",
      "verify email",
      "continue",
      "save"
    ];

    const candidates = [
      ...container.querySelectorAll(
        'button, input[type="submit"], [role="button"]'
      )
    ].filter(visible);

    for (const candidate of candidates) {
      const text = textOf(candidate);
      if (
        text.includes("update") ||
        text.includes("change") ||
        text.includes("remove")
      ) {
        continue;
      }
      if (allowed.some(label => text === label || text.includes(label))) {
        return candidate;
      }
    }

    const submits = candidates.filter(candidate => {
      if (candidate instanceof HTMLInputElement) {
        return candidate.type === "submit";
      }
      return candidate.tagName === "BUTTON" &&
        (candidate.type === "submit" || candidate.getAttribute("type") === "submit");
    });
    return submits.length === 1 ? submits[0] : null;
  }

  function buttonEnabled(button) {
    if (!button) return false;
    return !button.disabled &&
      button.getAttribute("aria-disabled") !== "true";
  }

  async function waitFor(getter, attempts = POLL_ATTEMPTS) {
    for (let attempt = 0; attempt < attempts; attempt++) {
      const value = getter();
      if (value) return value;
      await wait(POLL_MS);
    }
    return null;
  }

  function showPanel(message, good = false) {
    document.getElementById("scarn-email-setup")?.remove();
    const panel = document.createElement("div");
    panel.id = "scarn-email-setup";
    panel.style.cssText = [
      "position:fixed",
      "right:18px",
      "bottom:18px",
      "z-index:2147483647",
      "width:330px",
      "padding:14px 15px",
      "border-radius:12px",
      "background:#0f141c",
      "color:#eef4ff",
      "border:1px solid #314052",
      "box-shadow:0 18px 50px rgba(0,0,0,.45)",
      "font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif"
    ].join(";");

    const title = document.createElement("div");
    title.style.cssText = "font-weight:800;margin-bottom:7px";
    title.textContent = "✉️ Scarn's Email Helper";

    const body = document.createElement("div");
    body.style.color = good ? "#53f59a" : "#9fb0c2";
    body.textContent = message;

    panel.append(title, body);
    document.documentElement.appendChild(panel);
  }

  async function status(message) {
    await localSet({ emailSetupStatus: message });
  }

  async function finish(message, good = true) {
    await status(message);
    await localRemove("emailSetupPending");
    await clearPendingSecret();
    showPanel(message, good);
  }

  async function run() {
    if (/\/CreateAccount/i.test(location.pathname)) return;

    const {
      emailAddress,
      autoAddEmail,
      emailSetupPending
    } = await localGet({
      emailAddress: "",
      autoAddEmail: false,
      emailSetupPending: null
    });

    if (!autoAddEmail || !EMAIL_RE.test(String(emailAddress || ""))) return;
    if (!emailSetupPending) return;

    const pending = emailSetupPending;
    const now = Date.now();

    if (
      !pending.username ||
      !pending.email ||
      !pending.expiresAt ||
      now > pending.expiresAt
    ) {
      await finish("Email setup expired before signup completed.", false);
      return;
    }

    if (pending.status === "submitted") {
      showPanel(
        `Verification was requested for ${pending.email}. Check your inbox and complete it manually.`,
        true
      );
      return;
    }

    const auth = await getAuthenticatedUser();
    if (!auth?.ok || !auth.user?.name) {
      await status(
        `Waiting to confirm that ${pending.username} is logged in before adding the email.`
      );
      return;
    }

    if (
      String(auth.user.name).toLowerCase() !==
      String(pending.username).toLowerCase()
    ) {
      await status(
        `Email setup paused: expected ${pending.username}, but Roblox is logged in as ${auth.user.name}.`
      );
      return;
    }

    if (!/\/my\/account/i.test(location.pathname)) {
      await status(
        `Signup confirmed for ${pending.username}. Opening Account Info to add ${pending.email}.`
      );
      location.assign(SETTINGS_URL);
      return;
    }

    showPanel(`Adding ${pending.email} to ${pending.username}…`);

    let addButton = findAddEmailButton();
    if (!addButton) {
      const existing = findExistingEmailControl();
      if (existing) {
        await finish(
          "This account already has an email control. Scarn's helper will not replace or change an existing email.",
          false
        );
        return;
      }

      addButton = await waitFor(findAddEmailButton);
    }

    if (!addButton) {
      await status(
        "Could not find Roblox's Add Email button. The page may have changed; no existing email was modified."
      );
      showPanel(
        "Could not find the Add Email button. Nothing was changed.",
        false
      );
      return;
    }

    addButton.click();

    const emailInput = await waitFor(findEmailInput);
    if (!emailInput) {
      await status("Add Email opened, but the email field could not be located.");
      showPanel("Add Email opened, but I couldn't locate the email field.", false);
      return;
    }

    setNativeValue(emailInput, pending.email);

    const passwordInput = findPasswordInput();
    if (passwordInput) {
      const secretResponse = await getPendingSecret(pending.username);

      if (!secretResponse?.ok || !secretResponse.secret?.password) {
        await status(
          "Roblox requested the account password, but the temporary signup password is no longer available."
        );
        showPanel(
          "Email filled. Roblox also wants the password, but the temporary password is no longer available. Fill it manually.",
          false
        );
        return;
      }

      setNativeValue(passwordInput, secretResponse.secret.password);
    }

    let submit = findSubmitButton(emailInput);
    if (!submit) {
      submit = await waitFor(() => findSubmitButton(emailInput), 20);
    }

    if (!submit) {
      await status(
        "Email was filled, but the normal Add Email / Send Verification button could not be located."
      );
      showPanel(
        "Email filled. I couldn't find the final Add Email button, so nothing was submitted.",
        false
      );
      return;
    }

    for (let attempt = 0; attempt < 20 && !buttonEnabled(submit); attempt++) {
      await wait(POLL_MS);
    }

    if (!buttonEnabled(submit)) {
      await status(
        "Email was filled, but Roblox kept the Add Email button disabled."
      );
      showPanel(
        "Email filled, but Roblox kept the submit button disabled. Nothing was bypassed.",
        false
      );
      return;
    }

    submit.click();

    const submittedPending = {
      ...pending,
      status: "submitted",
      submittedAt: Date.now()
    };
    await localSet({
      emailSetupPending: submittedPending,
      emailSetupStatus:
        `Verification requested for ${pending.email}. Check your inbox and verify it manually.`
    });

    // Give Roblox a moment to surface a normal success/error response. We do
    // not interact with the verification email itself.
    await wait(1200);
    showPanel(
      `Verification requested for ${pending.email}. Check your inbox and complete the Roblox verification manually.`,
      true
    );

    await clearPendingSecret();
  }

  run().catch(async error => {
    const message =
      "Email helper stopped safely: " +
      String(error?.message || error || "unknown error");
    try {
      await status(message);
    } catch (_) {}
    showPanel(message, false);
  });
})();
~~~~~


---

## FILE: `browser-extension/enter-submit.js`

Blob SHA: `8afd296f69ae56f56f059b6d4c127e01f200f905`

~~~~~javascript
(() => {
  "use strict";

  let enterSubmitEnabled = true;

  chrome.storage.local.get({ enterSubmit: true }, ({ enterSubmit }) => {
    enterSubmitEnabled = enterSubmit !== false;
  });

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === "local" && changes.enterSubmit) {
      enterSubmitEnabled = changes.enterSubmit.newValue !== false;
    }
  });

  function visible(element) {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function firstVisible(selectors) {
    for (const selector of selectors) {
      for (const element of document.querySelectorAll(selector)) {
        if (visible(element)) return element;
      }
    }
    return null;
  }

  function formLooksFilled() {
    const username = firstVisible([
      'input[name="username"]',
      'input[autocomplete="username"]',
      'input[id*="username" i]',
      'input[placeholder*="username" i]'
    ]);
    const password = firstVisible([
      'input[autocomplete="new-password"]',
      'input[name="password"]',
      'input[id*="password" i]',
      'input[type="password"]'
    ]);

    if (!username?.value?.trim() || !password?.value) return false;

    const dateInput = firstVisible([
      'input[type="date"][name*="birth" i]',
      'input[type="date"][id*="birth" i]',
      'input[type="date"][autocomplete="bday"]'
    ]);
    if (dateInput && !dateInput.value) return false;

    const month = firstVisible(['#MonthDropdown', 'select[name*="month" i]', 'select[id*="month" i]']);
    const day = firstVisible(['#DayDropdown', 'select[name*="day" i]', 'select[id*="day" i]']);
    const year = firstVisible(['#YearDropdown', 'select[name*="year" i]', 'select[id*="year" i]']);
    if ((month || day || year) && (!month?.value || !day?.value || !year?.value)) return false;

    return true;
  }

  function findCreateAccountButton() {
    const buttons = [...document.querySelectorAll("button")].filter(visible);
    const exact = buttons.find(button => {
      const text = (button.textContent || "").trim().toLowerCase();
      return text === "sign up" || text === "signup" || text === "create account";
    });
    if (exact) return exact;

    const submits = buttons.filter(button => button.type === "submit");
    return submits.length === 1 ? submits[0] : null;
  }

  document.addEventListener("keydown", event => {
    if (!enterSubmitEnabled) return;
    if (event.key !== "Enter" || event.repeat) return;
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    if (event.target instanceof HTMLTextAreaElement || event.target?.isContentEditable) return;
    if (!formLooksFilled()) return;

    const button = findCreateAccountButton();
    if (!button || button.disabled || button.getAttribute("aria-disabled") === "true") return;

    event.preventDefault();
    event.stopPropagation();
    button.click();
  }, true);
})();
~~~~~


---

## FILE: `browser-extension/manifest.json`

Blob SHA: `5f409de6d2a43c8f111738f88dc1e5d65d220b1e`

~~~~~json
{
  "manifest_version": 3,
  "name": "Scarn's Name Sniffer Autofill",
  "version": "2.5.1",
  "description": "Autofills Roblox signup, securely hands off generated credentials, and can add your saved email after signup before you verify it manually.",
  "permissions": [
    "clipboardRead",
    "clipboardWrite",
    "storage"
  ],
  "host_permissions": [
    "https://users.roblox.com/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_title": "Scarn's Name Sniffer Autofill",
    "default_popup": "popup.html"
  },
  "content_scripts": [
    {
      "matches": [
        "https://www.roblox.com/CreateAccount*"
      ],
      "js": [
        "content.js",
        "enter-submit.js"
      ],
      "run_at": "document_idle"
    },
    {
      "matches": [
        "https://www.roblox.com/*"
      ],
      "js": [
        "email.js"
      ],
      "run_at": "document_idle"
    }
  ]
}
~~~~~


---

## FILE: `browser-extension/popup.html`

Blob SHA: `768698247407be040b6f95ae074378e41876208f`

~~~~~html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Name Sniffer Autofill</title>
  <style>
    body { width: 320px; margin: 0; padding: 16px; background: #0f141c; color: #eef4ff; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
    h1 { font-size: 16px; margin: 0 0 8px; }
    p { color: #9fb0c2; margin: 0 0 14px; }
    label { display: block; font-weight: 700; margin-bottom: 6px; }
    input[type="date"], input[type="email"] { width: 100%; box-sizing: border-box; border: 1px solid #314052; border-radius: 8px; background: #080b10; color: #eef4ff; padding: 9px 10px; }
    .row { display: flex; gap: 8px; margin-top: 10px; }
    .toggle { display:flex; align-items:center; gap:8px; margin-top:14px; font-weight:700; }
    .toggle input { width:auto; }
    button { flex: 1; border: 1px solid #314052; border-radius: 8px; background: #18212d; color: #eef4ff; padding: 8px 10px; cursor: pointer; font-weight: 700; }
    button.primary { background: #53f59a; color:#04120a; border-color: transparent; }
    #status { min-height: 20px; margin-top: 10px; color: #65d9ff; font-size: 12px; }
    .note { margin-top: 12px; color: #7f93a8; font-size: 11px; }
  </style>
</head>
<body>
  <h1>🔎 Name Sniffer Autofill v2.5.1</h1>
  <p>Set the signup birthday and optional recovery email.</p>

  <label for="birthday">Birthday</label>
  <input id="birthday" type="date" autocomplete="bday">

  <label for="email" style="margin-top:14px">Recovery email</label>
  <input id="email" type="email" autocomplete="email" placeholder="you@example.com">

  <label class="toggle"><input id="auto-email" type="checkbox"> Automatically add email after signup</label>

  <div class="row">
    <button id="save" class="primary">Save settings</button>
    <button id="clear-birthday">Clear birthday</button>
  </div>
  <div class="row">
    <button id="clear-email">Clear email</button>
  </div>

  <label class="toggle"><input id="enter-submit" type="checkbox"> Press Enter to submit signup</label>

  <div id="status"></div>
  <div id="history" class="note"></div>
  <div class="note">Auto-add Email only uses Roblox's normal Add Email flow after confirming the newly created username is logged in. It stops after requesting the verification email, and you verify it manually from your inbox. Existing emails are never replaced. Any password needed by the Add Email dialog is kept only in browser-session storage.</div>

  <script src="popup.js"></script>
</body>
</html>
~~~~~
