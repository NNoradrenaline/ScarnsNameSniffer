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


---

## FILE: `browser-extension/popup.js`

Blob SHA: `068d3586af5b96c42f840782579c4ef6bc4bb989`

~~~~~javascript
(() => {
  "use strict";

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const birthday = document.getElementById("birthday");
  const email = document.getElementById("email");
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const clearBirthday = document.getElementById("clear-birthday");
  const clearEmail = document.getElementById("clear-email");
  const history = document.getElementById("history");
  const enterSubmit = document.getElementById("enter-submit");
  const autoEmail = document.getElementById("auto-email");

  chrome.storage.local.get(
    {
      birthday: "",
      emailAddress: "",
      autoAddEmail: false,
      accountHistory: [],
      enterSubmit: true,
      emailSetupStatus: ""
    },
    values => {
      birthday.value = values.birthday || "";
      email.value = values.emailAddress || "";
      autoEmail.checked = values.autoAddEmail === true;
      enterSubmit.checked = values.enterSubmit !== false;

      const count = Array.isArray(values.accountHistory)
        ? values.accountHistory.length
        : 0;

      history.textContent =
        count + " account" + (count === 1 ? "" : "s") +
        " recorded locally." +
        (values.emailSetupStatus
          ? " Email helper: " + values.emailSetupStatus
          : "");
    }
  );

  enterSubmit.addEventListener("change", () => {
    chrome.storage.local.set({ enterSubmit: enterSubmit.checked }, () => {
      status.textContent = enterSubmit.checked
        ? "Enter-to-submit enabled ✓"
        : "Enter-to-submit disabled.";
    });
  });

  autoEmail.addEventListener("change", () => {
    const emailValue = email.value.trim();

    if (autoEmail.checked && !EMAIL_RE.test(emailValue)) {
      autoEmail.checked = false;
      status.textContent =
        "Enter and save a valid email before enabling Auto-add Email.";
      return;
    }

    chrome.storage.local.set(
      { autoAddEmail: autoEmail.checked },
      () => {
        status.textContent = autoEmail.checked
          ? "Auto-add Email enabled ✓"
          : "Auto-add Email disabled.";
      }
    );
  });

  save.addEventListener("click", () => {
    const emailValue = email.value.trim();

    if (emailValue && !EMAIL_RE.test(emailValue)) {
      status.textContent = "Enter a valid email address.";
      return;
    }

    if (autoEmail.checked && !emailValue) {
      status.textContent =
        "Auto-add Email needs a saved email address.";
      return;
    }

    chrome.storage.local.set(
      {
        birthday: birthday.value || "",
        emailAddress: emailValue,
        autoAddEmail: autoEmail.checked && Boolean(emailValue)
      },
      () => {
        status.textContent = "Settings saved ✓";
      }
    );
  });

  clearBirthday.addEventListener("click", () => {
    chrome.storage.local.remove("birthday", () => {
      birthday.value = "";
      status.textContent = "Saved birthday cleared.";
    });
  });

  clearEmail.addEventListener("click", () => {
    chrome.storage.local.remove(
      ["emailAddress", "emailSetupPending", "emailSetupStatus"],
      () => {
        chrome.storage.local.set({ autoAddEmail: false }, () => {
          chrome.runtime.sendMessage(
            { type: "scarn:clearPendingSecret" },
            () => {
              email.value = "";
              autoEmail.checked = false;
              status.textContent =
                "Saved email and pending email job cleared.";
            }
          );
        });
      }
    );
  });
})();
~~~~~


---

## FILE: `docs/index.html`

Blob SHA: `8f59e4e9b0ad9eaa0a9355e57e9bd41ca3657ef2`

~~~~~html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Scarn's Name Sniffer v2.5 is a Windows Roblox username generator and availability checker with secure credential storage and an optional Chrome/Edge autofill companion." />
  <title>Scarn's Name Sniffer v2.5</title>
  <style>
    :root { color-scheme: dark; --bg:#080b10; --panel:#0f141c; --panel2:#141b25; --text:#eef4ff; --muted:#94a3b8; --green:#53f59a; --cyan:#65d9ff; --line:#243041; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:radial-gradient(circle at 50% -20%,#152236 0,#080b10 38rem); color:var(--text); }
    a { color:inherit; }
    .wrap { width:min(1060px,calc(100% - 36px)); margin:auto; }
    nav { display:flex; justify-content:space-between; align-items:center; padding:24px 0; }
    .brand { font-weight:800; }
    .navlinks { display:flex; gap:18px; color:var(--muted); font-size:14px; }
    .hero { padding:78px 0 50px; text-align:center; }
    .eyebrow { display:inline-flex; padding:8px 12px; border:1px solid var(--line); border-radius:999px; color:var(--green); background:#0c1319; font:600 13px ui-monospace,SFMono-Regular,Consolas,monospace; }
    h1 { font-size:clamp(44px,8vw,82px); line-height:.95; letter-spacing:-.055em; margin:24px auto 22px; max-width:900px; }
    .lead { color:var(--muted); font-size:clamp(18px,2.4vw,22px); line-height:1.6; max-width:760px; margin:0 auto 30px; }
    .actions { display:flex; flex-wrap:wrap; justify-content:center; gap:12px; }
    .btn { text-decoration:none; border-radius:10px; padding:13px 18px; font-weight:800; border:1px solid var(--line); background:var(--panel); }
    .btn.primary { background:var(--green); color:#04120a; border-color:transparent; }
    .terminal { margin:50px auto 0; max-width:820px; text-align:left; border:1px solid var(--line); background:#080c11; border-radius:16px; overflow:hidden; box-shadow:0 30px 90px #0008; }
    .bar { padding:12px 14px; border-bottom:1px solid var(--line); background:#0d1219; }
    pre { margin:0; padding:22px; overflow:auto; font:14px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace; color:#d8e5f5; }
    section { padding:54px 0; }
    h2 { font-size:36px; letter-spacing:-.035em; margin:0 0 12px; }
    .sub { color:var(--muted); margin:0 0 28px; line-height:1.6; }
    .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
    .card { border:1px solid var(--line); background:linear-gradient(180deg,var(--panel2),var(--panel)); border-radius:14px; padding:20px; }
    .card strong { display:block; font-size:17px; margin-bottom:8px; }
    .card p { color:var(--muted); line-height:1.55; margin:0; font-size:14px; }
    .steps { counter-reset:step; display:grid; gap:12px; }
    .step { counter-increment:step; padding:18px 20px 18px 62px; position:relative; border:1px solid var(--line); border-radius:12px; background:var(--panel); }
    .step:before { content:counter(step); position:absolute; left:18px; top:15px; width:28px; height:28px; display:grid; place-items:center; border-radius:50%; background:var(--green); color:#04120a; font-weight:900; }
    code { color:var(--cyan); }
    footer { border-top:1px solid var(--line); padding:30px 0 44px; color:var(--muted); font-size:14px; display:flex; justify-content:space-between; gap:20px; }
    @media (max-width:760px) { .grid { grid-template-columns:1fr; } .navlinks { display:none; } footer { flex-direction:column; } }
  </style>
</head>
<body>
  <div class="wrap">
    <nav>
      <div class="brand">🔎 Scarn's Name Sniffer</div>
      <div class="navlinks"><a href="#features">Features</a><a href="#download">Download</a><a href="https://github.com/NNoradrenaline/ScarnsNameSniffer">GitHub</a></div>
    </nav>
    <main>
      <div class="hero">
        <div class="eyebrow">WINDOWS · v2.5 · MADE BY SCARN</div>
        <h1>Sniff out a Roblox name worth keeping.</h1>
        <p class="lead">Generate short usernames, check availability, hunt for word-like names, scan custom wordlists, save finds, and optionally use the browser companion for signup autofill.</p>
        <div class="actions">
          <a class="btn primary" href="https://github.com/NNoradrenaline/ScarnsNameSniffer/releases/latest">Download latest release</a>
          <a class="btn" href="https://github.com/NNoradrenaline/ScarnsNameSniffer">View source</a>
        </div>
        <div class="terminal">
          <div class="bar">● ● ●</div>
          <pre>                 Scarn's Name Sniffer v2.5
       (Roblox username generator + availability checker)

Fetching CSRF token... OK

Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist [c]redentials?</pre>
        </div>
      </div>
      <section id="features">
        <h2>Built for the name hunt.</h2>
        <p class="sub">Fast checks, practical generation modes, and a local credential workflow without requiring an existing Roblox password or cookie.</p>
        <div class="grid">
          <div class="card"><strong>🔍 Availability scan</strong><p>Generate usernames and check them against Roblox's validation service.</p></div>
          <div class="card"><strong>✨ Aesthetic mode</strong><p>Favor more pronounceable results using consonant/vowel patterns and word-like scoring.</p></div>
          <div class="card"><strong>⌨️ Manual + wordlist modes</strong><p>Check names you already have or feed the tool a custom wordlist.</p></div>
          <div class="card"><strong>🔐 Saved Accounts</strong><p>Generated single-name credentials can be stored locally in Windows Credential Manager.</p></div>
          <div class="card"><strong>🌐 Autofill companion</strong><p>Optional Chrome/Edge extension fills birthday, username, and generated password.</p></div>
          <div class="card"><strong>↵ Enter to submit</strong><p>After autofill, press Enter to activate Roblox's normal visible signup button.</p></div>
        </div>
      </section>
      <section id="download">
        <h2>Download from Releases</h2>
        <p class="sub">Normal users do not need Python or PyInstaller.</p>
        <div class="steps">
          <div class="step"><strong>Open GitHub Releases.</strong><br>Download the latest v2.5 Windows release.</div>
          <div class="step"><strong>Run the app.</strong><br>Launch <code>ScarnsNameSniffer.exe</code>.</div>
          <div class="step"><strong>Optional extension.</strong><br>Extract <code>ScarnsNameSniffer-Autofill-v2.5.zip</code>, enable Developer mode in Chrome/Edge, and use Load unpacked on the folder containing <code>manifest.json</code>.</div>
        </div>
      </section>
    </main>
    <footer><span>Unofficial community tool. Not affiliated with Roblox Corporation.</span><span>Scarn's Name Sniffer v2.5</span></footer>
  </div>
</body>
</html>
~~~~~


---

## FILE: `portable.flag.example`

Blob SHA: `d4e13cf2519efa56f394e37e1766498045d3ae07`

~~~~~text
Rename this file to portable.flag and place it beside ScarnsNameSniffer.exe to enable portable mode.

Portable mode stores scanner history, presets, exclusions, resume data, and exports under a local data/ folder beside the EXE.
~~~~~


---

## FILE: `requirements.txt`

Blob SHA: `0eb8cae7f9083d1b4e70d94cbd6ac82cd63476d9`

~~~~~text
requests>=2.31.0
~~~~~


---

## FILE: `roblox_name_gen.py`

Blob SHA: `81e49eecf53ed775669acb85e5060714eabb1592`

~~~~~python
#!/usr/bin/env python3
import requests, random, string, time, sys, re, os, webbrowser, subprocess, secrets, ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from collections import Counter
from datetime import datetime

LETTERS = string.ascii_lowercase
DIGITS  = string.digits
CHARSET = LETTERS + DIGITS
NUMBERS_ONLY = DIGITS
VOWELS  = set('aeiou')
MAX_WORKERS = 10
REQUEST_DELAY = 0.15

COMMON_BIGRAMS = {
    'th','he','in','er','an','re','ed','on','es','st','en','at',
    'to','nt','wa','hi','it','nd','ha','ou','ea','ng','al','ar',
    've','ra','le','sa','ro','li','se','la','ne','el','ma','ch',
    'sh','io','ti','ci','si','be','me','de','no','te','co','ca',
    'pa','ta','lo','fo','ho','mo','ke','so','wo','pe','qu','ph',
    'gh','ck','ke','ly','ty','ry','ny','ll','ss','tt','ff','bb',
    'dd','gg','mm','nn','pp','rr'
}
NICE_ENDINGS = {'er','ly','ed','en','al','el','le','on','an','ar',
                'ck','ng','ty','ry','ke','ne','ll','ss','tt'}
NICE_STARTS = {'th','he','re','be','de','co','ca','pa','ma','ta',
               'lo','ro','ho','mo','ke','se','le','ne','te','ve',
               'ra','st','wh','ch','sh','fl','tr','br','gr','pr',
               'dr','fr','pl','cl','bl','gl','cr','sp','sw','tw'}
CONS = list('bcdfghjklmnpqrstvwxyz')

PATTERNS_4 = ['CVCV','VCVC','CVCC','CCVC','VCCV','CVC']
PATTERNS_5 = ['CVCVC','CVCV','VCVCV','VCCVC','CVCCV','CVCVV','VVCVC','CCVCC','CVC','VCVC']
PATTERNS_6 = ['CVCVCV','VCVCVC','CVCCVC','VCCVCC','CVCVCC','VCVCCV','CCVCVC','CVCCVV']

APP_NAME = "Scarn's Name Sniffer"
APP_VER = "2.4"
ROBLOX_REGISTRATION_URL = "https://www.roblox.com/CreateAccount"
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
os.makedirs(SAVE_DIR, exist_ok=True)

# ── Secure account credential storage ─────────────────────────
PASSWORD_LOWER = "abcdefghijkmnopqrstuvwxyz"
PASSWORD_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
PASSWORD_DIGITS = "23456789"
PASSWORD_SYMBOLS = "!@#$%"


def generate_account_password(length=16):
    """Generate a strong password without ambiguous characters."""
    rng = secrets.SystemRandom()
    chars = [
        secrets.choice(PASSWORD_LOWER),
        secrets.choice(PASSWORD_UPPER),
        secrets.choice(PASSWORD_DIGITS),
        secrets.choice(PASSWORD_SYMBOLS),
    ]
    alphabet = PASSWORD_LOWER + PASSWORD_UPPER + PASSWORD_DIGITS + PASSWORD_SYMBOLS
    while len(chars) < max(12, length):
        chars.append(secrets.choice(alphabet))
    rng.shuffle(chars)
    return "".join(chars)


def save_windows_credential(username, password):
    """Save one Roblox credential in Windows Credential Manager.

    The password is stored as a Generic Credential under the current Windows
    account. Nothing is written to a plaintext password file.
    """
    if os.name != "nt":
        return False

    try:
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
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        cred_write = advapi32.CredWriteW
        cred_write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
        cred_write.restype = wintypes.BOOL

        blob = password.encode("utf-16-le")
        blob_buffer = ctypes.create_string_buffer(blob)

        credential = CREDENTIALW()
        credential.Flags = 0
        credential.Type = 1
        credential.TargetName = f"ScarnsNameSniffer:{username}"
        credential.Comment = f"Saved by {APP_NAME} v{APP_VER}"
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = 2
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = username

        return bool(cred_write(ctypes.byref(credential), 0))
    except Exception:
        return False


def make_autofill_payload(username, password, saved):
    return f"SCARN_AUTOFILL_V2|{username}|{password}|{1 if saved else 0}"

# ── Clipboard helper ──────────────────────────────────────────
def copy_to_clipboard(text):
    """Copy text to the Windows clipboard reliably."""
    text = str(text)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
        proc.communicate(text, timeout=5)
        if proc.returncode == 0: return True
    except Exception:
        pass
    try:
        proc = subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "[Console]::In.ReadToEnd() | Set-Clipboard"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
        proc.communicate(text, timeout=5)
        if proc.returncode == 0: return True
    except Exception:
        pass
    return False

def print_available(name, extra=""):
    print(f"    -> \033[92m{name}\033[0m  {extra}")

# ── Scoring ──────────────────────────────────────────────────
def is_wordlike(name):
    name = name.lower(); n = len(name)
    if n < 3 or not any(c in VOWELS for c in name): return 0
    cur_cons = 0
    for c in name:
        if c in VOWELS: cur_cons = 0
        else: cur_cons += 1
        if cur_cons > 3: return 0
    score = sum(2 for i in range(n-1) if name[i:i+2] in COMMON_BIGRAMS)
    if n >= 2 and name[-2:] in NICE_ENDINGS: score += 3
    if n >= 3 and name[-3:] in ('ing','ion','ent','ive','ble','ght'): score += 4
    if name[:2] in NICE_STARTS: score += 2
    vc = sum(1 for c in name if c in VOWELS)
    if vc in (2,3): score += 2
    elif vc in (1,4): score += 1
    dc = sum(1 for c in name if c in DIGITS)
    if dc > 2: score -= 2
    elif dc == 0: score += 1
    if n >= 4 and all((name[i] in VOWELS) != (name[i+1] in VOWELS) for i in range(n-1)): score += 3
    ugly = {'xz','zx','xq','qx','qq','zz','jj','vv','ww','yy','kk','hx','xj','jz','zq','qj'}
    for i in range(n-1):
        if name[i:i+2] in ugly: score -= 3
    return max(0, score)

def is_aesthetic(name): return is_wordlike(name) >= 5

def generate_aesthetic(length=5):
    if length < 3: return ''.join(random.choices(LETTERS, k=length))
    pattern_map = {4: PATTERNS_4, 5: PATTERNS_5, 6: PATTERNS_6}
    usable = pattern_map.get(length, []) or [p for p in (PATTERNS_4+PATTERNS_5+PATTERNS_6) if abs(len(p)-length) <= 1]
    if not usable: usable = PATTERNS_5
    name_chars=[]
    for ch in random.choice(usable):
        name_chars.append(random.choice(CONS) if ch == 'C' else random.choice(list(VOWELS)) if ch == 'V' else ch)
    result=''.join(name_chars)[:length]
    while len(result)<length: result += random.choice(LETTERS)
    leet={'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7'}
    if random.random()<0.25:
        idx=random.randrange(len(result))
        if result[idx] in leet and random.random()<0.5:
            lst=list(result); lst[idx]=leet[result[idx]]; result=''.join(lst)
    return result

def generate_random(length=5, charset=None): return ''.join(random.choices(charset or CHARSET, k=length))

def generate_from_word(word, length=5):
    word=word.strip().lower()
    if not word: return None
    if len(word)==length: return word
    if len(word)<length: return word + ''.join(random.choices(CHARSET, k=length-len(word)))
    return word[:length]

def save_results(names, mode_desc="batch", extra=""):
    timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"); filename=f"sniff_{timestamp}.txt"; filepath=os.path.join(SAVE_DIR,filename)
    with open(filepath,'w') as f:
        f.write(f"{APP_NAME} v{APP_VER}\nMode: {mode_desc}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*40}\n")
        for name in names: f.write(f"{name}\n")
        if extra: f.write(f"\n{extra}\n")
        f.write("\n--- made by scarn ---\n")
    print(f"\n  [SAVED] Results written to: {filepath}"); return filepath

def open_registration_page(name=None):
    if not name:
        try: webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL); print("    Opening Roblox Create Account...")
        except Exception as e: print(f"    Could not open browser: {e}")
        return
    password=generate_account_password(); saved=save_windows_credential(name,password); copied=copy_to_clipboard(make_autofill_payload(name,password,saved))
    print(f"    Saved '{name}' securely in Windows Credential Manager." if saved else "    Warning: Windows Credential Manager save failed.")
    print("    Prepared one-time autofill handoff for the browser companion." if copied else "    Clipboard handoff failed; browser autofill may need manual input.")
    try:
        webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL); print("    Opening Roblox Create Account..."); print("    Companion v2.4 will fill username/password and clear the clipboard handoff.")
    except Exception as e: print(f"    Could not open browser: {e}")

def open_signup_pages(names, max_tabs=10):
    selected=list(names[:max_tabs])
    if not selected: return
    print("    Bulk mode opens signup tabs only. Use single-name claim mode for secure password saving.")
    for i,_name in enumerate(selected):
        try:
            if i==0: webbrowser.open_new(ROBLOX_REGISTRATION_URL)
            else: webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL)
        except Exception: pass

TOKEN_LOCK=Lock(); CSRF_TOKEN=None; SESH=requests.Session(); SESH.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
def get_csrf_token():
    global CSRF_TOKEN
    try:
        resp=SESH.post("https://auth.roblox.com/v2/logout",timeout=10); tok=resp.headers.get("x-csrf-token")
        if tok: CSRF_TOKEN=tok; return tok
        resp2=SESH.get("https://www.roblox.com/",timeout=10); m=re.search(r'data-token="([^"]+)"',resp2.text)
        if m: CSRF_TOKEN=m.group(1); return m.group(1)
    except: pass
    return None
def ensure_token():
    global CSRF_TOKEN
    # Fast path: once initialized, concurrent validators avoid the lock.
    if CSRF_TOKEN:
        return CSRF_TOKEN
    with TOKEN_LOCK:
        if CSRF_TOKEN:
            return CSRF_TOKEN
        return get_csrf_token()
def refresh_token():
    with TOKEN_LOCK: return get_csrf_token()
def check_username(name):
    url="https://auth.roblox.com/v1/usernames/validate"; params={"request.username":name,"request.context":"Signup","request.birthday":"2000-01-01"}; token=ensure_token(); headers={"x-csrf-token":token} if token else {}
    try:
        resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==403:
            t2=refresh_token()
            if t2: headers["x-csrf-token"]=t2; resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==429:return(name,"ratelimited")
        if resp.status_code==403:return(name,"csrf_blocked")
        if resp.status_code!=200:return(name,f"http_{resp.status_code}")
        data=resp.json(); msg=data.get("message",""); code=data.get("code")
        if "Username is valid" in msg or "Valid username" in msg:return(name,"available")
        if "already in use" in msg or "AlreadyInUse" in msg:return(name,"taken")
        if "not appropriate" in msg or "inappropriate" in msg:return(name,"inappropriate")
        if "start or end with" in msg or "cannot start" in msg:return(name,"invalid_format")
        if code==0:return(name,"available")
        if code in(1,4):return(name,"taken")
        if code==2:return(name,"invalid_length")
        if code==3:return(name,"inappropriate")
        return(name,f"unknown({msg[:40]})")
    except requests.exceptions.RequestException as e:return(name,f"error({e})")
def check_username_v2(name):
    url="https://auth.roblox.com/v2/usernames/validate"; params={"request.username":name,"request.birthday":"04/15/2002","request.context":"Signup"}; token=ensure_token(); headers={"x-csrf-token":token} if token else {}
    try:
        resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==403:
            t2=refresh_token()
            if t2: headers["x-csrf-token"]=t2; resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code!=200:return(name,None)
        c=resp.json().get("code","")
        if "ValidUsername" in c:return(name,"available")
        if "AlreadyInUseError" in c:return(name,"taken")
        return(name,None)
    except:return(name,None)
def smart_check(name):
    r=check_username(name)
    if r[1] and (r[1].startswith("unknown") or r[1].startswith("error(")):
        r2=check_username_v2(name)
        if r2[1] is not None:return r2
    return r
p_lock=Lock()
def p_prog(name,status,found,total):
    with p_lock:
        mark="AVAILABLE <<<<" if status=="available" else "taken" if status=="taken" else (status or "?")[:25]; sys.stdout.write(f"\r  [{total:>4}] {name:<8} -> {mark:<30}"); sys.stdout.flush()
def pick_length():
    l=input("Name length? [4/5/6] (default 5): ").strip(); return int(l) if l in('4','6') else 5
def get_tab_count():
    ans=input("  Max browser tabs to open? (default 10, 0 to skip): ").strip()
    try:return max(0,int(ans))
    except:return 10
def claim_available_name(names):
    unique_names=list(dict.fromkeys(names))
    if not unique_names:return
    print("\n  CLAIM A NAME\n  "+"-"*36)
    for i,name in enumerate(unique_names,1):print(f"  [{i:>2}] {name}")
    while True:
        choice=input("\n  Choose a number to claim, [b] bulk open, or Enter to skip: ").strip().lower()
        if not choice:return
        if choice=='b': open_signup_pages(unique_names,get_tab_count()); return
        if choice.isdigit():
            idx=int(choice)-1
            if 0<=idx<len(unique_names):open_registration_page(unique_names[idx]); return
        print(f"  Enter a number from 1 to {len(unique_names)}, 'b', or press Enter to skip.")

def manual_lookup_mode():
    print("\n--- Manual Lookup Mode ---\nType usernames to check one at a time. Type 'done' to finish.\n"); found=[]; checked=[]
    while True:
        name=input("  Check name: ").strip()
        if not name or name.lower()=='done':break
        if not re.match(r'^[a-zA-Z0-9_]+$',name):print("    Invalid (letters, numbers, underscores only)");continue
        _,status=smart_check(name.lower());checked.append((name,status))
        if status=="available":print(f"    -> \033[92m{name.lower()}\033[0m: AVAILABLE!");found.append(name.lower())
        elif status=="taken":print(f"    -> {name}: Taken")
        else:print(f"    -> {name}: {status}")
    print(f"\n{'='*55}\n  MANUAL LOOKUP RESULTS\n{'='*55}")
    for n,s in checked: print(f"    \033[92m{n:<15}\033[0m -> AVAILABLE <<<<" if s=="available" else f"    {n:<15} -> {s}")
    if found:
        claim_available_name(found); ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
        if ans2!='n':save_results(found,"manual-lookup")
    print("\n--- made by scarn ---\n")

def wordlist_mode(length):
    path=input("Path to wordlist file: ").strip().replace('"','')
    if not os.path.exists(path):print(f"  File not found: {path}");return
    with open(path,'r',encoding='utf-8',errors='ignore') as f:words=[w.strip() for w in f.readlines() if w.strip()]
    variations=list(set(filter(None,[generate_from_word(w,length) for w in words])));print(f"  Loaded {len(words)} words from file\n  Generated {len(variations)} unique {length}-char variations\n\nChecking {len(variations)} names...\n")
    res=[]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in variations})):
            res.append(f.result());n,s=res[-1];p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
            if(i+1)%MAX_WORKERS==0:time.sleep(REQUEST_DELAY)
    av=[n for n,s in res if s=="available"];aest=[n for n in av if is_aesthetic(n)];rand=[n for n in av if not is_aesthetic(n)]
    print(f"\n\n{'='*55}\n  WORDLIST RESULTS ({length} chars) - Available: {len(av)}/{len(variations)}\n{'='*55}")
    if aest:
        print(f"\n  AESTHETIC ({len(aest)}):")
        for n in aest:print_available(n,f"({is_wordlike(n)}/10)")
    if rand:
        print(f"\n  RANDOM ({len(rand)}):")
        for n in rand:print_available(n)
    if av:
        claim_available_name(av);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
        if ans2!='n':save_results(av,"wordlist",f"Source: {path}")
    print("\n--- made by scarn ---\n")

if __name__=="__main__":
    try:
        print(f"{APP_NAME} v{APP_VER}".center(55));print("(Roblox username generator + availability checker)".center(55));print();print("Fetching CSRF token...",end=" ");tok=get_csrf_token();print(f"{'OK' if tok else 'FAILED'}\n")
        mode=input("Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist? ").strip().lower()
        if mode=='m':manual_lookup_mode()
        elif mode=='w':wordlist_mode(pick_length())
        elif mode=='a':
            length=pick_length();target=int(input("How many aesthetic names to find? ") or "5");max_c=int(input("Max checks? ") or "500");found=[];total=0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found)<target and total<max_c:
                    bs=min(MAX_WORKERS,max_c-total);names=[generate_aesthetic(length) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s=f.result();total+=1
                        if s=="available":found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}\n  AESTHETIC AVAILABLE ({length} chars): {len(found)}\n{'='*55}")
            for n in found:print_available(n)
            if found:
                claim_available_name(found);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(found,f"aesthetic-{length}char")
            print("\n--- made by scarn ---\n")
        elif mode=='s':
            length=pick_length();target=int(input("How many names to find? ") or "5");print("Charset options:\n  [L] Letters only (a-z)\n  [M] Mixed letters+digits (default)\n  [N] Numbers only (0-9)");cs_in=input("Choose: ").strip().lower();cs=LETTERS if cs_in=='l' else NUMBERS_ONLY if cs_in=='n' else CHARSET;max_c=int(input("Max checks? ") or "500");found=[];total=0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found)<target and total<max_c:
                    bs=min(MAX_WORKERS,max_c-total);names=[generate_random(length,cs) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s=f.result();total+=1
                        if s=="available":found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}\n  SCAN DONE - Checked {total}, found {len(found)} available ({length} chars)\n{'='*55}")
            for n in found:print_available(n)
            if not found:print("    (none found)")
            if found:
                claim_available_name(found);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(found,f"scan-{length}char")
            print("\n--- made by scarn ---\n")
        else:
            length=pick_length();batch=int(input("How many names? ") or "100");aeh=input("Aesthetic/word-like? [y/N]: ").strip().lower()=='y';print("Charset options:\n  [L] Letters only (a-z)\n  [M] Mixed letters+digits (default)\n  [N] Numbers only (0-9)");cs_in=input("Choose: ").strip().lower();cs=LETTERS if cs_in=='l' else NUMBERS_ONLY if cs_in=='n' else CHARSET;names=[generate_aesthetic(length) if aeh else generate_random(length,cs) for _ in range(batch)];res=[]
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in names})):
                    res.append(f.result());n,s=res[-1];p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
                    if(i+1)%MAX_WORKERS==0:time.sleep(REQUEST_DELAY)
            av=[n for n,s in res if s=="available"];aest=[n for n in av if is_aesthetic(n)];rand=[n for n in av if not is_aesthetic(n)]
            print(f"\n\n{'='*55}\n  RESULTS ({length} chars) - Available: {len(av)}/{batch}\n{'='*55}")
            if aest:
                print(f"\n  AESTHETIC ({len(aest)}):")
                for n in aest:print_available(n,f"({is_wordlike(n)}/10)")
            if rand:
                print(f"\n  RANDOM ({len(rand)}):")
                for n in rand:print_available(n)
            if av:
                claim_available_name(av);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(av,f"batch-{length}char")
            print("\n--- made by scarn ---\n")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nExiting.\n--- made by scarn ---");input("Press Enter to exit...")
~~~~~


---

## FILE: `tests/test_extension_email.py`

Blob SHA: `eae63a5ae5196779f41a9e91e690b194a9b3adbd`

~~~~~python
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "browser-extension"


def test_extension_manifest_wires_email_helper():
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["version"] == "2.5.1"
    assert manifest["background"]["service_worker"] == "background.js"
    assert "https://users.roblox.com/*" in manifest["host_permissions"]

    scripts = manifest["content_scripts"]
    assert any(
        "email.js" in entry.get("js", [])
        and "https://www.roblox.com/*" in entry.get("matches", [])
        for entry in scripts
    )


def test_popup_exposes_email_controls():
    html = (EXT / "popup.html").read_text(encoding="utf-8")
    assert 'id="email"' in html
    assert 'id="auto-email"' in html
    assert 'id="clear-email"' in html


def test_content_script_arms_email_without_persistent_password_storage():
    content = (EXT / "content.js").read_text(encoding="utf-8")
    assert "armEmailSetup" in content
    assert "scarn:storePendingSecret" in content
    assert "chrome.storage.session" not in content


def test_email_helper_stops_at_verification_request():
    email = (EXT / "email.js").read_text(encoding="utf-8")
    assert "scarn:getAuthenticatedUser" in email
    assert "findAddEmailButton" in email
    assert "findExistingEmailControl" in email
    assert "scarn:getPendingSecret" in email
    assert "Verification requested" in email
    assert "verify it manually" in email
    assert "inbox" in email.lower()


def test_background_owns_session_secret():
    background = (EXT / "background.js").read_text(encoding="utf-8")
    assert "chrome.storage.session.set" in background
    assert "chrome.storage.session.get" in background
    assert "chrome.storage.session.remove" in background
    assert "pendingSignupSecret" in background
~~~~~


---

## FILE: `tests/test_v25_engine.py`

Blob SHA: `2aa8abf3af54bd735c19ff09560490c467894e0c`

~~~~~python
import json
import time
from pathlib import Path

import v25_engine as eng


def test_cache_ttls_do_not_cache_errors():
    assert eng.ttl_for_status("taken") >= 30 * 24 * 60 * 60
    assert eng.ttl_for_status("available") < eng.ttl_for_status("taken")
    assert eng.ttl_for_status("ratelimited") == 0
    assert eng.ttl_for_status("error(timeout)") == 0
    assert eng.ttl_for_status("http_500") == 0


def test_filters_cover_digits_vowels_repeats_and_banned():
    cfg = eng.FilterConfig(
        allow_digits=False,
        allow_underscores=False,
        max_digits=0,
        must_start_letter=True,
        must_contain_vowel=True,
        avoid_repeats=True,
    )
    assert eng.passes_filters("sorin", cfg, [])
    assert not eng.passes_filters("s0rin", cfg, [])
    assert not eng.passes_filters("ssrin", cfg, [])
    assert not eng.passes_filters("srtn", cfg, [])
    assert not eng.passes_filters("badname", cfg, ["bad"])


def test_score_prefers_clean_wordlike_name():
    assert 0 <= eng.score_username("sorin") <= 100
    assert eng.score_username("sorin") > eng.score_username("xq77")
    assert eng.score_label(95) == "Excellent"


def test_mutation_engine_is_unique_ranked_and_length_aware():
    names = eng.mutate_word("scarn", target_length=5, limit=100)
    assert names
    assert len(names) == len(set(names))
    assert all(len(name) == 5 for name in names)
    assert "sc4rn" in names
    scores = [eng.score_username(n) for n in names]
    assert scores == sorted(scores, reverse=True)


def test_adaptive_workers_use_aimd_growth_and_hard_rate_limit_backoff():
    a = eng.AdaptiveWorkers(workers=12, minimum=4, maximum=32)
    a.observe(["taken"] * 12)
    assert a.workers == 12
    a.observe(["available"] + ["taken"] * 11)
    assert a.workers == 16
    a.observe(["ratelimited"] + ["taken"] * 15)
    assert a.workers == 8


def test_history_cache_expiry_and_watchlist(tmp_path):
    db = tmp_path / "history.sqlite3"
    store = eng.HistoryStore(db)
    store.record("Sorin", "taken", 88, "test")
    assert store.cached_status("sorin") == "taken"

    old = time.time() - eng.ttl_for_status("taken") - 10
    store.conn.execute("UPDATE checks SET checked_at=? WHERE username=?", (old, "sorin"))
    store.conn.commit()
    assert store.cached_status("sorin") is None

    store.add_watch("Sorin", "favorite")
    rows = store.watch_items()
    assert len(rows) == 1
    assert rows[0]["username"] == "sorin"
    store.remove_watch("sorin")
    assert store.watch_items() == []
    store.close()


def test_checkpoint_roundtrip(monkeypatch, tmp_path):
    target = tmp_path / "resume.json"
    monkeypatch.setattr(eng, "checkpoint_path", lambda: target)
    monkeypatch.setattr(eng, "ensure_support_files", lambda: None)
    eng.save_checkpoint({"mode": "scan", "checked": 42, "found": ["sorin"]})
    loaded = eng.load_checkpoint()
    assert loaded["checked"] == 42
    assert loaded["found"] == ["sorin"]
    assert "saved_at" in loaded
    eng.clear_checkpoint()
    assert not target.exists()


def test_presets_roundtrip(monkeypatch, tmp_path):
    target = tmp_path / "presets.json"
    target.write_text(json.dumps(eng.BUILTIN_PRESETS), encoding="utf-8")
    monkeypatch.setattr(eng, "presets_path", lambda: target)
    monkeypatch.setattr(eng, "ensure_support_files", lambda: None)
    presets = eng.load_presets()
    presets["mine"] = {"length": 5}
    eng.save_presets(presets)
    assert eng.load_presets()["mine"]["length"] == 5


def test_export_creates_txt_csv_json(monkeypatch, tmp_path):
    monkeypatch.setattr(eng, "exports_dir", lambda: tmp_path)
    rows = [eng.result_row("sorin", "available")]
    paths = eng.export_results(rows, "test")
    assert set(paths) == {"txt", "csv", "json"}
    for path in paths.values():
        assert Path(path).exists()
    assert "sorin" in Path(paths["txt"]).read_text(encoding="utf-8")
    assert json.loads(Path(paths["json"]).read_text(encoding="utf-8"))[0]["score"] == eng.score_username("sorin")


def test_version_comparison():
    assert eng.is_newer_version("2.5", "v2.5.1")
    assert eng.is_newer_version("2.5.9", "2.6.0")
    assert not eng.is_newer_version("2.5", "v2.5")
    assert not eng.is_newer_version("2.6", "v2.5.9")


def test_result_row_shape():
    row = eng.result_row("sorin", "available", "2026-01-01T00:00:00+00:00")
    assert row == {
        "username": "sorin",
        "status": "available",
        "score": eng.score_username("sorin"),
        "length": 5,
        "checked_at": "2026-01-01T00:00:00+00:00",
    }


def test_portable_mode_and_state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SCARN_PORTABLE", "1")
    monkeypatch.setattr(eng, "app_root", lambda: tmp_path)
    assert eng.portable_mode()
    assert eng.state_dir() == tmp_path / "data"
    assert eng.exports_dir() == tmp_path / "data" / "exports"


def test_history_batch_read_write(tmp_path):
    store = eng.HistoryStore(tmp_path / "batch.sqlite3")
    store.record_many([
        ("sorin", "taken", 0, "bulk"),
        ("melix", "available", 91, "validator"),
        ("badone", "inappropriate", 0, "validator"),
    ])

    cached = store.cached_status_many(["sorin", "melix", "badone", "missing"])
    assert cached == {
        "sorin": "taken",
        "melix": "available",
        "badone": "inappropriate",
    }
    assert store.summary()["total"] == 3
    store.close()


def test_unique_space_generator_is_full_permutation_and_resumable():
    generator = eng.UniqueSpaceGenerator(
        ["ab", "01", "xy"],
        multiplier=3,
        offset=1,
    )
    first = [next(generator) for _ in range(3)]
    snapshot = generator.snapshot()
    resumed = eng.UniqueSpaceGenerator.from_snapshot(snapshot)
    rest = list(resumed)

    combined = first + rest
    assert len(combined) == 8
    assert len(set(combined)) == 8
    assert set(combined) == {
        a + b + c
        for a in "ab"
        for b in "01"
        for c in "xy"
    }


def test_history_uses_large_sqlite_variable_limit_when_available(tmp_path):
    store = eng.HistoryStore(tmp_path / "vars.sqlite3")
    assert store.query_chunk_size >= 800
    store.close()
~~~~~


---

## FILE: `tests/test_v25_fastnet.py`

Blob SHA: `78e7707917adcba99e62b421f421d5c7f279c46d`

~~~~~python
import v25_fastnet as fastnet


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_chunks_use_100_name_batches():
    values = [f"name{i}" for i in range(205)]
    chunks = list(fastnet.chunks(values))
    assert [len(c) for c in chunks] == [100, 100, 5]


def test_bulk_lookup_maps_requested_usernames(monkeypatch):
    response = FakeResponse(
        200,
        {
            "data": [
                {"requestedUsername": "TakenOne", "name": "TakenOne", "id": 1},
                {"requestedUsername": "OtherTaken", "name": "OtherTaken", "id": 2},
            ]
        },
        {
            "x-ratelimit-limit": "500",
            "x-ratelimit-remaining": "499",
            "x-ratelimit-reset": "12",
        },
    )

    monkeypatch.setattr(fastnet._session, "post", lambda *a, **k: response)
    result = fastnet.bulk_existing(["takenone", "freeone", "othertaken"])

    assert result.ok
    assert result.existing == {"takenone", "othertaken"}
    assert result.rate_limit == 500
    assert result.rate_remaining == 499
    assert result.rate_reset == 12


def test_bulk_lookup_429_exposes_retry_information(monkeypatch):
    response = FakeResponse(429, {}, {"retry-after": "3"})
    monkeypatch.setattr(fastnet._session, "post", lambda *a, **k: response)

    result = fastnet.bulk_existing(["name"])
    assert not result.ok
    assert result.status_code == 429
    assert result.retry_after == 3
    assert result.error == "http_429"


def test_bulk_lookup_rejects_more_than_100_names():
    try:
        fastnet.bulk_existing([f"x{i}" for i in range(101)])
    except ValueError as exc:
        assert "at most 100" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_bulk_controller_aimd_and_cooldown():
    controller = fastnet.BulkConcurrencyController(
        workers=4, minimum=1, maximum=8
    )
    healthy = [fastnet.BulkLookupResult(["a"], {"a"}, True)]
    controller.observe(healthy)
    assert controller.workers == 4
    controller.observe(healthy)
    assert controller.workers == 5

    limited = [
        fastnet.BulkLookupResult(
            ["b"],
            set(),
            False,
            status_code=429,
            retry_after=2,
            error="http_429",
        )
    ]
    controller.observe(limited)
    assert controller.workers == 2
    assert controller.cooldown_seconds(limited) == 2


def test_bulk_existing_many_splits_thousand_names_into_ten_requests(monkeypatch):
    calls = []

    def fake_bulk(names, timeout=(3.05, 8.0)):
        calls.append(tuple(names))
        return fastnet.BulkLookupResult(
            requested=list(names),
            existing=set(names),
            ok=True,
            status_code=200,
        )

    monkeypatch.setattr(fastnet, "bulk_existing", fake_bulk)
    controller = fastnet.BulkConcurrencyController(
        workers=4, minimum=1, maximum=8
    )
    names = [f"name{i:04d}" for i in range(1000)]
    results, controller = fastnet.bulk_existing_many(names, controller)

    assert len(results) == 10
    assert len(calls) == 10
    assert all(len(call) == 100 for call in calls)
    assert sum(len(result.existing) for result in results) == 1000
~~~~~


---

## FILE: `tests/test_v25_scanner.py`

Blob SHA: `14194c453620f5281b7b34356f05694e343fc504`

~~~~~python
import time

import v25_engine as eng
import v25_fastnet as fastnet
import v25_scanner as scanner


class FakeStore:
    def __init__(self, cached=None):
        self.cached = cached or {}
        self.records = []

    def cached_status_many(self, names, now=None):
        return {name: self.cached[name] for name in names if name in self.cached}

    def record_many(self, rows, checked_at=None):
        self.records.extend(rows)

    def record(self, username, status, score=0, mode=""):
        self.records.append((username, status, score, mode))


def bulk_result(requested, existing=(), ok=True, status_code=200, retry_after=None, error=""):
    return fastnet.BulkLookupResult(
        requested=list(requested),
        existing=set(existing),
        ok=ok,
        status_code=status_code,
        retry_after=retry_after,
        error=error,
    )


def test_charset_respects_filter_flags():
    no_digits = eng.FilterConfig(allow_digits=False, allow_underscores=False)
    chars = scanner.charset_for("u", no_digits)
    assert "_" not in chars
    assert not any(c.isdigit() for c in chars)

    mixed = eng.FilterConfig(allow_digits=True, allow_underscores=True)
    chars2 = scanner.charset_for("u", mixed)
    assert "_" in chars2
    assert any(c.isdigit() for c in chars2)


def test_generate_unique_filters_seen_and_banned():
    values = iter(["sorin", "sorin", "badx", "xq77", "melix"])
    cfg = eng.FilterConfig(
        allow_digits=False,
        allow_underscores=False,
        must_start_letter=True,
        must_contain_vowel=True,
        avoid_repeats=True,
    )
    out = scanner.generate_unique(2, lambda: next(values), cfg, ["bad"], set())
    assert out == ["sorin", "melix"]


def test_checkpoint_payload_preserves_turbo_statistics():
    stats = eng.ScanStats(time.time() - 5)
    stats.checked = 20
    stats.network_checks = 12
    stats.cache_hits = 8
    stats.available = 2
    stats.taken = 16
    stats.inappropriate = 1
    stats.other = 1
    stats.http_requests = 4
    stats.bulk_requests = 2
    stats.bulk_resolved = 10
    stats.individual_validations = 2
    cfg = eng.FilterConfig(allow_digits=False)

    payload = scanner.checkpoint_payload(
        "scan", 5, 10, 500, ["sorin", "melix"], stats, cfg, "l", False
    )

    assert payload["checked"] == 20
    assert payload["network_checks"] == 12
    assert payload["cache_hits"] == 8
    assert payload["http_requests"] == 4
    assert payload["bulk_requests"] == 2
    assert payload["bulk_resolved"] == 10
    assert payload["individual_validations"] == 2
    assert payload["filters"]["allow_digits"] is False
    assert payload["elapsed"] >= 5


def test_cache_batch_never_touches_network(monkeypatch):
    def fail_bulk(names):
        raise AssertionError(f"bulk network called for cached names: {names}")

    def fail_validator(name):
        raise AssertionError(f"validator called for cached name: {name}")

    monkeypatch.setattr(scanner.fastnet, "bulk_existing", fail_bulk)
    monkeypatch.setattr(scanner.base, "smart_check", fail_validator)

    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=12)
    rows = scanner.check_candidates(
        ["sorin", "melix"],
        FakeStore({"sorin": "taken", "melix": "taken"}),
        stats,
        adaptive,
        "test",
        target=2,
        found=[],
    )

    assert len(rows) == 2
    assert stats.checked == 2
    assert stats.cache_hits == 2
    assert stats.network_checks == 0
    assert stats.http_requests == 0


def test_bulk_taken_names_skip_individual_validator(monkeypatch):
    monkeypatch.setattr(
        scanner.fastnet,
        "bulk_existing",
        lambda names: bulk_result(names, existing=set(names)),
    )

    def fail_validator(name):
        raise AssertionError(f"individual validator called for bulk-taken name {name}")

    monkeypatch.setattr(scanner.base, "smart_check", fail_validator)

    store = FakeStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=12)
    rows = scanner.check_candidates(
        ["sorin", "melix", "scarn"],
        store,
        stats,
        adaptive,
        "test",
        target=3,
        found=[],
    )

    assert all(row["status"] == "taken" for row in rows)
    assert stats.checked == 3
    assert stats.bulk_requests == 1
    assert stats.bulk_resolved == 3
    assert stats.individual_validations == 0
    assert stats.http_requests == 1
    assert len(store.records) == 3


def test_only_bulk_survivors_reach_individual_validator(monkeypatch):
    monkeypatch.setattr(
        scanner.fastnet,
        "bulk_existing",
        lambda names: bulk_result(names, existing={"takenone"}),
    )

    calls = []

    def validator(name):
        calls.append(name)
        return (name, "available" if name == "freeone" else "inappropriate")

    monkeypatch.setattr(scanner.base, "smart_check", validator)

    store = FakeStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=12)
    found = []
    rows = scanner.check_candidates(
        ["takenone", "freeone", "badone"],
        store,
        stats,
        adaptive,
        "test",
        target=3,
        found=found,
    )

    assert set(calls) == {"freeone", "badone"}
    statuses = {row["username"]: row["status"] for row in rows}
    assert statuses == {
        "takenone": "taken",
        "freeone": "available",
        "badone": "inappropriate",
    }
    assert found == ["freeone"]
    assert stats.bulk_requests == 1
    assert stats.bulk_resolved == 1
    assert stats.individual_validations == 2
    assert stats.http_requests == 3


def test_target_scan_can_stop_after_survivor_wave(monkeypatch):
    monkeypatch.setattr(
        scanner.fastnet,
        "bulk_existing",
        lambda names: bulk_result(names, existing=set()),
    )

    calls = []

    def validator(name):
        calls.append(name)
        return (name, "available")

    monkeypatch.setattr(scanner.base, "smart_check", validator)

    store = FakeStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=2, minimum=2, maximum=2)
    found = []

    scanner.check_candidates(
        ["aone", "atwo", "athree", "afour"],
        store,
        stats,
        adaptive,
        "test",
        target=1,
        found=found,
        stop_after_available=1,
    )

    assert len(calls) == 2
    assert len(found) >= 1


def test_thousand_taken_names_collapse_to_ten_bulk_requests(monkeypatch):
    def all_taken(names):
        return bulk_result(names, existing=set(names))

    monkeypatch.setattr(scanner.fastnet, "bulk_existing", all_taken)
    monkeypatch.setattr(
        scanner.base,
        "smart_check",
        lambda name: (_ for _ in ()).throw(
            AssertionError("all names should be resolved by bulk lookup")
        ),
    )

    store = FakeStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=20)
    candidates = [f"name{i:04d}" for i in range(1000)]
    found = []

    rows = scanner.check_candidates(
        candidates,
        store,
        stats,
        adaptive,
        "benchmark",
        target=len(candidates),
        found=found,
    )

    assert len(rows) == 1000
    assert stats.checked == 1000
    assert stats.bulk_resolved == 1000
    assert stats.bulk_requests == 10
    assert stats.http_requests == 10
    assert stats.individual_validations == 0
    assert stats.network_checks / stats.http_requests == 100


def test_cached_available_target_prevents_unneeded_bulk_request(monkeypatch):
    monkeypatch.setattr(
        scanner.fastnet,
        "bulk_existing",
        lambda names: (_ for _ in ()).throw(
            AssertionError(f"bulk request should have been skipped: {names}")
        ),
    )
    monkeypatch.setattr(
        scanner.base,
        "smart_check",
        lambda name: (_ for _ in ()).throw(
            AssertionError(f"validator should have been skipped: {name}")
        ),
    )

    store = FakeStore({"freeone": "available"})
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=16)
    found = []

    rows = scanner.check_candidates(
        ["freeone", "uncachedone"],
        store,
        stats,
        adaptive,
        "target",
        target=1,
        found=found,
        stop_after_available=1,
    )

    assert [row["username"] for row in rows] == ["freeone"]
    assert found == ["freeone"]
    assert stats.cache_hits == 1
    assert stats.http_requests == 0


def test_structural_generator_never_starts_or_ends_with_underscore():
    cfg = eng.FilterConfig(
        allow_digits=True,
        allow_underscores=True,
        must_start_letter=True,
    )
    source = scanner.build_unique_generator(4, "ab1_", cfg)
    names = [next(source) for _ in range(min(50, source.size))]
    assert len(names) == len(set(names))
    assert all(name[0].isalpha() for name in names)
    assert all(not name.startswith("_") and not name.endswith("_") for name in names)


def test_unique_source_generation_does_not_need_seen_set():
    cfg = eng.FilterConfig()
    source = eng.UniqueSpaceGenerator(["ab", "01"], multiplier=3, offset=0)
    out = scanner.generate_unique(
        4,
        source.__next__,
        cfg,
        [],
        seen=None,
        source_unique=True,
    )
    assert len(out) == 4
    assert len(set(out)) == 4


def test_pipeline_stops_before_consuming_second_bulk_result(monkeypatch):
    class EarlyStopScheduler:
        def __init__(self):
            self.controller = fastnet.BulkConcurrencyController(
                workers=2, minimum=1, maximum=2
            )
            self.submitted_requests = 0

        def iter_lookup_many(self, names):
            self.submitted_requests += 2
            yield bulk_result(["freeone"], existing=set())
            raise AssertionError(
                "second bulk result was consumed after target was already reached"
            )

    calls = []

    def validator(name):
        calls.append(name)
        return (name, "available")

    monkeypatch.setattr(scanner.base, "smart_check", validator)

    store = FakeStore()
    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=1, minimum=1, maximum=1)
    found = []
    scheduler = EarlyStopScheduler()

    scanner.check_candidates(
        ["freeone", "laterone"],
        store,
        stats,
        adaptive,
        "pipeline",
        target=1,
        found=found,
        stop_after_available=1,
        bulk_scheduler=scheduler,
    )

    assert calls == ["freeone"]
    assert found == ["freeone"]
    assert stats.bulk_requests == 2
~~~~~


---

## FILE: `v25_engine.py`

Blob SHA: `dc13d5dbc8c7a576005d684b13586ad327d9b36d`

~~~~~python
#!/usr/bin/env python3
"""Feature engine for Scarn's Name Sniffer v2.5."""
from __future__ import annotations
import csv, json, math, os, re, secrets, sqlite3, sys, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "ScarnsNameSniffer"
REPO = "NNoradrenaline/ScarnsNameSniffer"
GITHUB_LATEST_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"
DEFAULT_WORKERS, MIN_WORKERS, MAX_WORKERS = 16, 4, 32
CACHE_TTLS = {"available": 900, "taken": 2592000, "inappropriate": 7776000, "invalid_format": 7776000, "invalid_length": 7776000}
DEFAULT_CACHE_TTL = 3600
BUILTIN_PRESETS = {
    "rare-4": {"description":"4-character letters only, clean filtering","length":4,"target":10,"max_checks":1000,"aesthetic":False,"filters":{"allow_digits":False,"allow_underscores":False,"max_digits":0,"must_start_letter":True,"must_contain_vowel":False,"avoid_repeats":True}},
    "clean-5": {"description":"5-character word-like names with no digits","length":5,"target":10,"max_checks":1000,"aesthetic":True,"filters":{"allow_digits":False,"allow_underscores":False,"max_digits":0,"must_start_letter":True,"must_contain_vowel":True,"avoid_repeats":True}},
    "mixed-6": {"description":"6-character mixed names with at most one digit","length":6,"target":10,"max_checks":1000,"aesthetic":False,"filters":{"allow_digits":True,"allow_underscores":False,"max_digits":1,"must_start_letter":True,"must_contain_vowel":False,"avoid_repeats":True}},
}

def utc_now_ts(): return time.time()
def utc_iso(ts=None): return datetime.fromtimestamp(ts or utc_now_ts(), tz=timezone.utc).isoformat()
def app_root(): return Path(sys.executable if getattr(sys,"frozen",False) else __file__).resolve().parent
def portable_mode():
    env=os.environ.get("SCARN_PORTABLE","").strip().lower()
    return env in {"1","true","yes","on"} or (app_root()/"portable.flag").exists()
def state_dir():
    if portable_mode(): path=app_root()/"data"
    elif os.name=="nt": path=Path(os.environ.get("LOCALAPPDATA") or Path.home())/APP_NAME
    else: path=Path.home()/".scarns_name_sniffer"
    path.mkdir(parents=True,exist_ok=True); return path
def exports_dir():
    if portable_mode(): path=state_dir()/"exports"
    else:
        desktop=Path.home()/"Desktop"; path=desktop if desktop.exists() else state_dir()/"exports"
    path.mkdir(parents=True,exist_ok=True); return path
def db_path(): return state_dir()/"history.sqlite3"
def checkpoint_path(): return state_dir()/"resume.json"
def presets_path(): return state_dir()/"presets.json"
def excluded_patterns_path(): return state_dir()/"excluded_patterns.txt"
def ensure_support_files():
    p=excluded_patterns_path()
    if not p.exists(): p.write_text("# One substring or regular expression per line.\n# Blank lines and lines beginning with # are ignored.\n",encoding="utf-8")
    p2=presets_path()
    if not p2.exists(): p2.write_text(json.dumps(BUILTIN_PRESETS,indent=2),encoding="utf-8")


class UniqueSpaceGenerator:
    """Random-looking permutation of a finite username space.

    Every value is produced at most once without needing a growing duplicate
    set. Position-specific alphabets let the scanner enforce cheap structural
    rules such as "must start with a letter" before network work begins.
    """

    def __init__(self, alphabets, multiplier=None, offset=None, index=0):
        self.alphabets = [tuple(dict.fromkeys(chars)) for chars in alphabets]
        if not self.alphabets or any(not chars for chars in self.alphabets):
            raise ValueError("every position needs at least one character")
        self.radices = [len(chars) for chars in self.alphabets]
        self.size = math.prod(self.radices)
        self.index = int(index)

        if multiplier is None:
            if self.size <= 1:
                multiplier = 1
            else:
                while True:
                    candidate = secrets.randbelow(self.size - 1) + 1
                    if math.gcd(candidate, self.size) == 1:
                        multiplier = candidate
                        break
        if math.gcd(int(multiplier), self.size) != 1:
            raise ValueError("multiplier must be coprime with username-space size")

        self.multiplier = int(multiplier)
        self.offset = secrets.randbelow(self.size) if offset is None else int(offset) % self.size

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.size:
            raise StopIteration
        value = (self.multiplier * self.index + self.offset) % self.size
        self.index += 1

        chars = [""] * len(self.alphabets)
        for pos in range(len(self.alphabets) - 1, -1, -1):
            radix = self.radices[pos]
            value, digit = divmod(value, radix)
            chars[pos] = self.alphabets[pos][digit]
        return "".join(chars)

    def snapshot(self):
        return {
            "alphabets": ["".join(chars) for chars in self.alphabets],
            "multiplier": self.multiplier,
            "offset": self.offset,
            "index": self.index,
        }

    @classmethod
    def from_snapshot(cls, payload):
        return cls(
            payload["alphabets"],
            multiplier=payload["multiplier"],
            offset=payload["offset"],
            index=payload.get("index", 0),
        )

@dataclass
class FilterConfig:
    allow_digits: bool=True
    allow_underscores: bool=False
    max_digits: int=99
    must_start_letter: bool=True
    must_contain_vowel: bool=False
    avoid_repeats: bool=False
    @classmethod
    def from_dict(cls,data):
        data=data or {}; return cls(**{k:data[k] for k in cls.__dataclass_fields__ if k in data})

@dataclass
class ScanStats:
    started_at: float
    checked:int=0; network_checks:int=0; cache_hits:int=0; available:int=0; taken:int=0; inappropriate:int=0; other:int=0
    http_requests:int=0; bulk_requests:int=0; bulk_resolved:int=0; individual_validations:int=0
    def record(self,status,cached=False):
        self.checked+=1; self.cache_hits+=int(cached); self.network_checks+=int(not cached)
        if status=="available": self.available+=1
        elif status=="taken": self.taken+=1
        elif status=="inappropriate": self.inappropriate+=1
        else: self.other+=1
    @property
    def elapsed(self): return max(.001,time.time()-self.started_at)
    @property
    def speed(self): return self.checked/self.elapsed

class AdaptiveWorkers:
    def __init__(self,workers=DEFAULT_WORKERS,minimum=MIN_WORKERS,maximum=MAX_WORKERS):
        self.minimum=minimum; self.maximum=maximum; self.workers=max(minimum,min(maximum,workers)); self.healthy_streak=0
    def observe(self,statuses):
        """AIMD-style concurrency control: ramp on health, cut hard on 429."""
        statuses=list(statuses)
        if not statuses:return self.workers
        rl=sum(s=="ratelimited" for s in statuses)
        errors=sum(s=="csrf_blocked" or s.startswith("http_") or s.startswith("error(") for s in statuses)
        if rl:
            self.workers=max(self.minimum,max(1,self.workers//2)); self.healthy_streak=0
        elif errors/len(statuses)>=.25:
            self.workers=max(self.minimum,self.workers-4); self.healthy_streak=0
        else:
            self.healthy_streak+=1
            if self.healthy_streak>=2:
                self.workers=min(self.maximum,self.workers+4); self.healthy_streak=0
        return self.workers

class HistoryStore:
    def __init__(self,path=None):
        self.path=Path(path or db_path()); self.path.parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA cache_size=-16000")
        self.conn.execute("PRAGMA mmap_size=268435456")
        self.query_chunk_size = 800
        try:
            for row in self.conn.execute("PRAGMA compile_options"):
                option = row[0]
                if option.startswith("MAX_VARIABLE_NUMBER="):
                    limit = int(option.split("=", 1)[1])
                    self.query_chunk_size = max(800, min(5000, limit - 16))
                    break
        except Exception:
            pass
        self._init_schema()
    def _init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS checks(username TEXT PRIMARY KEY,status TEXT NOT NULL,checked_at REAL NOT NULL,score INTEGER NOT NULL DEFAULT 0,mode TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status);
        CREATE INDEX IF NOT EXISTS idx_checks_checked_at ON checks(checked_at);
        CREATE TABLE IF NOT EXISTS watchlist(username TEXT PRIMARY KEY,added_at REAL NOT NULL,note TEXT NOT NULL DEFAULT '');
        """); self.conn.commit()
    def close(self): self.conn.close()
    def record_many(self,records,checked_at=None):
        rows=[]
        now=utc_now_ts() if checked_at is None else float(checked_at)
        for record in records:
            if isinstance(record,dict):
                rows.append((str(record["username"]).lower(),str(record["status"]),float(record.get("checked_at_ts",now)),int(record.get("score",0)),str(record.get("mode",""))))
            else:
                username,status,score,mode=record
                rows.append((str(username).lower(),str(status),now,int(score),str(mode)))
        if not rows:return
        self.conn.executemany("""INSERT INTO checks(username,status,checked_at,score,mode) VALUES(?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET status=excluded.status,checked_at=excluded.checked_at,score=excluded.score,mode=excluded.mode""",rows)
        self.conn.commit()
    def record(self,username,status,score=0,mode=""):
        self.record_many([(username,status,score,mode)])
    def get(self,username): return self.conn.execute("SELECT * FROM checks WHERE username=?",(username.lower(),)).fetchone()
    def cached_status_many(self,usernames,now=None):
        names=list(dict.fromkeys(str(name).lower() for name in usernames if name))
        if not names:return {}
        current=utc_now_ts() if now is None else float(now)
        result={}
        for offset in range(0,len(names),self.query_chunk_size):
            chunk=names[offset:offset+self.query_chunk_size]
            placeholders=",".join("?" for _ in chunk)
            rows=self.conn.execute(f"SELECT username,status,checked_at FROM checks WHERE username IN ({placeholders})",chunk).fetchall()
            for row in rows:
                ttl=ttl_for_status(row["status"])
                if ttl>0 and current-float(row["checked_at"])<=ttl:
                    result[row["username"]]=row["status"]
        return result
    def cached_status(self,username,now=None):
        return self.cached_status_many([username],now).get(username.lower())
    def add_watch(self,username,note=""):
        self.conn.execute("""INSERT INTO watchlist(username,added_at,note) VALUES(?,?,?) ON CONFLICT(username) DO UPDATE SET note=excluded.note""",(username.lower(),utc_now_ts(),note)); self.conn.commit()
    def remove_watch(self,username): self.conn.execute("DELETE FROM watchlist WHERE username=?",(username.lower(),)); self.conn.commit()
    def watch_items(self): return self.conn.execute("""SELECT w.username,w.added_at,w.note,c.status,c.checked_at,c.score FROM watchlist w LEFT JOIN checks c ON c.username=w.username ORDER BY w.added_at DESC""").fetchall()
    def summary(self):
        total=self.conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
        statuses={r[0]:r[1] for r in self.conn.execute("SELECT status,COUNT(*) FROM checks GROUP BY status")}
        watches=self.conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        return {"total":total,"statuses":statuses,"watchlist":watches}

def ttl_for_status(status):
    if status=="ratelimited" or status=="csrf_blocked" or status.startswith("error(") or status.startswith("http_") or status.startswith("unknown"): return 0
    return CACHE_TTLS.get(status,DEFAULT_CACHE_TTL)
def load_banned_patterns(path=None):
    p=Path(path or excluded_patterns_path())
    if not p.exists():return []
    return [x.strip() for x in p.read_text(encoding="utf-8",errors="ignore").splitlines() if x.strip() and not x.strip().startswith("#")]
def matches_banned(name,patterns):
    lower=name.lower()
    for pattern in patterns:
        try:
            if re.search(pattern,lower,re.I):return True
        except re.error:
            if pattern.lower() in lower:return True
    return False
def passes_filters(name,config,banned_patterns=None):
    if not name:return False
    if not config.allow_digits and any(c.isdigit() for c in name):return False
    if not config.allow_underscores and "_" in name:return False
    if sum(c.isdigit() for c in name)>config.max_digits:return False
    if config.must_start_letter and not name[0].isalpha():return False
    if config.must_contain_vowel and not any(c.lower() in "aeiou" for c in name):return False
    if config.avoid_repeats and any(a==b for a,b in zip(name,name[1:])):return False
    if matches_banned(name,banned_patterns or []):return False
    return True
COMMON_BIGRAMS={"th","he","in","er","an","re","on","at","en","nd","st","to","it","ha","ou","ea","ng","al","ar","le","se","or","te","co","de","ra","ri","ne","ma","li","ro","ch","sh","tr","br","cr","dr","fr","gr","pr","cl","fl","gl","pl","sl","sp","sw","sk"}
UGLY_BIGRAMS={"qx","xq","qj","jq","zx","xz","vv","qq","jj","ww","zz"}
def score_username(name):
    if not name:return 0
    lower=name.lower(); score=45; digits=sum(c.isdigit() for c in lower); underscores=lower.count("_"); vowels=sum(c in "aeiou" for c in lower); alpha=sum(c.isalpha() for c in lower)
    if lower[0].isalpha():score+=6
    if lower[-1].isalpha():score+=3
    if 4<=len(lower)<=6:score+=5
    score+=min(18,sum(4 for i in range(len(lower)-1) if lower[i:i+2] in COMMON_BIGRAMS)); score-=sum(9 for i in range(len(lower)-1) if lower[i:i+2] in UGLY_BIGRAMS)
    if alpha and vowels:
        ratio=vowels/alpha
        if .25<=ratio<=.60:score+=10
        elif ratio<.15 or ratio>.75:score-=6
    if digits==0:score+=8
    elif digits==1:score+=2
    else:score-=min(18,(digits-1)*6)
    score-=underscores*5
    if len(set(lower))==len(lower):score+=4
    if any(a==b for a,b in zip(lower,lower[1:])):score-=7
    if re.search(r"[a-z]\d[a-z]\d|\d[a-z]\d[a-z]",lower):score-=5
    return max(0,min(100,int(score)))
def score_label(score):
    return "Excellent" if score>=90 else "Great" if score>=80 else "Good" if score>=65 else "Fair" if score>=45 else "Random"
def mutate_word(word,target_length=None,limit=200):
    word=re.sub(r"[^a-zA-Z0-9_]","",word.strip().lower())
    if not word:return []
    out={word}; leet={"a":"4","e":"3","i":"1","o":"0","s":"5","t":"7"}; subs={"c":"k","k":"c","s":"z","z":"s","v":"x","x":"v"}
    for i,ch in enumerate(word):
        if ch in leet:out.add(word[:i]+leet[ch]+word[i+1:])
        if ch in subs:out.add(word[:i]+subs[ch]+word[i+1:])
        out.add(word[:i]+word[i+1:])
    for suffix in ("x","z","v","r","n","s","7","1","0"):out.add(word+suffix)
    for prefix in ("x","v","z","i"):out.add(prefix+word)
    if len(word)>=2:out.add(word[:-1]+word[-1]*2);out.add(word[0]*2+word[1:])
    if target_length:
        expanded=set()
        for item in out:
            if len(item)==target_length:expanded.add(item)
            elif len(item)>target_length:expanded.add(item[:target_length])
            else:
                for suffix in ("x","z","7","1","0","v","r","n"):expanded.add((item+suffix*target_length)[:target_length])
        out=expanded
    return sorted(out,key=lambda n:(-score_username(n),n))[:limit]
def save_checkpoint(data):
    ensure_support_files()
    payload=dict(data)
    payload["saved_at"]=utc_iso()
    checkpoint_path().write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
    return checkpoint_path()
def load_checkpoint():
    p=checkpoint_path()
    if not p.exists():return None
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None
def clear_checkpoint():
    try:checkpoint_path().unlink()
    except FileNotFoundError:pass
def load_presets():
    ensure_support_files()
    try:
        data=json.loads(presets_path().read_text(encoding="utf-8"));return data if isinstance(data,dict) else dict(BUILTIN_PRESETS)
    except Exception:return dict(BUILTIN_PRESETS)
def save_presets(data):presets_path().write_text(json.dumps(data,indent=2),encoding="utf-8")
def export_results(results,prefix="scan"):
    rows=list(results);stamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S");base=exports_dir()/f"{prefix}_{stamp}"
    paths={"txt":str(base.with_suffix(".txt")),"csv":str(base.with_suffix(".csv")),"json":str(base.with_suffix(".json"))}
    with open(paths["txt"],"w",encoding="utf-8") as f:
        for row in rows:f.write(f"{row.get('username','')}\n")
    fields=["username","status","score","length","checked_at"]
    with open(paths["csv"],"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();[w.writerow(r) for r in rows]
    with open(paths["json"],"w",encoding="utf-8") as f:json.dump(rows,f,indent=2)
    return paths
def version_tuple(value):
    nums=re.findall(r"\d+",value or "");return tuple(int(n) for n in nums[:4]) or (0,)
def is_newer_version(current,latest):
    a=version_tuple(current);b=version_tuple(latest);width=max(len(a),len(b));return b+(0,)*(width-len(b))>a+(0,)*(width-len(a))
def format_duration(seconds):
    seconds=max(0,int(seconds));minutes,sec=divmod(seconds,60);hours,minutes=divmod(minutes,60);return f"{hours:02d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"
def result_row(username,status,checked_at=None):
    return {"username":username,"status":status,"score":score_username(username),"length":len(username),"checked_at":checked_at or utc_iso()}
ensure_support_files()
~~~~~
