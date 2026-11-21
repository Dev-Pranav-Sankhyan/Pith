"""
Step 4: honest Ledger, append-only resolutions, schema migrations, reader votes,
public routing and rate limits.
Run: python3 -m unittest tests.test_step4
"""

import datetime as dt
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import unittest

from core.db import Database
from core.ledger import LedgerEngine
from core.models import Prediction
from core.ratelimit import RateLimiter
from core import votes, auth
from core.newsfeed import init_schema


def _pred(pid, status="open", prob=0.7, made="2026-01-01", resolves="2026-02-01", provenance="live"):
    return Prediction(
        id=pid, statement=f"Statement {pid}", probability=prob, made_at=made, resolves_at=resolves,
        resolution_criteria="Official docs say so.", status=status, provenance=provenance,
        evidence_url="https://example.com/e" if status != "open" else None,
    )


class TempBriefDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "brief.sqlite3")
        self.db = Database(self.path)

    def tearDown(self):
        self.tmp.cleanup()


class TestMigrations(TempBriefDB):
    def test_fresh_db_is_at_latest_version(self):
        self.assertEqual(self.db.schema_version(), len(Database.MIGRATIONS))

    def test_reopening_is_idempotent(self):
        Database(self.path)
        Database(self.path)
        self.assertEqual(self.db.schema_version(), len(Database.MIGRATIONS))

    def test_legacy_seed_rows_become_illustrative(self):
        # Simulate a pre-migration DB holding hand-seeded history.
        legacy = os.path.join(self.tmp.name, "legacy.sqlite3")
        conn = sqlite3.connect(legacy)
        conn.executescript("""
            CREATE TABLE predictions (id TEXT PRIMARY KEY, card_id TEXT, statement TEXT NOT NULL,
              probability REAL NOT NULL, made_at TEXT NOT NULL, resolves_at TEXT NOT NULL,
              resolution_criteria TEXT NOT NULL, category TEXT DEFAULT 'technology',
              status TEXT DEFAULT 'open', resolved_at TEXT, evidence_url TEXT, postmortem TEXT);
            INSERT INTO predictions (id, statement, probability, made_at, resolves_at, resolution_criteria, status)
              VALUES ('hist-pred-01', 's', 0.8, '2026-01-01', '2026-02-01', 'c', 'correct'),
                     ('pred-live', 's', 0.6, '2026-11-20', '2027-02-01', 'c', 'open');
        """)
        conn.commit()
        conn.close()
        db = Database(legacy)
        prov = {p.id: p.provenance for p in db.get_all_predictions()}
        self.assertEqual(prov, {"hist-pred-01": "illustrative", "pred-live": "live"})


class TestHonestLedger(unittest.TestCase):
    def test_illustrative_predictions_never_count(self):
        preds = [
            _pred("i1", "correct", provenance="illustrative"),
            _pred("i2", "correct", provenance="illustrative"),
            _pred("l1", "open"),
        ]
        stats = LedgerEngine.calculate_statistics(preds)
        self.assertEqual(stats["resolved_count"], 0)
        self.assertIsNone(stats["brier_score"])
        self.assertIsNone(stats["hit_rate_pct"])
        self.assertEqual(stats["open_count"], 1)
        self.assertEqual(stats["illustrative"]["count"], 2)

    def test_brier_skill_score(self):
        # Perfectly confident and right on a mixed record -> positive skill.
        preds = [_pred("a", "correct", 0.9), _pred("b", "wrong", 0.1 + 1e-9), _pred("c", "correct", 0.9)]
        preds[1].probability = 0.1
        stats = LedgerEngine.calculate_statistics(preds)
        self.assertGreater(stats["brier_skill_score"], 0)


class TestResolutions(TempBriefDB):
    def setUp(self):
        super().setUp()
        self.db.save_prediction(_pred("p1", made="2026-01-01"))

    def test_requires_named_reviewer_and_evidence(self):
        with self.assertRaises(ValueError):
            self.db.record_resolution("p1", "correct", "https://e", None, resolved_by="")
        with self.assertRaises(ValueError):
            self.db.record_resolution("p1", "correct", None, None, resolved_by="Ana")
        with self.assertRaises(KeyError):
            self.db.record_resolution("nope", "void", None, None, resolved_by="Ana")

    def test_resolution_updates_prediction_and_logs(self):
        self.db.record_resolution("p1", "wrong", "https://e/1", "Missed it", resolved_by="Ana")
        p = {x.id: x for x in self.db.get_all_predictions()}["p1"]
        self.assertEqual((p.status, p.resolved_by), ("wrong", "Ana"))
        self.assertEqual(len(self.db.get_resolution_history("p1")), 1)

    def test_correction_supersedes_without_erasing(self):
        first = self.db.record_resolution("p1", "wrong", "https://e/1", None, resolved_by="Ana")
        self.db.record_resolution("p1", "correct", "https://e/2", "Re-read the docs", resolved_by="Ben")
        hist = self.db.get_resolution_history("p1")
        self.assertEqual([h["status"] for h in hist], ["wrong", "correct"])
        self.assertEqual(hist[1]["supersedes_id"], first)

    def test_log_is_append_only(self):
        self.db.record_resolution("p1", "void", None, None, resolved_by="Ana")
        with self.db.get_connection() as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE prediction_resolutions SET status = 'correct'")
        with self.db.get_connection() as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM prediction_resolutions")


class TestForecastImmutability(TempBriefDB):
    def test_past_forecast_cannot_be_edited(self):
        self.db.save_prediction(_pred("old", prob=0.7, made="2026-01-01"))
        # Re-saving with a new probability is silently ignored...
        self.db.save_prediction(_pred("old", prob=0.95, made="2026-01-01"))
        self.assertEqual({p.id: p for p in self.db.get_all_predictions()}["old"].probability, 0.7)
        # ...and a direct UPDATE is rejected by the trigger.
        with self.db.get_connection() as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE predictions SET probability = 0.99 WHERE id = 'old'")

    def test_same_day_redraft_is_allowed(self):
        today = dt.date.today().isoformat()
        self.db.save_prediction(_pred("new", prob=0.6, made=today, resolves="2027-01-01"))
        self.db.save_prediction(_pred("new", prob=0.65, made=today, resolves="2027-01-01"))
        self.assertEqual({p.id: p for p in self.db.get_all_predictions()}["new"].probability, 0.65)

    def test_resave_never_reopens_a_resolved_prediction(self):
        self.db.save_prediction(_pred("r", made="2026-01-01"))
        self.db.record_resolution("r", "correct", "https://e", None, resolved_by="Ana")
        self.db.save_prediction(_pred("r", made="2026-01-01"))  # status="open" in the object
        self.assertEqual({p.id: p for p in self.db.get_all_predictions()}["r"].status, "correct")


class TestLedgerRender(unittest.TestCase):
    def test_render_with_no_live_resolutions(self):
        from pipeline.render_html import render_ledger
        preds = [_pred("i1", "correct", provenance="illustrative"), _pred("l1")]
        stats = LedgerEngine.calculate_statistics(preds)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "ledger.html")
            render_ledger(preds, stats, out)
            html = open(out, encoding="utf-8").read()
        self.assertIn("No live forecast has resolved yet", html)
        self.assertIn("Illustrative", html)
        self.assertNotIn("European Union AI Act", html)  # the old hard-coded "wrong call"


class TestVotesAndRateLimit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "fy.sqlite3")
        init_schema(self.db)
        self.u1 = auth.create_user("voter1", "password123", "", self.db)
        self.u2 = auth.create_user("voter2", "password123", "", self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_current_vote_per_reader(self):
        votes.cast_vote(self.u1, "card-x", "agree", self.db)
        votes.cast_vote(self.u1, "card-x", "lower", self.db)
        votes.cast_vote(self.u2, "card-x", "lower", self.db)
        self.assertEqual(votes.counts("card-x", self.db), {"higher": 0, "agree": 0, "lower": 2})

    def test_invalid_vote_rejected(self):
        with self.assertRaises(ValueError):
            votes.cast_vote(self.u1, "card-x", "maybe", self.db)

    def test_rate_limiter_window(self):
        rl = RateLimiter(max_hits=2, window_seconds=10)
        self.assertTrue(rl.allow("ip", now=0))
        self.assertTrue(rl.allow("ip", now=1))
        self.assertFalse(rl.allow("ip", now=2))
        self.assertTrue(rl.allow("other", now=2))
        self.assertTrue(rl.allow("ip", now=12))


class TestPublicRouting(unittest.TestCase):
    """Boots the real handler on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.httpd = server.ThreadingServer(("127.0.0.1", 0), server.BriefHTTPRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, r.getheader("Location"), body

    def test_brief_and_ledger_are_public(self):
        for path in ("/", "/ledger", "/archive", "/patterns", "/about"):
            status, _, _ = self._get(path)
            self.assertEqual(status, 200, path)

    def test_for_you_requires_login(self):
        status, loc, _ = self._get("/foryou")
        self.assertEqual(status, 302)
        self.assertIn("about.html", loc)

    def test_no_directory_listing(self):
        status, _, _ = self._get("/audio/")
        self.assertEqual(status, 404)

    def test_healthz_and_votes(self):
        status, _, body = self._get("/healthz")
        self.assertEqual((status, json.loads(body)["ok"]), (200, True))
        status, _, body = self._get("/api/votes?card_id=card-none")
        self.assertEqual(status, 200)
        self.assertEqual(sum(json.loads(body)["counts"].values()), 0)


if __name__ == "__main__":
    unittest.main()
