import importlib
import os
import tempfile
import unittest


class V26EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        os.environ["LOCALAPPDATA"] = cls.tempdir.name
        cls.engine = importlib.import_module("v26_engine")
        cls.engine.init_db()

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def test_score_is_bounded(self):
        for name in ("norai", "aaaaa", "x4q7z", "12345"):
            score = self.engine.score_name(name)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_cache_round_trip(self):
        result = {
            "name": "cachetest",
            "status": "taken",
            "verified": False,
            "score": 42,
            "latency_ms": 123.0,
            "cached": False,
        }
        self.engine.cache_put(result)
        cached = self.engine.cache_get("cachetest")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status"], "taken")
        self.assertEqual(cached["score"], 42)
        self.assertTrue(cached["cached"])

    def test_checkpoint_round_trip(self):
        config = {
            "lengths": [4, 5],
            "target": 3,
            "max_checks": 100,
            "charset": "letters",
            "aesthetic": True,
        }
        checkpoint_id = self.engine.create_checkpoint("scan", config)
        self.engine.save_checkpoint(
            checkpoint_id,
            17,
            ["norai"],
            ["vekro"],
            active=True,
        )
        checkpoint = self.engine.latest_checkpoint()
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint["checked_count"], 17)
        self.assertEqual(checkpoint["found"], ["norai"])
        self.assertEqual(checkpoint["unverified"], ["vekro"])
        self.assertEqual(checkpoint["config"]["lengths"], [4, 5])
        self.engine.save_checkpoint(
            checkpoint_id,
            17,
            ["norai"],
            ["vekro"],
            active=False,
        )

    def test_watchlist_round_trip(self):
        self.engine.add_watch("watchtest", 1)
        rows = self.engine.get_watchlist()
        self.assertTrue(any(row[0] == "watchtest" and row[1] == 1 for row in rows))
        self.engine.update_watch_result("watchtest", "taken")
        rows = self.engine.get_watchlist()
        row = next(row for row in rows if row[0] == "watchtest")
        self.assertEqual(row[3], "taken")
        self.engine.remove_watch("watchtest")
        self.assertFalse(any(row[0] == "watchtest" for row in self.engine.get_watchlist()))


if __name__ == "__main__":
    unittest.main()
