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
