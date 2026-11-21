"""
Step 5: outcome-based weight tuning, clustering quality, verdict drafts,
Anthropic provider request shape, email edition, retention.
Run: python3 -m unittest tests.test_step5
"""

import datetime as dt
import json
import os
import tempfile
import unittest
from unittest import mock

from core.cluster_eval import evaluate, featurize_articles
from core.clustering import ClusterEngine
from core.db import Database
from core.models import Prediction
from core.scoring import DEFAULT_WEIGHTS, ScoringEngine, load_weights, outcome_correlations


class TestOutcomeTuning(unittest.TestCase):
    def _rows(self, n):
        # irreversibility predicts outcomes; the other factors are flat.
        rows = []
        for i in range(n):
            hit = i % 2 == 0
            f = {k: 60.0 for k in DEFAULT_WEIGHTS}
            f["irreversibility"] = 85.0 if hit else 40.0
            rows.append({"outcome": 1.0 if hit else 0.0, "factors": f})
        return rows

    def test_no_tuning_below_minimum_sample(self):
        self.assertEqual(outcome_correlations(self._rows(19)), {})

    def test_predictive_factor_gains_weight(self):
        corr = outcome_correlations(self._rows(24))
        self.assertGreater(corr["irreversibility"], 0.9)
        engine = ScoringEngine(weights=dict(DEFAULT_WEIGHTS))
        engine.tune_weights(corr)
        self.assertGreater(engine.weights["irreversibility"], DEFAULT_WEIGHTS["irreversibility"])
        self.assertAlmostEqual(sum(engine.weights.values()), 1.0, places=2)

    def test_invalid_weights_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.json")
            json.dump({"weights": {"irreversibility": 1.0}}, open(path, "w"))
            self.assertEqual(load_weights(path), DEFAULT_WEIGHTS)
            self.assertEqual(load_weights(os.path.join(d, "missing.json")), DEFAULT_WEIGHTS)

    def test_factor_scores_round_trip_through_db(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(os.path.join(d, "b.sqlite3"))
            self.assertEqual(db.schema_version(), len(Database.MIGRATIONS))
            from pipeline.ingest_seed import generate_seed_issue
            issue = generate_seed_issue()
            issue.cards[0].factor_scores = {"irreversibility": 77.0}
            db.save_issue(issue)
            card = {c.id: c for c in db.get_latest_issue().cards}[issue.cards[0].id]
            self.assertEqual(card.factor_scores, {"irreversibility": 77.0})


class TestClustering(unittest.TestCase):
    def test_gold_set_quality(self):
        scores = evaluate("tests/fixtures/cluster_gold.json")
        self.assertGreaterEqual(scores["precision"], 0.95)  # never merge different stories
        self.assertGreaterEqual(scores["recall"], 0.75)     # was 0.27 before the rewrite

    def test_shared_big_company_name_does_not_merge(self):
        items = [
            {"id": "x", "title": "OpenAI cuts API prices for cached prompts", "summary": "Prompt caching is cheaper.",
             "published_at": "2026-11-18T09:00:00Z"},
            {"id": "y", "title": "OpenAI names two new board members", "summary": "Governance changes at the board.",
             "published_at": "2026-11-18T10:00:00Z"},
        ]
        clusters = ClusterEngine.cluster_articles(featurize_articles(items))
        self.assertEqual(len(clusters), 2)

    def test_outside_time_window_never_merges(self):
        items = [
            {"id": "x", "title": "Kubernetes 1.35 released with in-place pod resize", "summary": "",
             "published_at": "2026-11-01T09:00:00Z"},
            {"id": "y", "title": "Kubernetes 1.35 released with in-place pod resize", "summary": "",
             "published_at": "2026-11-10T09:00:00Z"},
        ]
        self.assertEqual(len(ClusterEngine.cluster_articles(featurize_articles(items))), 2)


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, system_prompt, user_prompt, json_mode=True):
        return self.reply


class TestVerdictDraft(unittest.TestCase):
    PRED = Prediction(id="p", statement="X ships by June", probability=0.7, made_at="2026-01-01",
                      resolves_at="2026-06-30", resolution_criteria="Official release notes.")
    PAGE = "Release notes. Version 2.0 of X shipped on 3 June 2026 to all users."

    def test_verified_quote_keeps_verdict(self):
        from pipeline.resolve_predictions import draft_verdict
        llm = FakeLLM(json.dumps({"verdict": "correct", "quote": "Version 2.0 of X shipped on 3 June 2026", "reasoning": "r"}))
        d = draft_verdict(self.PRED, self.PAGE, llm)
        self.assertEqual((d["verdict"], d["quote_verified"]), ("correct", True))

    def test_invented_quote_is_downgraded(self):
        from pipeline.resolve_predictions import draft_verdict
        llm = FakeLLM(json.dumps({"verdict": "correct", "quote": "X shipped in May", "reasoning": "r"}))
        d = draft_verdict(self.PRED, self.PAGE, llm)
        self.assertEqual(d["verdict"], "insufficient")

    def test_garbage_reply_is_insufficient(self):
        from pipeline.resolve_predictions import draft_verdict
        self.assertEqual(draft_verdict(self.PRED, self.PAGE, FakeLLM("not json"))["verdict"], "insufficient")


class TestAnthropicProvider(unittest.TestCase):
    def _call(self, response):
        from core.llm import AnthropicProvider, ANTHROPIC_DEFAULT_MODEL
        sent = {}

        class Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                return json.dumps(response).encode()

        def fake_urlopen(req, timeout=None):
            sent["body"] = json.loads(req.data)
            sent["headers"] = dict(req.header_items())
            return Resp()

        with mock.patch("core.llm.urllib.request.urlopen", fake_urlopen):
            out = AnthropicProvider(api_key="test").complete("sys", "user")
        return out, sent, ANTHROPIC_DEFAULT_MODEL

    def test_request_shape_and_text_extraction(self):
        out, sent, model = self._call({
            "stop_reason": "end_turn",
            "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "{\"ok\": 1}"}],
        })
        self.assertEqual(out, "{\"ok\": 1}")  # skips the leading thinking block
        self.assertEqual(sent["body"]["model"], model)
        self.assertNotIn("temperature", sent["body"])  # rejected by current models
        self.assertEqual(sent["body"]["fallbacks"], "default")

    def test_refusal_raises(self):
        with self.assertRaises(RuntimeError):
            self._call({"stop_reason": "refusal", "stop_details": {"category": "cyber"}, "content": []})


class TestEmailEdition(unittest.TestCase):
    def test_renders_issue_and_honest_record(self):
        from pipeline.email_edition import build_email_edition
        from pipeline.ingest_seed import generate_seed_issue
        with tempfile.TemporaryDirectory() as d:
            dbp = os.path.join(d, "b.sqlite3")
            issue = generate_seed_issue()
            Database(dbp).save_issue(issue)
            path = build_email_edition(dbp, d)
            html = open(path, encoding="utf-8").read()
            text = open(os.path.join(d, "email", "latest.txt"), encoding="utf-8").read()
        self.assertIn(issue.cards[0].headline.split(",")[0], html)
        self.assertIn("none resolved yet", text)
        self.assertNotIn("<script", html)


class TestRetention(unittest.TestCase):
    def test_old_events_and_expired_sessions_pruned(self):
        from core import auth
        from core.newsfeed import connect, init_schema, prune_old
        with tempfile.TemporaryDirectory() as d:
            dbp = os.path.join(d, "fy.sqlite3")
            init_schema(dbp)
            uid = auth.create_user("keeper", "password123", "", dbp)
            old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=400)).isoformat(timespec="seconds")
            new = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            with connect(dbp) as c:
                c.execute("INSERT INTO events (user_id, kind, created_at) VALUES (?, 'click', ?)", (uid, old))
                c.execute("INSERT INTO events (user_id, kind, created_at) VALUES (?, 'click', ?)", (uid, new))
                c.execute("INSERT INTO sessions VALUES ('h', ?, ?, ?)", (uid, old, old))
            report = prune_old(dbp)
            self.assertEqual((report["events"], report["sessions"]), (1, 1))
            with connect(dbp) as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
