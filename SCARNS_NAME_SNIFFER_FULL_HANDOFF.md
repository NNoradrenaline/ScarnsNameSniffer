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
