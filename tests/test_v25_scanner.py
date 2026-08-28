import time

import v25_engine as eng
import v25_scanner as scanner


class CacheOnlyStore:
    def __init__(self, status="taken"):
        self.status = status

    def cached_status(self, name):
        return self.status

    def record(self, *args, **kwargs):
        raise AssertionError("network/cache-only test should not record")


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
    out = scanner.generate_unique(
        2,
        lambda: next(values),
        cfg,
        ["bad"],
        set(),
    )
    assert out == ["sorin", "melix"]


def test_checkpoint_payload_preserves_resume_statistics():
    stats = eng.ScanStats(time.time() - 5)
    stats.checked = 20
    stats.network_checks = 12
    stats.cache_hits = 8
    stats.available = 2
    stats.taken = 16
    stats.inappropriate = 1
    stats.other = 1
    cfg = eng.FilterConfig(allow_digits=False)

    payload = scanner.checkpoint_payload(
        "scan", 5, 10, 500, ["sorin", "melix"], stats, cfg, "l", False
    )

    assert payload["checked"] == 20
    assert payload["network_checks"] == 12
    assert payload["cache_hits"] == 8
    assert payload["available"] == 2
    assert payload["taken"] == 16
    assert payload["found"] == ["sorin", "melix"]
    assert payload["filters"]["allow_digits"] is False
    assert payload["elapsed"] >= 5


def test_check_candidates_uses_valid_cache_without_network(monkeypatch):
    def fail_network(name):
        raise AssertionError(f"network called for cached username {name}")

    monkeypatch.setattr(scanner.base, "smart_check", fail_network)

    stats = eng.ScanStats(time.time())
    adaptive = eng.AdaptiveWorkers(workers=12)
    found = []

    rows = scanner.check_candidates(
        ["sorin", "melix"],
        CacheOnlyStore("taken"),
        stats,
        adaptive,
        "test",
        target=2,
        found=found,
    )

    assert len(rows) == 2
    assert all(row["status"] == "taken" for row in rows)
    assert stats.checked == 2
    assert stats.cache_hits == 2
    assert stats.network_checks == 0
    assert found == []
