#!/usr/bin/env python3
"""Scarn's Name Sniffer v2.6 scanning engine.

Adds verified availability, SQLite caching/history, adaptive concurrency,
resume checkpoints, live metrics, watchlists, diagnostics, and ranked
candidate generation on top of the stable scanner/credential code.
"""

import csv
import json
import os
import random
import shutil
import sqlite3
import sys
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import roblox_name_gen as base
import v25_launcher as accounts

APP_VER = "2.6"
base.APP_VER = APP_VER

DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "ScarnsNameSniffer",
)
DB_PATH = os.path.join(DATA_DIR, "sniffer.db")
CACHE_TTL_SECONDS = 15 * 60
MIN_WORKERS = 3
MAX_WORKERS = 12
START_WORKERS = 6
USERS_LOOKUP_URL = "https://users.roblox.com/v1/usernames/users"
DB_LOCK = threading.Lock()
THREAD_LOCAL = threading.local()

os.makedirs(DATA_DIR, exist_ok=True)


def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    with DB_LOCK:
        with db_connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS checks (
                    username TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    checked_at REAL NOT NULL,
                    latency_ms REAL NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS scan_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    checked_count INTEGER NOT NULL DEFAULT 0,
                    found_json TEXT NOT NULL DEFAULT '[]',
                    unverified_json TEXT NOT NULL DEFAULT '[]',
                    started_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    username TEXT PRIMARY KEY,
                    priority INTEGER NOT NULL DEFAULT 2,
                    added_at REAL NOT NULL,
                    last_status TEXT,
                    last_checked REAL
                );
                """
            )


def cache_get(username, max_age=CACHE_TTL_SECONDS):
    now = time.time()
    with DB_LOCK:
        with db_connect() as conn:
            row = conn.execute(
                "SELECT status, verified, score, checked_at, latency_ms "
                "FROM checks WHERE username = ?",
                (username.lower(),),
            ).fetchone()
    if not row or now - row[3] > max_age:
        return None
    return {
        "name": username.lower(),
        "status": row[0],
        "verified": bool(row[1]),
        "score": row[2],
        "latency_ms": row[4],
        "cached": True,
    }


def cache_put(result):
    with DB_LOCK:
        with db_connect() as conn:
            conn.execute(
                """
                INSERT INTO checks(username, status, verified, score, checked_at, latency_ms)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    status=excluded.status,
                    verified=excluded.verified,
                    score=excluded.score,
                    checked_at=excluded.checked_at,
                    latency_ms=excluded.latency_ms
                """,
                (
                    result["name"].lower(),
                    result["status"],
                    1 if result.get("verified") else 0,
                    int(result.get("score", 0)),
                    time.time(),
                    float(result.get("latency_ms", 0)),
                ),
            )


def score_name(name):
    """Return a stable 0-100 quality score for display/ranking."""
    n = name.lower()
    base_score = min(10, base.is_wordlike(n))
    score = 25 + base_score * 7

    digits = sum(ch.isdigit() for ch in n)
    underscores = n.count("_")
    if digits == 0:
        score += 5
    elif digits == 1:
        score -= 2
    else:
        score -= 8 + (digits - 2) * 4

    if underscores:
        score -= underscores * 5

    if any(n[i] == n[i + 1] for i in range(len(n) - 1)):
        score -= 5

    if n.isalpha() and 4 <= len(n) <= 6:
        score += 4

    return max(0, min(100, score))


def generate_ranked(length, charset=None, aesthetic=True):
    """Best-of-N generation so the scanner spends requests on stronger candidates."""
    charset = charset or base.CHARSET
    pool = []
    attempts = 10 if aesthetic else 4
    for _ in range(attempts):
        if aesthetic:
            candidate = base.generate_aesthetic(length)
            if charset == base.LETTERS:
                candidate = "".join(ch for ch in candidate if ch.isalpha())
                while len(candidate) < length:
                    candidate += random.choice(base.LETTERS)
                candidate = candidate[:length]
            elif charset == base.NUMBERS_ONLY:
                candidate = base.generate_random(length, base.NUMBERS_ONLY)
        else:
            candidate = base.generate_random(length, charset)
        pool.append(candidate.lower())
    return max(pool, key=score_name)


def _http_session():
    session = getattr(THREAD_LOCAL, "session", None)
    if session is None:
        session = base.requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 ScarnsNameSniffer/2.6"
                )
            }
        )
        THREAD_LOCAL.session = session
    return session


def second_stage_verify(username):
    """Confirm that no Roblox user resolves to the candidate username."""
    try:
        response = _http_session().post(
            USERS_LOOKUP_URL,
            json={"usernames": [username], "excludeBannedUsers": False},
            timeout=10,
        )
        if response.status_code == 429:
            return "ratelimited"
        if response.status_code != 200:
            return "unavailable_verifier"
        data = response.json().get("data", [])
        for item in data:
            if str(item.get("name", "")).lower() == username.lower():
                return "taken"
        return "clear"
    except Exception:
        return "unavailable_verifier"


def network_check(username):
    started = time.perf_counter()
    name, first_status = base.smart_check(username.lower())
    verified = False
    status = first_status

    if first_status == "available":
        second = second_stage_verify(name)
        if second == "clear":
            status = "verified_available"
            verified = True
        elif second == "taken":
            status = "taken"
        elif second == "ratelimited":
            status = "ratelimited"
        else:
            status = "available_unverified"

    latency_ms = (time.perf_counter() - started) * 1000
    result = {
        "name": name,
        "status": status,
        "verified": verified,
        "score": score_name(name),
        "latency_ms": latency_ms,
        "cached": False,
    }
    cache_put(result)
    return result


class AdaptiveScanner:
    def __init__(self, workers=START_WORKERS):
        self.workers = max(MIN_WORKERS, min(MAX_WORKERS, workers))
        self.latencies = deque(maxlen=60)
        self.cache_hits = 0
        self.network_checks = 0
        self.rate_limits = 0
        self.started = time.perf_counter()

    def check_one(self, username, use_cache=True):
        if use_cache:
            cached = cache_get(username)
            if cached:
                self.cache_hits += 1
                return cached
        result = network_check(username)
        self.network_checks += 1
        self.latencies.append(result["latency_ms"])
        if result["status"] == "ratelimited":
            self.rate_limits += 1
        return result

    def run_batch(self, names):
        before_limits = self.rate_limits
        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self.check_one, name): name for name in names}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    name = futures[future]
                    results.append(
                        {
                            "name": name,
                            "status": f"error({exc})",
                            "verified": False,
                            "score": score_name(name),
                            "latency_ms": 0,
                            "cached": False,
                        }
                    )

        batch_limits = self.rate_limits - before_limits
        network_in_batch = sum(not r.get("cached") for r in results)
        avg_latency = (
            sum(r["latency_ms"] for r in results if not r.get("cached"))
            / max(1, network_in_batch)
        )

        cooldown = 0
        if batch_limits:
            self.workers = max(MIN_WORKERS, self.workers // 2)
            cooldown = min(15, 2 + batch_limits * 2)
        elif network_in_batch and avg_latency < 450 and self.workers < MAX_WORKERS:
            self.workers += 1
        elif avg_latency > 1200 and self.workers > MIN_WORKERS:
            self.workers -= 1

        return results, cooldown

    def avg_latency(self):
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0

    def elapsed(self):
        return max(0.001, time.perf_counter() - self.started)


def create_checkpoint(mode, config):
    now = time.time()
    with DB_LOCK:
        with db_connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO scan_checkpoints(
                    mode, config_json, checked_count, found_json,
                    unverified_json, started_at, updated_at, active
                ) VALUES (?, ?, 0, '[]', '[]', ?, ?, 1)
                """,
                (mode, json.dumps(config), now, now),
            )
            return cur.lastrowid


def save_checkpoint(checkpoint_id, checked_count, found, unverified, active=True):
    with DB_LOCK:
        with db_connect() as conn:
            conn.execute(
                """
                UPDATE scan_checkpoints
                SET checked_count=?, found_json=?, unverified_json=?,
                    updated_at=?, active=?
                WHERE id=?
                """,
                (
                    int(checked_count),
                    json.dumps(found),
                    json.dumps(unverified),
                    time.time(),
                    1 if active else 0,
                    checkpoint_id,
                ),
            )


def latest_checkpoint():
    with DB_LOCK:
        with db_connect() as conn:
            row = conn.execute(
                """
                SELECT id, mode, config_json, checked_count, found_json,
                       unverified_json, started_at, updated_at
                FROM scan_checkpoints
                WHERE active=1
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "mode": row[1],
        "config": json.loads(row[2]),
        "checked_count": row[3],
        "found": json.loads(row[4]),
        "unverified": json.loads(row[5]),
        "started_at": row[6],
        "updated_at": row[7],
    }


def format_eta(seconds):
    if seconds is None or seconds < 0:
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def progress_line(checked, max_checks, found, unverified, scanner):
    speed = checked / scanner.elapsed()
    remaining = max(0, max_checks - checked)
    eta = remaining / speed if speed > 0 else None
    text = (
        f"\r  {checked:>6}/{max_checks:<6} "
        f"verified:{len(found):<4} maybe:{len(unverified):<4} "
        f"{speed:>5.1f}/s  ETA {format_eta(eta):<8} "
        f"workers:{scanner.workers:<2} "
        f"lat:{scanner.avg_latency():>5.0f}ms "
        f"cache:{scanner.cache_hits:<5}"
    )
    sys.stdout.write(text[:160])
    sys.stdout.flush()


def choose_lengths():
    raw = input("Lengths [4/5/6 or comma list, default 5]: ").strip()
    if not raw:
        return [5]
    lengths = []
    for token in raw.replace(" ", "").split(","):
        if token in {"4", "5", "6"}:
            value = int(token)
            if value not in lengths:
                lengths.append(value)
    return lengths or [5]


def choose_charset():
    print("Charset: [L] letters  [M] mixed (default)  [N] numbers")
    choice = input("Choose: ").strip().lower()
    if choice == "l":
        return "letters"
    if choice == "n":
        return "numbers"
    return "mixed"


def charset_from_name(name):
    return {
        "letters": base.LETTERS,
        "numbers": base.NUMBERS_ONLY,
        "mixed": base.CHARSET,
    }.get(name, base.CHARSET)


def make_candidate(config):
    length = random.choice(config["lengths"])
    return generate_ranked(
        length,
        charset_from_name(config["charset"]),
        aesthetic=bool(config.get("aesthetic", True)),
    )


def export_results(results, label):
    if not results:
        return []
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = os.path.join(base.SAVE_DIR, f"sniff_{label}_{stamp}")
    paths = []

    json_path = base_path + ".json"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    paths.append(json_path)

    csv_path = base_path + ".csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["name", "status", "verified", "score", "latency_ms", "cached"],
        )
        writer.writeheader()
        writer.writerows(results)
    paths.append(csv_path)

    txt_path = base_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as handle:
        for result in results:
            handle.write(
                f"{result['name']}\t{result['status']}\t"
                f"score={result['score']}\n"
            )
    paths.append(txt_path)
    return paths


def print_scan_summary(results, scanner):
    counts = Counter(r["status"] for r in results)
    verified = [r for r in results if r["status"] == "verified_available"]
    maybe = [r for r in results if r["status"] == "available_unverified"]
    print("\n\n" + "=" * 72)
    print("  v2.6 SCAN SUMMARY")
    print("=" * 72)
    print(f"  Checked:          {len(results)}")
    print(f"  Verified avail.:  {len(verified)}")
    print(f"  Unverified avail:{len(maybe):>5}")
    print(f"  Taken:            {counts.get('taken', 0)}")
    print(f"  Rate limited:     {counts.get('ratelimited', 0)}")
    print(f"  Cache hits:       {scanner.cache_hits}")
    print(f"  Network checks:   {scanner.network_checks}")
    print(f"  Avg API latency:  {scanner.avg_latency():.0f} ms")
    print(f"  Final workers:    {scanner.workers}")

    if verified:
        print("\n  BEST VERIFIED NAMES")
        for result in sorted(verified, key=lambda r: (-r["score"], r["name"]))[:25]:
            print(
                f"    {result['name']:<20} "
                f"score {result['score']:>3}/100  VERIFIED ✓"
            )
    if maybe:
        print("\n  NEEDS RECHECK")
        for result in sorted(maybe, key=lambda r: (-r["score"], r["name"]))[:10]:
            print(f"    {result['name']:<20} score {result['score']:>3}/100")


def run_scan(config, checkpoint=None):
    scanner = AdaptiveScanner()
    checked = int(checkpoint["checked_count"]) if checkpoint else 0
    found = list(checkpoint["found"]) if checkpoint else []
    unverified = list(checkpoint["unverified"]) if checkpoint else []
    checkpoint_id = checkpoint["id"] if checkpoint else create_checkpoint("scan", config)
    all_results = []
    seen = set(found) | set(unverified)

    print("\n  Adaptive scanner started.")
    print("  Only double-checked names count as verified available.")
    print("  Ctrl+C safely pauses this scan and saves a resume checkpoint.\n")

    try:
        while checked < config["max_checks"] and len(found) < config["target"]:
            batch_size = min(scanner.workers, config["max_checks"] - checked)
            names = []
            attempts = 0
            while len(names) < batch_size and attempts < batch_size * 30:
                attempts += 1
                candidate = make_candidate(config)
                if candidate not in seen and candidate not in names:
                    names.append(candidate)
            if not names:
                break

            results, cooldown = scanner.run_batch(names)
            for result in results:
                seen.add(result["name"])
                all_results.append(result)
                checked += 1
                if result["status"] == "verified_available":
                    if result["name"] not in found:
                        found.append(result["name"])
                elif result["status"] == "available_unverified":
                    if result["name"] not in unverified:
                        unverified.append(result["name"])
                progress_line(
                    checked,
                    config["max_checks"],
                    found,
                    unverified,
                    scanner,
                )
                if len(found) >= config["target"]:
                    break

            save_checkpoint(checkpoint_id, checked, found, unverified, active=True)

            if cooldown:
                print(
                    f"\n  Roblox throttled this batch. "
                    f"Workers reduced to {scanner.workers}; cooling down {cooldown}s."
                )
                time.sleep(cooldown)

        save_checkpoint(checkpoint_id, checked, found, unverified, active=False)
    except KeyboardInterrupt:
        save_checkpoint(checkpoint_id, checked, found, unverified, active=True)
        print("\n\n  Scan paused safely. Resume checkpoint saved.")
        return found, unverified, all_results, True

    print_scan_summary(all_results, scanner)
    if found:
        base.claim_available_name(found)
    save = input("\n  Export this session as TXT + CSV + JSON? [Y/n]: ").strip().lower()
    if save != "n":
        paths = export_results(all_results, "v26")
        for path in paths:
            print(f"  Saved: {path}")
    return found, unverified, all_results, False


def scan_mode(aesthetic_default=True):
    lengths = choose_lengths()
    target = max(1, int(input("How many VERIFIED available names to find? ") or "5"))
    max_checks = max(target, int(input("Max checks? ") or "500"))
    config = {
        "lengths": lengths,
        "target": target,
        "max_checks": max_checks,
        "charset": choose_charset(),
        "aesthetic": aesthetic_default,
    }
    run_scan(config)


def generate_batch_mode():
    lengths = choose_lengths()
    batch = max(1, int(input("How many names to check? ") or "100"))
    aesthetic = input("Rank toward cleaner/word-like names? [Y/n]: ").strip().lower() != "n"
    config = {
        "lengths": lengths,
        "target": batch,
        "max_checks": batch,
        "charset": choose_charset(),
        "aesthetic": aesthetic,
    }

    scanner = AdaptiveScanner()
    names = []
    seen = set()
    while len(names) < batch:
        candidate = make_candidate(config)
        if candidate not in seen:
            seen.add(candidate)
            names.append(candidate)

    results = []
    print("\n  Checking generated batch with adaptive concurrency...\n")
    index = 0
    while index < len(names):
        chunk = names[index : index + scanner.workers]
        batch_results, cooldown = scanner.run_batch(chunk)
        results.extend(batch_results)
        index += len(chunk)
        verified = [r for r in results if r["status"] == "verified_available"]
        maybe = [r for r in results if r["status"] == "available_unverified"]
        progress_line(len(results), batch, verified, maybe, scanner)
        if cooldown:
            print(
                f"\n  Rate limit response detected; workers -> {scanner.workers}, "
                f"cooldown {cooldown}s."
            )
            time.sleep(cooldown)

    print_scan_summary(results, scanner)
    available = [
        r["name"]
        for r in sorted(results, key=lambda r: (-r["score"], r["name"]))
        if r["status"] == "verified_available"
    ]
    if available:
        base.claim_available_name(available)
    if input("\n  Export TXT + CSV + JSON? [Y/n]: ").strip().lower() != "n":
        for path in export_results(results, "v26_batch"):
            print(f"  Saved: {path}")


def manual_mode():
    scanner = AdaptiveScanner()
    print("\n--- Verified Manual Lookup ---")
    print("Type one username at a time. Type 'done' to return.\n")
    results = []
    while True:
        name = input("  Username: ").strip().lower()
        if not name or name == "done":
            break
        if not base.re.match(r"^[a-zA-Z0-9_]{3,20}$", name):
            print("  Invalid Roblox username format.")
            continue
        result = scanner.check_one(name, use_cache=False)
        results.append(result)
        cache_note = " cache" if result.get("cached") else ""
        if result["status"] == "verified_available":
            print(
                f"  {name}: VERIFIED AVAILABLE ✓ "
                f"(score {result['score']}/100, {result['latency_ms']:.0f} ms{cache_note})"
            )
        elif result["status"] == "available_unverified":
            print(f"  {name}: POSSIBLY AVAILABLE ⚠ second verifier unavailable")
        else:
            print(f"  {name}: {result['status']} ({result['latency_ms']:.0f} ms{cache_note})")

    available = [r["name"] for r in results if r["status"] == "verified_available"]
    if available:
        base.claim_available_name(available)


def add_watch(username, priority):
    priority = max(1, min(3, int(priority)))
    with DB_LOCK:
        with db_connect() as conn:
            conn.execute(
                """
                INSERT INTO watchlist(username, priority, added_at)
                VALUES(?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET priority=excluded.priority
                """,
                (username.lower(), priority, time.time()),
            )


def remove_watch(username):
    with DB_LOCK:
        with db_connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE username=?", (username.lower(),))


def get_watchlist():
    with DB_LOCK:
        with db_connect() as conn:
            return conn.execute(
                """
                SELECT username, priority, added_at, last_status, last_checked
                FROM watchlist
                ORDER BY priority ASC, added_at ASC
                """
            ).fetchall()


def update_watch_result(username, status):
    with DB_LOCK:
        with db_connect() as conn:
            conn.execute(
                """
                UPDATE watchlist SET last_status=?, last_checked=?
                WHERE username=?
                """,
                (status, time.time(), username.lower()),
            )


def watchlist_mode():
    while True:
        rows = get_watchlist()
        print("\n--- Watchlist ---")
        if rows:
            for i, row in enumerate(rows, 1):
                username, priority, _, status, checked = row
                label = {1: "HIGH", 2: "NORMAL", 3: "LOW"}[priority]
                checked_text = (
                    datetime.fromtimestamp(checked).strftime("%Y-%m-%d %H:%M")
                    if checked
                    else "never"
                )
                print(
                    f"  [{i:>2}] [{label:<6}] {username:<20} "
                    f"{status or 'unknown':<20} {checked_text}"
                )
        else:
            print("  (empty)")

        action = input(
            "\n  [a] add  [c] check all  [r] remove  Enter back: "
        ).strip().lower()
        if not action:
            return
        if action == "a":
            username = input("  Username: ").strip().lower()
            if not base.re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
                print("  Invalid username.")
                continue
            p = input("  Priority [1 high / 2 normal / 3 low] (2): ").strip()
            add_watch(username, int(p) if p in {"1", "2", "3"} else 2)
            print("  Added.")
            continue
        if action == "r":
            username = input("  Username to remove: ").strip().lower()
            remove_watch(username)
            print("  Removed if present.")
            continue
        if action == "c":
            if not rows:
                print("  Watchlist is empty.")
                continue
            scanner = AdaptiveScanner(workers=4)
            names = [row[0] for row in rows]
            previous = {row[0]: row[3] for row in rows}
            print("\n  Checking watchlist...\n")
            index = 0
            while index < len(names):
                chunk = names[index : index + scanner.workers]
                results, cooldown = scanner.run_batch(chunk)
                index += len(chunk)
                for result in results:
                    old = previous.get(result["name"])
                    update_watch_result(result["name"], result["status"])
                    changed = old and old != result["status"]
                    marker = "  CHANGED!" if changed else ""
                    print(
                        f"  {result['name']:<20} -> {result['status']}{marker}"
                    )
                if cooldown:
                    time.sleep(cooldown)
            continue


def resume_mode():
    checkpoint = latest_checkpoint()
    if not checkpoint:
        print("\n  No interrupted scan checkpoint found.")
        return
    cfg = checkpoint["config"]
    print("\n  INTERRUPTED SCAN FOUND")
    print(f"  Checked: {checkpoint['checked_count']} / {cfg['max_checks']}")
    print(f"  Verified found: {len(checkpoint['found'])} / {cfg['target']}")
    print(f"  Lengths: {cfg['lengths']}  Charset: {cfg['charset']}")
    choice = input("  Resume it? [Y/n]: ").strip().lower()
    if choice != "n":
        run_scan(cfg, checkpoint=checkpoint)


def diagnostics_mode():
    print("\n--- Diagnostics ---")
    init_db()
    tests = []

    try:
        with db_connect() as conn:
            conn.execute("SELECT 1").fetchone()
        tests.append(("SQLite database", "OK", DB_PATH))
    except Exception as exc:
        tests.append(("SQLite database", "FAIL", str(exc)))

    if os.name == "nt":
        try:
            ctypes = __import__("ctypes")
            advapi32 = ctypes.WinDLL("Advapi32.dll")
            getattr(advapi32, "CredReadW")
            tests.append(("Credential Manager", "OK", "Win32 API available"))
        except Exception as exc:
            tests.append(("Credential Manager", "FAIL", str(exc)))
    else:
        tests.append(("Credential Manager", "N/A", "Windows only"))

    tests.append(
        (
            "Clipboard helper",
            "OK" if shutil.which("clip.exe") else "WARN",
            shutil.which("clip.exe") or "clip.exe not found",
        )
    )

    root = os.path.dirname(
        sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    )
    extension_manifest = os.path.join(root, "browser-extension", "manifest.json")
    tests.append(
        (
            "Browser companion",
            "OK" if os.path.exists(extension_manifest) else "WARN",
            extension_manifest,
        )
    )

    scanner = AdaptiveScanner(workers=3)
    started = time.perf_counter()
    result = scanner.check_one("roblox", use_cache=False)
    elapsed = (time.perf_counter() - started) * 1000
    api_ok = result["status"] in {
        "taken",
        "verified_available",
        "available_unverified",
        "inappropriate",
    }
    tests.append(
        (
            "Roblox username API",
            "OK" if api_ok else "WARN",
            f"{result['status']} in {elapsed:.0f} ms",
        )
    )

    for name, status, detail in tests:
        print(f"  {name:<22} {status:<5} {detail}")


def print_cache_stats():
    with DB_LOCK:
        with db_connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
            recent = conn.execute(
                "SELECT COUNT(*) FROM checks WHERE checked_at >= ?",
                (time.time() - CACHE_TTL_SECONDS,),
            ).fetchone()[0]
            watch = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
    print(
        f"  Local DB: {total} cached usernames "
        f"({recent} fresh), {watch} watchlist entries"
    )


def run_main():
    init_db()
    while True:
        print("\n" + "=" * 64)
        print(f"{base.APP_NAME} v{APP_VER}".center(64))
        print("Verified username scanning engine".center(64))
        print("=" * 64)
        print_cache_stats()
        checkpoint = latest_checkpoint()
        if checkpoint:
            print(
                f"  Resume available: {checkpoint['checked_count']}/"
                f"{checkpoint['config']['max_checks']} checked"
            )
        print(
            "\n  [s] smart scan     [g] generated batch   [a] aesthetic scan\n"
            "  [m] manual lookup  [w] watchlist         [r] resume scan\n"
            "  [c] credentials    [d] diagnostics       [l] legacy wordlist\n"
            "  [q] quit"
        )
        mode = input("\nMode: ").strip().lower()

        try:
            if mode == "s":
                scan_mode(aesthetic_default=False)
            elif mode == "g":
                generate_batch_mode()
            elif mode == "a":
                scan_mode(aesthetic_default=True)
            elif mode == "m":
                manual_mode()
            elif mode == "w":
                watchlist_mode()
            elif mode == "r":
                resume_mode()
            elif mode == "c":
                accounts.saved_accounts_mode()
            elif mode == "d":
                diagnostics_mode()
            elif mode == "l":
                base.wordlist_mode(base.pick_length())
            elif mode in {"q", "quit", "exit"}:
                return
            elif not mode:
                continue
            else:
                print("  Unknown mode.")
        except KeyboardInterrupt:
            print("\n  Operation cancelled. Returning to main menu.")


if __name__ == "__main__":
    run_main()
