"""
Tests for the For You personalisation stack: feed parsing, auth, learning and ranking.
Run: python3 -m unittest tests.test_foryou
"""

import os
import random
import tempfile
import unittest

from core import auth, newsfeed
from core.demo_news import seed_demo
from core.recommender import CORPUS, Recommender
from core.textfeatures import classify_topics, featurize, tokenize

RSS = b"""<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>Spurs win derby &amp; climb table</title><link>https://ex.com/a</link>
<description>&lt;p&gt;A late goal sealed the match.&lt;/p&gt;</description><pubDate>Fri, 20 Nov 2026 10:00:00 GMT</pubDate>
<media:thumbnail url="https://ex.com/a.jpg"/></item>
<item><title></title><link>https://ex.com/empty</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>NASA launches probe</title><link rel="alternate" href="https://ex.com/b"/>
<updated>2026-11-20T09:00:00Z</updated><summary>Rocket lifts off to Mars.</summary></entry></feed>"""


class TestTextFeatures(unittest.TestCase):
    def test_tokenize_drops_stopwords_and_stems(self):
        self.assertEqual(tokenize("The elections and the voters"), ["election", "voter"])

    def test_topics(self):
        _, topics, ents = featurize("India beat Australia in cricket final", "Kohli hit a century.", None)
        self.assertEqual(next(iter(topics)), "Sports")
        self.assertIn("India", ents)
        self.assertIn("Space", classify_topics(tokenize("NASA rocket launch to the moon")))


class TestFeedParsing(unittest.TestCase):
    def test_rss(self):
        items = newsfeed.parse_feed(RSS, {"id": "x", "publisher": "X", "topic": "Sports"})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Spurs win derby & climb table")
        self.assertEqual(items[0]["summary"], "A late goal sealed the match.")
        self.assertEqual(items[0]["image_url"], "https://ex.com/a.jpg")

    def test_atom(self):
        items = newsfeed.parse_feed(ATOM, {"id": "y", "publisher": "Y", "topic": "Space"})
        self.assertEqual(items[0]["url"], "https://ex.com/b")
        self.assertTrue(items[0]["published_at"].startswith("2026-11-20T09:00"))


class ForYouDBCase(unittest.TestCase):
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


class TestAuth(ForYouDBCase):
    def test_signup_login_session(self):
        uid = auth.create_user("reader_1", "correct horse", db_path=self.db)
        self.assertEqual(auth.authenticate("READER_1", "correct horse", self.db), uid)
        with self.assertRaises(auth.AuthError):
            auth.authenticate("reader_1", "wrong password", self.db)
        token = auth.create_session(uid, self.db)
        self.assertEqual(auth.user_for_token(token, self.db)["username"], "reader_1")
        auth.destroy_session(token, self.db)
        self.assertIsNone(auth.user_for_token(token, self.db))

    def test_validation(self):
        with self.assertRaises(auth.AuthError):
            auth.create_user("ab", "longenough", db_path=self.db)
        with self.assertRaises(auth.AuthError):
            auth.create_user("valid_name", "short", db_path=self.db)
        auth.create_user("dupe", "longenough", db_path=self.db)
        with self.assertRaises(auth.AuthError):
            auth.create_user("DUPE", "longenough", db_path=self.db)

    def test_password_not_stored_plain(self):
        h = auth.hash_password("secret-pass")
        self.assertNotIn("secret-pass", h)
        self.assertTrue(auth.verify_password("secret-pass", h))


class TestLearning(ForYouDBCase):
    def _articles(self, topic):
        corpus = CORPUS.get(self.db)
        return [a for a in corpus.articles.values() if next(iter(a["topics"])) == topic]

    def _share(self, items, topic):
        return sum(1 for i in items if i["topics"][0] == topic) / len(items)

    def test_feed_shifts_toward_what_user_reads(self):
        uid = auth.create_user("learner", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Business", "Politics", "Technology"])
        sports = self._articles("Sports")
        unread = {a["id"] for a in sports[4:]}

        def mean_rank(items):
            pos = [i for i, it in enumerate(items) if it["id"] in unread]
            return sum(pos) / len(pos) if pos else 999

        before = mean_rank(self.rec.rank(uid, limit=60, rng=random.Random(1)))

        for a in sports[:4]:
            self.rec.record(uid, {"kind": "click", "article_id": a["id"], "local_hour": 20})
            self.rec.record(uid, {"kind": "dwell", "article_id": a["id"], "value": 120, "local_hour": 20})
            self.rec.record(uid, {"kind": "like", "article_id": a["id"], "local_hour": 20})

        after = self.rec.rank(uid, limit=60, local_hour=20, rng=random.Random(1))
        # Unread sports stories climb from the back of the feed to the very top.
        self.assertLess(mean_rank(after), before)
        self.assertLessEqual(mean_rank(after), 4)
        self.assertEqual(after[0]["topics"][0], "Sports")
        prof = self.rec.profile(uid)
        self.assertEqual(prof["topics"][0]["key"], "Sports")
        self.assertIn("Sports", prof["dayparts"]["evening"])
        self.assertTrue(any(i["why"]["type"] in ("keyword", "topic", "entity", "daypart") for i in after[:3]))

    def test_read_articles_are_not_repeated(self):
        uid = auth.create_user("reader", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Sports", "Science", "Space"])
        first = self.rec.rank(uid, limit=5, rng=random.Random(2))[0]
        self.rec.record(uid, {"kind": "click", "article_id": first["id"]})
        ids = [i["id"] for i in self.rec.rank(uid, limit=40, rng=random.Random(2))]
        self.assertNotIn(first["id"], ids)

    def test_less_topic_and_mute(self):
        uid = auth.create_user("picky", "password123", db_path=self.db)
        self.rec.onboard(uid, ["Sports", "Gaming", "Entertainment"])
        self.rec.record(uid, {"kind": "less_topic", "topic": "Sports"})
        self.rec.record(uid, {"kind": "less_topic", "topic": "Sports"})
        top = self.rec.rank(uid, limit=8, rng=random.Random(3))
        self.assertLess(self._share(top, "Sports"), 0.25)

        pub = top[0]["publisher"]
        self.rec.record(uid, {"kind": "mute_source", "publisher": pub})
        self.assertFalse(any(i["publisher"] == pub for i in self.rec.rank(uid, limit=40)))
        self.assertIn(pub, self.rec.profile(uid)["muted_sources"])

    def test_bounce_is_negative(self):
        uid = auth.create_user("bouncer", "password123", db_path=self.db)
        a = self._articles("Health")[0]
        self.rec.record(uid, {"kind": "click", "article_id": a["id"]})
        w_click = self.rec.affinities(uid)["topic"]["Health"]
        self.rec.record(uid, {"kind": "dwell", "article_id": a["id"], "value": 3})
        self.assertLess(self.rec.affinities(uid)["topic"]["Health"], w_click)

    def test_collaborative_filtering(self):
        a_id = auth.create_user("alice", "password123", db_path=self.db)
        b_id = auth.create_user("bobby", "password123", db_path=self.db)
        sci = self._articles("Science")
        for art in sci[:2]:
            self.rec.record(a_id, {"kind": "like", "article_id": art["id"]})
            self.rec.record(b_id, {"kind": "like", "article_id": art["id"]})
        gaming = self._articles("Gaming")[0]
        self.rec.record(b_id, {"kind": "save", "article_id": gaming["id"]})
        self.assertGreater(self.rec._collaborative(a_id).get(gaming["id"], 0), 0)

    def test_reset(self):
        uid = auth.create_user("resetter", "password123", db_path=self.db)
        self.rec.onboard(uid, ["AI", "Science", "Space"])
        self.rec.reset(uid)
        self.assertEqual(self.rec.profile(uid)["topics"], [])


if __name__ == "__main__":
    unittest.main()
