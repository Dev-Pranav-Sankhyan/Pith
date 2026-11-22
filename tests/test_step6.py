"""
Step 6: real personalisation across both halves.
  * learning fixes (event allowlist, neutral "worth my time" undo, brief cards train the profile,
    dwell judged against the reader's own median)
  * role inference by whole tokens
  * the brief pool and a Your 5 that actually chooses
  * follows and story threads, preferences and depth
  * the personal forecast record (live only, call window, implied probability)
  * reader-added feeds (SSRF guards, private visibility), experiments, onboarding pairs, audio script
Run: python3 -m unittest tests.test_step6
"""

import datetime as dt
import json
import os
import random
import tempfile
import unittest

from core import auth, experiments, follows, prefs, userfeeds
from core.brief_bridge import BRIEF
from core.db import Database
from core.demo_news import seed_demo
from core.models import Card, DailyIssue, EvidenceLink, Prediction, RoleView
from core.newsfeed import connect, init_schema, store_articles
from core.personal_audio import build_script, script_stats
from core.personal_forecasts import forecast_record, implied_probability, vote_allowed
from core.recommender import CORPUS, Recommender
from core.your5 import Your5Engine, infer_role
from pipeline.experiment_report import compare, variant_metrics


def make_card(cid, headline, text="", score=80.0, date="2026-11-21", prob=0.7, made_at=None):
    rv = RoleView(impact=f"Impact of {headline}.", action_type="WATCH", action_text="Watch it.")
    return Card(
        id=cid, date=date, headline=headline, what_happened=text or f"{headline}. Details follow.",
        why_it_matters="It matters.", second_order=["One", "Two"], signal_score=score, signal_level="High",
        signal_reason="r", confidence="High", action_type="WATCH", action_text="Watch it.",
        prediction=Prediction(id=f"p-{cid}", statement=f"{headline} happens", probability=prob,
                              resolves_at="2027-06-01", resolution_criteria="Docs say so.",
                              made_at=made_at or date, card_id=cid),
        role_views={r: rv for r in ("developer", "founder", "investor", "everyday")},
        evidence_links=[EvidenceLink(title="src", url=f"https://example.com/{cid}", publisher="Example")],
    )


class Env(unittest.TestCase):
    """Temp For You DB seeded with demo news, plus a temp brief DB with core + pool cards."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fy = os.path.join(self.tmp.name, "foryou.sqlite3")
        self.brief = os.path.join(self.tmp.name, "brief.sqlite3")
        init_schema(self.fy)
        seed_demo(self.fy)
        CORPUS._sig = None
        BRIEF._sig = None
        core = [make_card(f"core-{i}", f"Inference runtime update number {i}", score=90 - i) for i in range(5)]
        pool = [make_card("pool-quantum", "Quantum computing error correction milestone",
                          "Quantum computing researchers report logical qubits with error correction.", score=66),
                make_card("pool-chips", "Chip export rules tighten for accelerators", score=64)]
        self.issue = DailyIssue(issue_id="issue-2026-11-21", date="2026-11-21", cards=core, pool=pool)
        Database(self.brief).save_issue(self.issue)
        self.rec = Recommender(self.fy, brief_db=self.brief)
        self.uid = auth.create_user("reader1", "password123", db_path=self.fy)

    def tearDown(self):
        CORPUS._sig = None
        BRIEF._sig = None
        self.tmp.cleanup()

    def aff(self, kind, key):
        return self.rec.affinities(self.uid).get(kind, {}).get(key, 0.0)


class TestLearningFixes(Env):
    def test_unknown_event_kind_is_dropped(self):
        self.rec.record(self.uid, {"kind": "totally_made_up", "article_id": "x"})
        with connect(self.fy) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM events WHERE kind='totally_made_up'").fetchone()[0], 0)

    def test_clearing_worth_is_neutral_not_negative(self):
        a = list(CORPUS.get(self.fy).articles.values())[0]
        topic = next(iter(a["topics"]))
        self.rec.record(self.uid, {"kind": "worth_time", "article_id": a["id"]})
        self.assertGreater(self.aff("topic", topic), 0)
        self.rec.record(self.uid, {"kind": "clear_worth", "article_id": a["id"]})
        self.assertAlmostEqual(self.aff("topic", topic), 0.0, places=2)

    def test_repeated_worth_tap_learns_once_and_switch_is_clean(self):
        a = list(CORPUS.get(self.fy).articles.values())[1]
        topic = next(iter(a["topics"]))
        self.rec.record(self.uid, {"kind": "worth_time", "article_id": a["id"]})
        once = self.aff("topic", topic)
        self.rec.record(self.uid, {"kind": "worth_time", "article_id": a["id"]})
        self.assertAlmostEqual(self.aff("topic", topic), once, places=3)
        self.rec.record(self.uid, {"kind": "not_worth_time", "article_id": a["id"]})
        self.assertLess(self.aff("topic", topic), 0)  # now only the "not worth it" remains

    def test_brief_card_feedback_trains_the_profile(self):
        self.rec.record(self.uid, {"kind": "worth_time", "article_id": "pool-quantum"})
        kws = self.rec.affinities(self.uid).get("keyword", {})
        self.assertTrue(any(k.startswith("quantum") and w > 0 for k, w in kws.items()), kws)

    def test_dwell_baseline_is_the_readers_own_median(self):
        arts = list(CORPUS.get(self.fy).articles.values())
        with connect(self.fy) as conn:
            for a in arts[:6]:
                conn.execute("INSERT INTO user_articles (user_id, article_id, dwell_seconds, last_seen) VALUES (?,?,?,?)",
                             (self.uid, a["id"], 200.0, "2026-11-20T10:00:00+00:00"))
            self.assertEqual(self.rec._typical_dwell(conn, self.uid, arts[10]), 200.0)


class TestRoleInference(unittest.TestCase):
    def test_substrings_no_longer_match(self):
        # "second" used to count as investor ("sec"), "capital" letters in "capture" etc.
        role, conf, reason = infer_role({"keyword": {"second": 9.0, "captur": 9.0, "tokenis": 9.0}})
        self.assertEqual(role, "developer")
        self.assertLess(conf, 0.5)
        self.assertIn("Not enough reading", reason)

    def test_no_built_in_developer_bias(self):
        role, _, _ = infer_role({"topic": {"Science": 3.0}})
        self.assertEqual(role, "everyday")


class TestPoolAndYour5(Env):
    def test_pool_round_trips_and_validates(self):
        loaded = Database(self.brief).get_latest_issue()
        self.assertEqual(len(loaded.cards), 5)
        self.assertEqual({c.id for c in loaded.pool}, {"pool-quantum", "pool-chips"})
        bad = DailyIssue(issue_id="x", date="2026-11-21", cards=[self.issue.cards[0]], pool=[self.issue.cards[0]])
        self.assertTrue(any("both" in e for e in bad.validate()))

    def test_anonymous_gets_the_editorial_five(self):
        res = Your5Engine(self.brief, self.fy).get_your_5(None)
        self.assertEqual([c["id"] for c in res["cards"]][0], "core-0")
        self.assertEqual(res["cards"][0]["slot"], "must_know")
        self.assertEqual(res["pool_size"], 7)
        self.assertNotIn("pool-quantum", [c["id"] for c in res["cards"]])

    def test_reader_interest_pulls_in_a_pool_card(self):
        self.rec.follow(self.uid, "keyword", "quantum computing")
        res = Your5Engine(self.brief, self.fy).get_your_5(self.uid)
        ids = [c["id"] for c in res["cards"]]
        self.assertEqual(ids[0], "core-0")            # must-know stays for everyone
        self.assertIn("pool-quantum", ids)
        card = next(c for c in res["cards"] if c["id"] == "pool-quantum")
        self.assertIn("quantum computing", card["why_chosen"])
        self.assertEqual(len(ids), 5)

    def test_hidden_card_is_never_picked(self):
        self.rec.record(self.uid, {"kind": "hide", "article_id": "core-1"})
        ids = [c["id"] for c in Your5Engine(self.brief, self.fy).get_your_5(self.uid)["cards"]]
        self.assertNotIn("core-1", ids)


class TestFollows(Env):
    def test_entity_and_keyword_matching(self):
        a = {"title": "OpenAI ships a new model", "summary": "", "entities": ["OpenAI"]}
        self.assertTrue(follows.matches({"kind": "entity", "key": "openai"}, a))
        self.assertFalse(follows.matches({"kind": "entity", "key": "open"}, a))
        b = {"title": "India elections: turnout record", "summary": "", "entities": []}
        self.assertTrue(follows.matches({"kind": "keyword", "key": "india elections"}, b))

    def test_story_follow_finds_later_coverage(self):
        seed = {"id": "s1", "title": "Acme releases Widget 3.2 with faster compiler",
                "summary": "Acme Widget 3.2 compiler is 40% faster.", "keywords": {"widget": 1.0, "acme": 0.8, "compil": 0.6},
                "entities": ["Acme", "Widget"], "published_at": "2026-11-20T00:00:00+00:00"}
        f = {"kind": "story", "key": "s1", "label": seed["title"], "seed": follows.story_seed(seed)}
        later = {"id": "s2", "title": "Hands-on with Acme Widget 3.2 and its new compiler",
                 "summary": "We tried Widget 3.2.", "keywords": {"widget": 1.0, "acme": 0.7, "compil": 0.5},
                 "entities": ["Acme", "Widget"]}
        unrelated = {"id": "s3", "title": "Football season opens", "summary": "Kickoff.",
                     "keywords": {"football": 1.0}, "entities": []}
        self.assertTrue(follows.matches(f, later))
        self.assertFalse(follows.matches(f, unrelated))
        self.assertFalse(follows.matches(f, seed))  # the story itself is not an update

    def test_follow_boosts_ranking_and_explains(self):
        corpus = CORPUS.get(self.fy)
        target = next(a for a in corpus.articles.values() if a["entities"])
        ent = target["entities"][0]
        self.rec.follow(self.uid, "entity", ent, ent)
        feed = self.rec.rank(self.uid, limit=60, rng=random.Random(1))
        hit = next((c for c in feed if c["id"] == target["id"]), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["why"]["type"], "follow")
        self.assertTrue(any(c["follow"]["kind"] == "entity" for c in self.rec.following(self.uid)))

    def test_follow_limit_and_validation(self):
        with self.assertRaises(ValueError):
            follows.follow(self.uid, "nonsense", "x", db_path=self.fy)
        with self.assertRaises(ValueError):
            follows.follow(self.uid, "story", "x", db_path=self.fy)  # no seed


class TestPrefs(Env):
    def test_validation(self):
        with self.assertRaises(ValueError):
            prefs.set_prefs(self.uid, {"depth": "huge"}, self.fy)
        with self.assertRaises(ValueError):
            prefs.set_prefs(self.uid, {"delivery_hour": 25}, self.fy)
        with self.assertRaises(ValueError):
            prefs.set_prefs(self.uid, {"last_forecast_seen": "x"}, self.fy)  # server-only
        p = prefs.set_prefs(self.uid, {"depth": "deep", "delivery_hour": 7, "region": "india"}, self.fy)
        self.assertEqual((p["depth"], p["delivery_hour"], p["region"]), ("deep", 7, "india"))

    def test_depth_inferred_from_dwell(self):
        self.assertEqual(prefs.effective_depth(self.uid, self.fy)["depth"], "standard")
        arts = list(CORPUS.get(self.fy).articles.values())
        with connect(self.fy) as conn:
            for a in arts[:6]:
                conn.execute("INSERT INTO user_articles (user_id, article_id, dwell_seconds, last_seen) VALUES (?,?,?,?)",
                             (self.uid, a["id"], 10.0, "2026-11-20T10:00:00+00:00"))
        self.assertEqual(prefs.effective_depth(self.uid, self.fy)["depth"], "headline")
        prefs.set_prefs(self.uid, {"depth": "deep"}, self.fy)
        self.assertEqual(prefs.effective_depth(self.uid, self.fy), {"depth": "deep", "source": "chosen", "reason": "Your setting"})


class TestPersonalForecasts(Env):
    def _vote(self, card_id, vote, when):
        with connect(self.fy) as conn:
            conn.execute("INSERT INTO forecast_votes (user_id, card_id, vote, created_at, updated_at) VALUES (?,?,?,?,?)",
                         (self.uid, card_id, vote, when, when))

    def test_implied_probability(self):
        self.assertEqual(implied_probability(0.7, "higher"), 0.85)
        self.assertEqual(implied_probability(0.1, "lower"), 0.02)

    def test_scoring_window_live_only_and_brier(self):
        db = Database(self.brief)
        old = [make_card("old-a", "Old A", date="2026-10-01", prob=0.7),
               make_card("old-b", "Old B", date="2026-10-01", prob=0.6)]
        db.save_issue(DailyIssue(issue_id="issue-2026-10-01", date="2026-10-01", cards=old))
        with db.get_connection() as conn:  # an illustrative prediction must never be scored
            conn.execute("UPDATE predictions SET provenance='illustrative' WHERE id='p-old-b'")
        self._vote("old-a", "higher", "2026-10-02T09:00:00+00:00")   # inside the 3-day window
        self._vote("old-b", "higher", "2026-10-02T09:00:00+00:00")
        self._vote("core-0", "lower", "2026-12-30T09:00:00+00:00")   # far outside the window: late
        db.record_resolution("p-old-a", "correct", "https://example.com/proof", None, "Tester")
        r = forecast_record(self.uid, self.fy, self.brief)
        s = r["stats"]
        self.assertEqual(s["scored"], 1)
        self.assertEqual(s["beat"], 1)
        self.assertAlmostEqual(s["your_brier"], 0.0225, places=4)   # (0.85 - 1)^2
        self.assertAlmostEqual(s["pith_brier"], 0.09, places=4)     # (0.70 - 1)^2
        self.assertIsNone(s["verdict"])                             # too few to declare
        self.assertEqual(s["late_calls"], 1)
        self.assertEqual(len(r["newly_resolved"]), 1)
        self.assertFalse(vote_allowed("old-a", self.brief)[0])      # resolved: calls closed
        self.assertTrue(vote_allowed("core-0", self.brief)[0])
        self.assertFalse(vote_allowed("no-such-card", self.brief)[0])


class TestUserFeeds(Env):
    def test_ssrf_guards(self):
        for bad in ("http://127.0.0.1/feed", "http://localhost/rss", "file:///etc/passwd", "ftp://example.com/x",
                    "http://user:pw@example.com/rss", "http://10.0.0.5/rss", "http://169.254.169.254/latest",
                    "http://[::1]/rss", "http://example.com:22/rss"):
            with self.assertRaises(userfeeds.FeedError, msg=bad):
                userfeeds.validate_url(bad)

    def test_private_feed_articles_only_reach_subscribers(self):
        fid = "u-test0000001"
        store_articles([{"title": "Hyperlocal council vote on bike lanes", "url": "https://local.example/bike",
                         "summary": "Council votes.", "publisher": "Local Paper", "feed_id": fid, "feed_topic": None,
                         "published_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}], self.fy)
        CORPUS._sig = None
        aid = next(a["id"] for a in CORPUS.get(self.fy).articles.values() if a["feed_id"] == fid)
        other = auth.create_user("reader2", "password123", db_path=self.fy)
        with connect(self.fy) as conn:
            conn.execute("INSERT INTO custom_feeds (feed_id, url, title, created_at) VALUES (?,?,?,?)",
                         (fid, "https://local.example/rss", "Local Paper", "2026-11-21T00:00:00+00:00"))
            conn.execute("INSERT INTO user_feeds (user_id, feed_id, added_at) VALUES (?,?,?)",
                         (self.uid, fid, "2026-11-21T00:00:00+00:00"))
        mine = [c["id"] for c in self.rec.rank(self.uid, limit=60)]
        theirs = [c["id"] for c in self.rec.rank(other, limit=60)]
        trending = [c["id"] for c in self.rec.trending(None, limit=60)]
        self.assertIn(aid, mine)
        self.assertNotIn(aid, theirs)
        self.assertNotIn(aid, trending)


class TestExperimentsOnboardingAudio(Env):
    def test_assignment_is_stable_and_exposure_logged(self):
        self.assertEqual(experiments.assign(self.uid, "explore_rate_v1"), experiments.assign(self.uid, "explore_rate_v1"))
        self.rec.rank(self.uid, limit=10)
        with connect(self.fy) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM experiment_exposures WHERE user_id=?",
                                          (self.uid,)).fetchone()[0], len(experiments.EXPERIMENTS))
        report = compare(variant_metrics("explore_rate_v1", self.fy))
        self.assertIn("not enough data", report["note"])

    def test_onboarding_pairs_and_choices(self):
        pairs = self.rec.onboarding_pairs(rng=random.Random(3))
        self.assertGreaterEqual(len(pairs), 3)
        for a, b in pairs:
            self.assertNotEqual(a["topic"], b["topic"])
        chosen, rejected = pairs[0]
        self.rec.onboard(self.uid, [], choices=[{"chosen": chosen["id"], "rejected": rejected["id"]}])
        self.assertGreater(self.aff("topic", chosen["topic"]), self.aff("topic", rejected["topic"]))
        self.assertGreater(self.rec.confidence(self.uid), 0)

    def test_audio_script(self):
        res = Your5Engine(self.brief, self.fy).get_your_5(self.uid)
        script = build_script(res, "Sam", 8)
        self.assertTrue(script.startswith("Good morning, Sam."))
        self.assertIn(res["cards"][0]["headline"], script)
        self.assertLess(script_stats(script)["words"], 400)


if __name__ == "__main__":
    unittest.main()
