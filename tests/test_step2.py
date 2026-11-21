"""
Unit tests for Step 2: Story Clustering & Measurable Signal Grounding.
Run: python3 -m unittest tests.test_step2
"""

import os
import random
import tempfile
import unittest
import datetime as dt

from core.clustering import ClusterEngine, StoryCluster, _publisher_authority
from core.scoring import ScoringEngine, extract_grounded_features, PRIMARY_DOMAINS
from core.models import SignalLevel
from core import auth, newsfeed
from core.demo_news import seed_demo
from core.recommender import CORPUS, Recommender


class TestClustering(unittest.TestCase):
    def test_publisher_authority_tiers(self):
        self.assertEqual(_publisher_authority("GitHub", "https://github.com/vllm-project/vllm"), 95)
        self.assertEqual(_publisher_authority("ArXiv", "https://arxiv.org/abs/2401.0001"), 100)
        self.assertEqual(_publisher_authority("Reuters", "https://reuters.com/tech/1"), 75)
        self.assertEqual(_publisher_authority("Random Blog", "https://blog.example.com/1"), 50)

    def test_cluster_matching_and_deduplication(self):
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        art1 = {
            "id": "art-1",
            "url": "https://techcrunch.com/2026/openai-pricing",
            "title": "OpenAI drops API inference pricing by 50 percent",
            "publisher": "TechCrunch",
            "published_at": now,
            "entities": ["OpenAI", "API", "GPT-4"],
            "topics": {"AI": 1.0, "Technology": 0.5},
            "keywords": {"pricing": 0.8, "openai": 0.9, "token": 0.7, "inference": 0.6},
            "kwset": {"pricing", "openai", "token", "inference"},
            "word_count": 400,
        }
        art2 = {
            "id": "art-2",
            "url": "https://openai.com/blog/price-reduction",
            "title": "OpenAI announces 50% price cut on API inference tokens",
            "publisher": "OpenAI Blog",
            "published_at": now,
            "entities": ["OpenAI", "API", "GPT-4"],
            "topics": {"AI": 1.0},
            "keywords": {"pricing": 0.85, "openai": 0.95, "token": 0.75, "cut": 0.5},
            "kwset": {"pricing", "openai", "token", "cut"},
            "word_count": 350,
        }
        art3 = {
            "id": "art-3",
            "url": "https://bbc.com/news/space-telescope",
            "title": "James Webb telescope discovers ancient galaxy cluster",
            "publisher": "BBC News",
            "published_at": now,
            "entities": ["James Webb", "NASA"],
            "topics": {"Space": 1.0, "Science": 0.8},
            "keywords": {"galaxy": 0.9, "telescope": 0.8, "ancient": 0.7},
            "kwset": {"galaxy", "telescope", "ancient"},
            "word_count": 500,
        }

        clusters = ClusterEngine.cluster_articles([art1, art2, art3])
        # art1 and art2 must cluster together; art3 forms its own cluster
        self.assertEqual(len(clusters), 2)
        clust_openai = next(c for c in clusters if "OpenAI" in c.lead_title or "OpenAI" in c.publishers)
        self.assertEqual(clust_openai.publisher_count, 2)
        self.assertIn("TechCrunch", clust_openai.publishers)
        self.assertIn("OpenAI Blog", clust_openai.publishers)
        # Authoritative domain (openai.com) should become the lead
        self.assertEqual(clust_openai.lead_publisher, "OpenAI Blog")
        self.assertGreater(clust_openai.corroboration_score, 0.5)

    def test_cluster_time_window_cutoff(self):
        t1 = "2026-11-01T10:00:00+00:00"
        t2 = "2026-11-10T10:00:00+00:00"  # 9 days later
        art1 = {
            "id": "art-old", "url": "https://tc.com/1", "title": "Postgres 18 adds async transactions",
            "publisher": "TC", "published_at": t1, "entities": ["PostgreSQL"],
            "keywords": {"postgres": 0.9, "transaction": 0.8}, "kwset": {"postgres", "transaction"}
        }
        art2 = {
            "id": "art-new", "url": "https://ars.com/2", "title": "Postgres 18 adds async transactions",
            "publisher": "Ars", "published_at": t2, "entities": ["PostgreSQL"],
            "keywords": {"postgres": 0.9, "transaction": 0.8}, "kwset": {"postgres", "transaction"}
        }
        clusters = ClusterEngine.cluster_articles([art1, art2], window_hours=48)
        # Should not cluster across 9 days
        self.assertEqual(len(clusters), 2)


class TestGroundedScoring(unittest.TestCase):
    def test_primary_domain_and_regex_detection(self):
        text = "The Linux Foundation and CNCF announced the creation of the Open Agent Protocol (OAP) v1.0 standard with $0.001 per-token pricing."
        url = "https://www.linuxfoundation.org/press/open-agent-protocol"
        features, penalties = extract_grounded_features(text, url=url, publisher="Linux Foundation", outlet_count=3)

        # Primary source domain authority check
        self.assertGreaterEqual(features["source_quality_corroboration"], 90.0)
        # Price and API change detection
        self.assertGreaterEqual(features["switching_or_lockin_cost"], 80.0)
        # Ecosystem match (linux, etc.)
        self.assertGreaterEqual(features["breadth_of_affected_users"], 65.0)
        # Penalties: no fluff
        self.assertFalse(penalties["press_release_language"])
        self.assertFalse(penalties["no_verifiable_facts"])

    def test_fluff_penalty(self):
        text = "We are thrilled to announce a game-changer paradigm shift that will seamlessly empower next-gen revolution."
        url = "https://random-startup.io/blog/launch"
        features, penalties = extract_grounded_features(text, url=url)
        self.assertTrue(penalties["press_release_language"])

        engine = ScoringEngine()
        score, level, reason, breakdown = engine.compute_score(features, penalties)
        self.assertTrue(any("Penalty [press_release_language]" in b for b in breakdown))

    def test_weight_tuning(self):
        engine = ScoringEngine()
        orig_wt = engine.weights["switching_or_lockin_cost"]
        # Positively reinforce switching cost
        engine.tune_weights({"switching_or_lockin_cost": 1.0, "time_sensitivity": -0.5})
        self.assertGreater(engine.weights["switching_or_lockin_cost"], orig_wt)
        # Sum of normalized weights must be ~1.0
        self.assertAlmostEqual(sum(engine.weights.values()), 1.0, places=2)


class TestRecommenderClusteringIntegration(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        newsfeed.init_schema(self.db)
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

    def test_cards_have_cluster_and_source_fields(self):
        uid = auth.create_user("cluster_user", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Technology", "Business", "AI"])
        items = self.rec.rank(uid, limit=10, rng=random.Random(42))
        self.assertGreater(len(items), 0)
        first = items[0]
        self.assertIn("source_count", first)
        self.assertIn("sources", first)
        self.assertIn("cluster_id", first)
        self.assertIn("corroboration_score", first)
        self.assertIsInstance(first["sources"], list)
        self.assertGreaterEqual(first["source_count"], 1)

    def test_cluster_deduplication_prevents_duplicate_events(self):
        uid = auth.create_user("dedupe_user", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Technology", "AI"])
        items = self.rec.rank(uid, limit=20, rng=random.Random(42))
        cluster_ids = [it["cluster_id"] for it in items if it.get("cluster_id")]
        # Every card in the feed must belong to a distinct cluster (no duplicate coverage leaks)
        self.assertEqual(len(cluster_ids), len(set(cluster_ids)))


if __name__ == "__main__":
    unittest.main()
