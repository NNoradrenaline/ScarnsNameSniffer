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
