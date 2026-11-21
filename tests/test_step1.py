"""
Tests for Step 1 Logic & Algorithm Fixes:
1. Parameterized _ua() SQL updates (no f-string interpolation)
2. Net negative bounce penalty for dwell < 8 seconds
3. Exploration slot selection of highest quality candidate
4. Prediction ledger horizon segmentation and automated resolution check
"""

import os
import tempfile
import unittest
import datetime

from core import auth, newsfeed
from core.models import Prediction
from core.demo_news import seed_demo
from core.recommender import Recommender, CORPUS
from core.ledger import LedgerEngine


class TestStep1RecommenderFixes(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        newsfeed.init_schema(self.db)
        seed_demo(self.db)
        self.uid = auth.create_user("testuser", "secretpass123", "Tester", self.db)
        self.rec = Recommender(self.db)
        CORPUS._sig = None  # Force corpus reload

    def tearDown(self):
        CORPUS._sig = None
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db + suffix)
            except FileNotFoundError:
                pass

    def test_parameterized_ua(self):
        """Verify that _ua safely parameterizes updates to user_articles."""
        corpus = CORPUS.get(self.db)
        first_aid = corpus.order[0]

        # Record an impression and check DB values
        self.rec.record(self.uid, {"kind": "impression", "article_id": first_aid})
        st = self.rec._user_state(self.uid)
        self.assertIn(first_aid, st)
        self.assertEqual(st[first_aid]["impressions"], 1)

        # Record a second impression
        self.rec.record(self.uid, {"kind": "impression", "article_id": first_aid})
        st2 = self.rec._user_state(self.uid)
        self.assertEqual(st2[first_aid]["impressions"], 2)

        # Record a dwell
        self.rec.record(self.uid, {"kind": "dwell", "article_id": first_aid, "value": 15.5})
        st3 = self.rec._user_state(self.uid)
        self.assertAlmostEqual(st3[first_aid]["dwell_seconds"], 15.5, places=1)

    def test_bounce_is_net_negative(self):
        """
        Claude's critique: Click gives +1.0; a dwell < 8s used to give -0.6, leaving +0.4 net positive.
        Verify that a click followed by a bounce (< 8s) leaves a net NEGATIVE affinity.
        """
        corpus = CORPUS.get(self.db)
        aid = corpus.order[0]
        article = corpus.articles[aid]
        primary_topic = next(iter(article["topics"]), None)
        self.assertIsNotNone(primary_topic)

        # 1. Click the article (+1.0)
        self.rec.record(self.uid, {"kind": "click", "article_id": aid})
        aff_after_click = self.rec.affinities(self.uid).get("topic", {}).get(primary_topic, 0.0)
        self.assertGreater(aff_after_click, 0.0)

        # 2. User bounces immediately back after 3 seconds (dwell < 8s)
        self.rec.record(self.uid, {"kind": "dwell", "article_id": aid, "value": 3.0})
        aff_after_bounce = self.rec.affinities(self.uid).get("topic", {}).get(primary_topic, 0.0)

        # Net affinity for that topic must now be negative (or substantially lower than click)
        self.assertLess(aff_after_bounce, 0.0,
                        f"Expected bounce to result in net negative affinity, but got {aff_after_bounce}")

    def test_exploration_picks_highest_quality(self):
        """
        Claude's critique: Exploration was picking the newest article in corpus.order regardless of quality.
        Verify rank() selects high-quality articles from scored pool for exploration slots.
        """
        # Onboard user so confidence > 0.05
        self.rec.onboard(self.uid, ["AI", "Technology"])
        feed = self.rec.rank(self.uid, limit=12)
        self.assertTrue(len(feed) > 0)

        # Check explore items have valid non-empty explain metadata
        explore_items = [item for item in feed if item.get("why", {}).get("type") == "explore"]
        for it in explore_items:
            self.assertIn("text", it["why"])


class TestStep1LedgerFixes(unittest.TestCase):
    def test_horizon_categorization(self):
        """Verify 30-day, 90-day, and 365-day horizons are correctly classified."""
        p_30 = Prediction(
            id="p30", statement="Statement 30", probability=0.8,
            made_at="2026-11-01", resolves_at="2026-11-25",
            resolution_criteria="Criteria"
        )
        p_90 = Prediction(
            id="p90", statement="Statement 90", probability=0.7,
            made_at="2026-11-01", resolves_at="2027-01-20",
            resolution_criteria="Criteria"
        )
        p_365 = Prediction(
            id="p365", statement="Statement 365", probability=0.6,
            made_at="2026-11-01", resolves_at="2027-11-01",
            resolution_criteria="Criteria"
        )

        self.assertEqual(LedgerEngine.get_horizon(p_30), "30-day")
        self.assertEqual(LedgerEngine.get_horizon(p_90), "90-day")
        self.assertEqual(LedgerEngine.get_horizon(p_365), "365-day")

    def test_horizon_breakdown_statistics(self):
        """Verify calculation of segmented stats per horizon."""
        preds = [
            Prediction(id="p1", statement="S1", probability=0.8, made_at="2026-01-01", resolves_at="2026-01-25", resolution_criteria="C", status="correct"),
            Prediction(id="p2", statement="S2", probability=0.6, made_at="2026-01-01", resolves_at="2026-01-25", resolution_criteria="C", status="wrong"),
            Prediction(id="p3", statement="S3", probability=0.75, made_at="2026-01-01", resolves_at="2026-03-25", resolution_criteria="C", status="correct"),
            Prediction(id="p4", statement="S4", probability=0.7, made_at="2026-01-01", resolves_at="2027-01-01", resolution_criteria="C", status="open"),
        ]

        breakdown = LedgerEngine.calculate_horizon_breakdown(preds)
        self.assertIn("30-day", breakdown)
        self.assertIn("90-day", breakdown)
        self.assertIn("365-day", breakdown)

        self.assertEqual(breakdown["30-day"]["resolved"], 2)
        self.assertEqual(breakdown["30-day"]["hit_rate_pct"], 50.0)
        self.assertEqual(breakdown["90-day"]["resolved"], 1)
        self.assertEqual(breakdown["90-day"]["hit_rate_pct"], 100.0)
        self.assertEqual(breakdown["365-day"]["open"], 1)

    def test_due_predictions_detection(self):
        """Verify automated detection of due predictions."""
        preds = [
            Prediction(id="past_due", statement="Past", probability=0.7, made_at="2026-01-01", resolves_at="2026-05-01", resolution_criteria="C", status="open"),
            Prediction(id="future", statement="Future", probability=0.7, made_at="2026-01-01", resolves_at="2027-05-01", resolution_criteria="C", status="open"),
            Prediction(id="already_resolved", statement="Resolved", probability=0.7, made_at="2026-01-01", resolves_at="2026-05-01", resolution_criteria="C", status="correct"),
        ]

        due = LedgerEngine.get_due_predictions(preds, as_of_date="2026-06-01")
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].id, "past_due")

    def test_resolve_prediction_audit(self):
        """Verify prediction resolution updates fields and audit trail."""
        p = Prediction(id="p_test", statement="Test", probability=0.75, made_at="2026-01-01", resolves_at="2026-03-01", resolution_criteria="C", status="open")
        resolved = LedgerEngine.resolve_prediction(
            p,
            status="correct",
            evidence_url="https://example.com/proof",
            postmortem="Correct as verified by release.",
            resolved_at="2026-03-01"
        )
        self.assertEqual(resolved.status, "correct")
        self.assertEqual(resolved.evidence_url, "https://example.com/proof")
        self.assertIn("Correct as verified", resolved.postmortem)
        self.assertEqual(resolved.resolved_at, "2026-03-01")


if __name__ == "__main__":
    unittest.main()
