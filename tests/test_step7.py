"""
Step 7: sign in with Google / GitHub / X / LinkedIn, interests from connected accounts, and the
chaptered personal audio brief.
  * OAuth: authorize URL + PKCE, single-use state bound to a cookie, safe redirects, account
    creation and linking, no merge by email, disconnect rules
  * social signals: what each provider contributes, idempotent re-sync, forget, region rules
  * personal audio: chapters, depth-sized length, follow and forecast segments
  * routing: sign-in lives on the About page; For You and its data need a session
Run: python3 -m unittest tests.test_step7
"""

import datetime as dt
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

from core import auth, oauth, social_signals
from core.brief_bridge import BRIEF
from core.newsfeed import connect, init_schema
from core.personal_audio import DEPTH_BUDGET, build_segments, build_script, chapters
from core.recommender import CORPUS, Recommender

KEYS = {f"PITH_{p.upper()}_{k}": f"{p}-{k.lower()}" for p in oauth.PROVIDERS for k in ("CLIENT_ID", "CLIENT_SECRET")}

GITHUB_USER = {"id": 4242, "login": "ada-dev", "name": "Ada Lovelace", "bio": "Building LLM inference tools in Rust",
               "company": "@openai", "location": "Bengaluru, India", "avatar_url": "https://avatars.example/ada",
               "public_repos": 3}
GITHUB_REPOS = [
    {"name": "fast-infer", "description": "Fast transformer inference server for large language models",
     "language": "Rust", "topics": ["llm", "machine-learning", "inference"], "fork": False,
     "owner": {"login": "ada-dev", "type": "User"}},
    {"name": "notes", "description": "my notes", "language": "Python", "topics": [], "fork": False,
     "owner": {"login": "ada-dev", "type": "User"}},
    {"name": "forked-thing", "description": "someone else's", "language": "Go", "topics": [], "fork": True,
     "owner": {"login": "ada-dev", "type": "User"}},
]
GITHUB_STARS = [
    {"name": "vllm", "description": "High-throughput LLM serving engine", "language": "Python",
     "topics": ["gpu", "llm"], "fork": False, "owner": {"login": "vllm-project", "type": "Organization"}},
    {"name": "transformers", "description": "State-of-the-art machine learning for PyTorch", "language": "Python",
     "topics": ["nlp", "deep-learning"], "fork": False, "owner": {"login": "huggingface", "type": "Organization"}},
]


def fake_http(responses):
    """responses: list of (url substring, status, payload). Records every call."""
    calls = []

    def http(method, url, data=None, headers=None):
        calls.append({"method": method, "url": url, "data": data, "headers": headers or {}})
        for needle, status, payload in responses:
            if needle in url:
                return status, payload
        return 404, {}
    http.calls = calls
    return http


def github_http():
    # Order matters: "api.github.com/user" is also a substring of the /users/... URLs.
    return fake_http([
        ("login/oauth/access_token", 200, {"access_token": "gho_token"}),
        ("/users/ada-dev/repos", 200, GITHUB_REPOS),
        ("/users/ada-dev/starred", 200, GITHUB_STARS),
        ("api.github.com/user", 200, GITHUB_USER),
    ])


class OAuthEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "foryou.sqlite3")
        init_schema(self.db)
        CORPUS._sig = None
        BRIEF._sig = None
        self.env = mock.patch.dict(os.environ, KEYS)
        self.env.start()
        self.http_orig = oauth.HTTP

    def tearDown(self):
        oauth.HTTP = self.http_orig
        self.env.stop()
        CORPUS._sig = None
        BRIEF._sig = None
        self.tmp.cleanup()

    def login(self, provider="github", http=None, link_user_id=None):
        oauth.HTTP = http or github_http()
        url, state = oauth.start(provider, "http://localhost:8010", "/foryou", link_user_id, self.db)
        result = oauth.complete(provider, "code-1", state, state, "http://localhost:8010", self.db)
        uid, created = oauth.sign_in(result["profile"], result["link_user_id"], self.db)
        return uid, created, result

    def aff(self, uid, kind, key):
        return Recommender(self.db).affinities(uid).get(kind, {}).get(key, 0.0)


class TestOAuthFlow(OAuthEnv):
    def test_authorize_url_and_pkce(self):
        url, state = oauth.start("google", "http://localhost:8010", "/foryou", None, self.db)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.assertEqual(q["client_id"], "google-client_id")
        self.assertEqual(q["redirect_uri"], "http://localhost:8010/api/auth/oauth/google/callback")
        self.assertEqual(q["state"], state)
        self.assertEqual(q["code_challenge_method"], "S256")
        self.assertNotIn("email", q["scope"])                    # no email is ever requested
        gh, _ = oauth.start("github", "http://localhost:8010", None, None, self.db)
        self.assertNotIn("code_challenge", gh)
        with connect(self.db) as conn:                           # state is stored hashed, never raw
            self.assertIsNone(conn.execute("SELECT 1 FROM oauth_states WHERE state_hash=?", (state,)).fetchone())

    def test_unconfigured_provider_is_refused(self):
        with mock.patch.dict(os.environ, {"PITH_LINKEDIN_CLIENT_ID": ""}):
            self.assertFalse(oauth.configured("linkedin"))
            with self.assertRaises(oauth.OAuthError):
                oauth.start("linkedin", "http://x", None, None, self.db)

    def test_base_url_env_wins(self):
        with mock.patch.dict(os.environ, {"PITH_AUTH_BASE_URL": "https://pith.example.com/"}):
            self.assertEqual(oauth.redirect_uri("x", "http://evil"), "https://pith.example.com/api/auth/oauth/x/callback")

    def test_state_must_match_cookie_and_is_single_use(self):
        oauth.HTTP = github_http()
        _, state = oauth.start("github", "http://h", None, None, self.db)
        with self.assertRaises(oauth.OAuthError):
            oauth.complete("github", "c", state, "other-cookie", "http://h", self.db)
        _, state = oauth.start("github", "http://h", None, None, self.db)
        oauth.complete("github", "c", state, state, "http://h", self.db)
        with self.assertRaises(oauth.OAuthError):
            oauth.complete("github", "c", state, state, "http://h", self.db)

    def test_state_for_another_provider_or_expired_is_refused(self):
        oauth.HTTP = github_http()
        _, state = oauth.start("github", "http://h", None, None, self.db)
        with self.assertRaises(oauth.OAuthError):
            oauth.complete("google", "c", state, state, "http://h", self.db)
        _, state = oauth.start("github", "http://h", None, None, self.db)
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=30)).isoformat(timespec="seconds")
        with connect(self.db) as conn:
            conn.execute("UPDATE oauth_states SET created_at=?", (old,))
        with self.assertRaises(oauth.OAuthError):
            oauth.complete("github", "c", state, state, "http://h", self.db)

    def test_safe_next_blocks_open_redirects(self):
        for bad in ("https://evil.com", "//evil.com", "/\\evil", "javascript:alert(1)", "",
                    "/\t/evil.com", "/\n/evil.com", "/a\r\nSet-Cookie: x=1", "/caf\u00e9", None, ["/x"]):
            self.assertEqual(oauth.safe_next(bad), "/", repr(bad))
        self.assertEqual(oauth.safe_next("/foryou?x=1"), "/foryou?x=1")
        self.assertEqual(oauth.safe_next("bad", default="/foryou"), "/foryou")

    def test_token_exchange_failure(self):
        oauth.HTTP = fake_http([("login/oauth/access_token", 400, {"error": "bad_verification_code"})])
        _, state = oauth.start("github", "http://h", None, None, self.db)
        with self.assertRaises(oauth.OAuthError):
            oauth.complete("github", "c", state, state, "http://h", self.db)

    def test_x_uses_basic_auth_and_pkce_verifier(self):
        http = fake_http([("oauth2/token", 200, {"access_token": "x-token"}),
                          ("/following", 403, {"title": "Client Forbidden"}),
                          ("users/me", 200, {"data": {"id": "77", "username": "adax", "name": "Ada",
                                                      "description": "#RustLang and #AI", "location": "London"}})])
        uid, created, result = self.login("x", http)
        token_call = next(c for c in http.calls if "oauth2/token" in c["url"])
        self.assertTrue(token_call["headers"]["Authorization"].startswith("Basic "))
        self.assertIn("code_verifier", token_call["data"])
        self.assertNotIn("client_secret", token_call["data"])
        self.assertTrue(result["profile"]["data"]["notes"])        # follows refused -> explained, not fatal
        self.assertTrue(created)

    def test_account_created_once_and_reused(self):
        uid, created, result = self.login()
        self.assertTrue(created)
        with connect(self.db) as conn:
            row = conn.execute("SELECT username, display_name, password_hash FROM users WHERE id=?", (uid,)).fetchone()
        self.assertEqual(row["username"], "ada-dev")
        self.assertEqual(row["display_name"], "Ada Lovelace")
        self.assertFalse(oauth.has_password(uid, self.db))
        with self.assertRaises(auth.AuthError):                   # no password login for OAuth-only accounts
            auth.authenticate("ada-dev", "oauth$github", self.db)
        uid2, created2, _ = self.login()
        self.assertEqual((uid2, created2), (uid, False))

    def test_username_collision_gets_suffix(self):
        auth.create_user("ada-dev", "password123", db_path=self.db)
        uid, _, _ = self.login()
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()[0], "ada-dev2")

    def test_linking_to_signed_in_reader_and_no_hijack(self):
        me = auth.create_user("reader", "password123", db_path=self.db)
        uid, created, _ = self.login(link_user_id=me)
        self.assertEqual((uid, created), (me, False))
        other = auth.create_user("other", "password123", db_path=self.db)
        with self.assertRaises(oauth.OAuthError):
            self.login(link_user_id=other)

    def test_disconnect_rules(self):
        uid, _, _ = self.login()
        with self.assertRaises(oauth.OAuthError):                # only way in: refuse
            oauth.disconnect(uid, "github", self.db)
        me = auth.create_user("pw-reader", "password123", db_path=self.db)
        x_http = fake_http([("oauth2/token", 200, {"access_token": "t"}),
                            ("/following", 403, {}),
                            ("users/me", 200, {"data": {"id": "99", "username": "pw", "name": "PW"}})])
        self.login("x", x_http, link_user_id=me)
        oauth.disconnect(me, "x", self.db)                       # has a password: fine
        self.assertEqual(oauth.identities(me, self.db), [])


class TestSocialSignals(OAuthEnv):
    def test_github_derivation(self):
        _, _, result = self.login()
        d = social_signals.derive(result["profile"], self.db)
        w = d["weights"]
        self.assertIn("AI", w["topic"])
        self.assertIn("Technology", w["topic"])
        self.assertIn("rust", w["keyword"])
        self.assertIn("OpenAI", w["entity"])                     # company
        self.assertIn("Hugging Face", w["entity"])               # starred org, news spelling
        self.assertEqual(d["region"], "india")
        self.assertTrue(any("repositories" in e for e in d["summary"]["evidence"]))

    def test_locale_providers(self):
        g = {"provider": "google", "data": {"country": "GB"}}
        self.assertEqual(social_signals.derive(g, self.db)["region"], "uk")
        li = social_signals.derive({"provider": "linkedin", "data": {"country": "IN"}}, self.db)
        self.assertEqual(li["region"], "india")
        self.assertIn("Business", li["weights"]["topic"])
        self.assertEqual(social_signals.region_from_place("Remote, Earth"), None)
        self.assertEqual(social_signals.region_from_place("SF Bay Area"), "americas")

    def test_sync_is_idempotent_and_forget_reverts(self):
        uid, _, result = self.login()
        social_signals.sync(uid, result["profile"], self.db)
        first = self.aff(uid, "topic", "AI")
        self.assertGreater(first, 1.0)
        social_signals.sync(uid, result["profile"], self.db)     # signing in again
        self.assertAlmostEqual(self.aff(uid, "topic", "AI"), first, places=2)
        self.assertEqual(self.aff(uid, "keyword", "rust") > 0, True)
        with connect(self.db) as conn:
            self.assertEqual(json.loads(conn.execute(
                "SELECT value FROM user_prefs WHERE user_id=? AND key='region'", (uid,)).fetchone()[0]), "india")
        self.assertTrue(social_signals.forget(uid, "github", self.db))
        self.assertAlmostEqual(self.aff(uid, "topic", "AI"), 0.0, places=2)
        with connect(self.db) as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM user_prefs WHERE user_id=? AND key='region'", (uid,)).fetchone())

    def test_explicit_region_is_never_overwritten(self):
        uid, _, result = self.login()
        from core import prefs
        prefs.set_prefs(uid, {"region": "europe"}, self.db)
        summary = social_signals.sync(uid, result["profile"], self.db)
        self.assertFalse(summary["region_applied"])
        self.assertEqual(prefs.get_prefs(uid, self.db)["region"], "europe")
        social_signals.forget(uid, "github", self.db)
        self.assertEqual(prefs.get_prefs(uid, self.db)["region"], "europe")

    def test_connections_view_and_onboarding_topics(self):
        uid, _, result = self.login()
        social_signals.sync(uid, result["profile"], self.db)
        view = social_signals.connections(uid, self.db)
        self.assertEqual(view["accounts"][0]["provider"], "github")
        self.assertFalse(view["accounts"][0]["can_disconnect"])
        self.assertIn("google", {p["id"] for p in view["available"]})
        self.assertIn("AI", social_signals.imported_topics(uid, self.db))
        self.assertGreater(Recommender(self.db).confidence(uid), 0)
        Recommender(self.db).reset(uid)                          # "reset my profile" clears imports too
        self.assertEqual(social_signals.summaries(uid, self.db), {})


def _your5(n=5):
    cards = []
    for i in range(n):
        cards.append({"id": f"c{i}", "headline": f"Headline number {i} about inference",
                      "why_it_matters": "It changes what inference costs for most teams.",
                      "second_order": ["Smaller labs can now afford long context windows."],
                      "role_view": {"impact": "Your inference bill drops this quarter.", "action_type": "DO",
                                    "action_text": "Re-run your cost model with the new prices."},
                      "prediction": {"statement": "Three runtimes ship the feature by June.", "probability": 0.7}})
    return {"cards": cards, "inferred_role": "developer"}


class TestPersonalAudio(unittest.TestCase):
    def test_chapters_and_budget(self):
        extras = {"top_topics": ["AI", "Markets"],
                  "follow_updates": [{"title": "Chip rules tighten again", "publisher": "Reuters"}],
                  "forecast": {"open_calls": 2, "newly_resolved": []}}
        segs = build_segments(_your5(), "Ada", 8, "standard", extras)
        kinds = [s["kind"] for s in segs]
        self.assertEqual(kinds[0], "intro")
        self.assertEqual(kinds.count("story"), 5)
        self.assertIn("follows", kinds)
        self.assertEqual(kinds[-1], "outro")
        self.assertTrue(segs[0]["text"].startswith("Good morning, Ada."))
        self.assertEqual(segs[1]["card_id"], "c0")
        starts = [c["start"] for c in chapters(segs)]
        self.assertEqual(starts[0], 0)
        self.assertEqual(starts, sorted(starts))
        for depth in ("headline", "standard", "deep"):
            words = len(build_script(_your5(), "Ada", 8, depth, extras).split())
            self.assertLessEqual(words, DEPTH_BUDGET[depth] + 40, depth)
        self.assertLess(len(build_script(_your5(), "", 8, "headline").split()),
                        len(build_script(_your5(), "", 8, "deep").split()))

    def test_every_story_survives_trimming(self):
        script = build_script(_your5(), "Ada", 20, "headline")
        for i in range(5):
            self.assertIn(f"Headline number {i}", script)
        self.assertTrue(script.startswith("Good evening, Ada."))

    def test_resolved_forecast_segment(self):
        extras = {"forecast": {"open_calls": 0, "newly_resolved": [
            {"statement": "Three runtimes ship the feature by June.", "status": "correct", "beat_pith": True}]}}
        segs = build_segments(_your5(), "", 9, "standard", extras)
        fc = next(s for s in segs if s["kind"] == "forecasts")
        self.assertIn("You beat Pith", fc["text"])


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import http.client
        import threading
        import server
        cls.http = http.client
        cls.httpd = server.ThreadingServer(("127.0.0.1", 0), server.BriefHTTPRequestHandler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path):
        conn = self.http.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r.status, r.getheader("Location"), body

    def test_sign_in_lives_on_about_and_for_you_needs_login(self):
        status, loc, _ = self._get("/foryou")
        self.assertEqual((status, loc), (302, "/about?next=/foryou#access"))
        status, _, body = self._get("/about")
        self.assertEqual(status, 200)
        self.assertIn(b"Continue with GitHub", body)
        self.assertIn(b'id="about-auth-form"', body)
        self.assertNotIn(b"Guest Pass", body)
        status, _, _ = self._get("/api/feed?tab=foryou")
        self.assertEqual(status, 401)

    def test_providers_endpoint(self):
        status, _, body = self._get("/api/auth/providers")
        self.assertEqual(status, 200)
        self.assertEqual({p["id"] for p in json.loads(body)["providers"]}, {"google", "github", "x", "linkedin"})

    def test_unconfigured_start_redirects_with_message(self):
        with mock.patch.dict(os.environ, {"PITH_GOOGLE_CLIENT_ID": "", "PITH_GOOGLE_CLIENT_SECRET": ""}):
            status, loc, _ = self._get("/api/auth/oauth/google/start")
        self.assertEqual(status, 302)
        self.assertTrue(loc.startswith("/about?auth_error="), loc)

    def test_callback_without_state_is_refused(self):
        with mock.patch.dict(os.environ, KEYS):
            status, loc, _ = self._get("/api/auth/oauth/github/callback?code=abc&state=forged")
        self.assertEqual(status, 302)
        self.assertIn("auth_error", loc)


if __name__ == "__main__":
    unittest.main()
