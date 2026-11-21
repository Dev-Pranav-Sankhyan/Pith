"""
Unit tests for Step 3: Unification of 'Your 5' (Daily News + For You),
Role Inference, Satisfaction Signal ('Worth my time?'), and Offline Evaluation.
Run: python3 -m unittest tests.test_step3
"""

import os
import random
import tempfile
import unittest
import datetime as dt

from core.your5 import infer_role, Your5Engine
from core.eval_personalization import evaluate_personalization, ndcg_at_k
from core.newsfeed import init_schema
from core.demo_news import seed_demo
from core.recommender import CORPUS, Recommender
from core import auth
from core.db import Database


class TestRoleInference(unittest.TestCase):
    def test_infer_developer_role(self):
        aff = {
            "topic": {"Technology": 6.5, "AI": 5.0},
            "keyword": {"code": 4.0, "api": 5.2, "latency": 3.8, "cuda": 4.5, "vllm": 3.0},
            "entity": {"GitHub": 3.5, "PyTorch": 4.0}
        }
        role, conf, reason = infer_role(aff)
        self.assertEqual(role, "developer")
        self.assertGreater(conf, 0.7)
        self.assertIn("code", reason.lower())

    def test_infer_founder_role(self):
        aff = {
            "topic": {"Business": 8.0, "Technology": 3.0},
            "keyword": {"startup": 5.0, "pricing": 6.0, "saas": 4.5, "growth": 4.0, "margin": 3.5},
            "entity": {"Stripe": 3.0}
        }
        role, conf, reason = infer_role(aff)
        self.assertEqual(role, "founder")
        self.assertGreater(conf, 0.7)
        self.assertIn("startup", reason.lower())

    def test_infer_investor_role(self):
        aff = {
            "topic": {"Markets": 9.0, "Business": 4.0},
            "keyword": {"valuation": 6.0, "ipo": 5.0, "venture": 4.5, "funding": 5.5, "shares": 4.0},
            "entity": {"Sequoia": 3.0}
        }
        role, conf, reason = infer_role(aff)
        self.assertEqual(role, "investor")
        self.assertGreater(conf, 0.7)
        self.assertIn("venture", reason.lower())

    def test_infer_everyday_role(self):
        aff = {
            "topic": {"Science": 7.0, "Space": 6.0, "Health": 5.0},
            "keyword": {"telescope": 5.0, "discovery": 4.0, "planet": 4.5},
            "entity": {"NASA": 4.0}
        }
        role, conf, reason = infer_role(aff)
        self.assertEqual(role, "everyday")
        self.assertGreater(conf, 0.6)


class TestYour5Engine(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        init_schema(self.db)
        seed_demo(self.db)
        CORPUS._sig = None
        self.engine = Your5Engine(brief_db_path="brief.sqlite3", foryou_db_path=self.db)

    def tearDown(self):
        CORPUS._sig = None
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db + suffix)
            except FileNotFoundError:
                pass

    def test_anonymous_your5(self):
        res = self.engine.get_your_5(user_id=None)
        self.assertEqual(len(res["cards"]), 5)
        self.assertEqual(res["inferred_role"], "developer")
        first = res["cards"][0]
        self.assertIn("headline", first)
        self.assertIn("what_happened", first)
        self.assertIn("role_view", first)
        self.assertIn("prediction", first)
        self.assertIn("action_type", first)
        self.assertGreater(len(res["not_included_today"]), 0)

    def test_personalized_your5_for_user(self):
        uid = auth.create_user("founder_user", "password123", db_path=self.db)
        # Learn founder affinities
        self.engine.rec.onboard(uid, ["Business", "Technology"])
        a = list(CORPUS.get(self.db).articles.values())[0]
        self.engine.rec.record(uid, {"kind": "click", "article_id": a["id"]})
        self.engine.rec.record(uid, {"kind": "worth_time", "article_id": a["id"]})

        res = self.engine.get_your_5(user_id=uid)
        self.assertEqual(len(res["cards"]), 5)
        self.assertIsNotNone(res["weekly_digest"])
        self.assertIn("reads", res["weekly_digest"])
        self.assertEqual(res["weekly_digest"]["reads"], 1)

    def test_worth_my_time_signal_boosting(self):
        uid = auth.create_user("sat_user", "password123", db_path=self.db)
        a = list(CORPUS.get(self.db).articles.values())[0]
        top_topic = next(iter(a["topics"]))

        # Record worth_time
        self.engine.rec.record(uid, {"kind": "worth_time", "article_id": a["id"]})
        aff = self.engine.rec.affinities(uid)
        # High satisfaction signal must significantly boost topic affinity (weight >= 3.0)
        self.assertGreaterEqual(aff["topic"].get(top_topic, 0.0), 3.0)


class TestOfflinePersonalizationEvaluator(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        init_schema(self.db)
        seed_demo(self.db)
        CORPUS._sig = None
        self.rec = Recommender(self.db)

    def tearDown(self):
        CORPUS._sig = None
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db + suffix)
            except FileNotFoundError:
                pass

    def test_ndcg_at_k(self):
        self.assertAlmostEqual(ndcg_at_k([1, 0, 0], 3), 1.0)
        self.assertAlmostEqual(ndcg_at_k([0, 1, 0], 3), 0.6309, places=3)
        self.assertEqual(ndcg_at_k([0, 0, 0], 3), 0.0)

    def test_offline_eval_with_seeded_interactions(self):
        # Create a user with 10 interactions on sports
        uid = auth.create_user("eval_sports_fan", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Sports"])
        corpus = CORPUS.get(self.db)
        sports_arts = [a for a in corpus.articles.values() if "Sports" in a["topics"]]

        for art in sports_arts:
            self.rec.record(uid, {"kind": "click", "article_id": art["id"]})
            self.rec.record(uid, {"kind": "worth_time", "article_id": art["id"]})

        results = evaluate_personalization(self.db, min_events=5)
        self.assertEqual(results["users_evaluated"], 1)
        # Personalized Hit Rate should be positive
        self.assertGreaterEqual(results["metrics"]["personalized"]["hr_at_10"], 0.5)


if __name__ == "__main__":
    unittest.main()
