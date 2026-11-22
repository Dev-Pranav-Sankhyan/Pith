"""
Step 8: the About page is the front door, plus the loopholes closed in the same pass.
  * access: signed out, only /about and its shell assets load; every member page redirects to
    About (with ?next=), every data file and API answers 401; signed in, everything loads
  * the gate decides on the decoded, normalised path, so encodings and dot segments can't slip by
  * HEAD gets the same gate as GET
  * hardening: negative Content-Length, non-object JSON, non-text credentials, odd event
    payloads, non-ASCII OAuth state, control characters in redirects, DNS-rebinding feed fetches
Run: python3 -m unittest tests.test_step8
"""

import http.client
import json
import os
import socket
import tempfile
import threading
import unittest
from unittest import mock

import server
from core import auth, oauth, userfeeds
from core.brief_bridge import BRIEF
from core.newsfeed import init_schema
from core.ratelimit import RateLimiter
from core.recommender import CORPUS, Recommender


class GateEnv(unittest.TestCase):
    """The real handler on an ephemeral port, with a throwaway For You database."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "foryou.sqlite3")
        init_schema(cls.db)
        cls.patches = [mock.patch.object(server, "FOR_YOU_DB", cls.db),
                       mock.patch.object(server, "recommender", Recommender(cls.db))]
        for p in cls.patches:
            p.start()
        CORPUS._sig = None
        BRIEF._sig = None
        uid = auth.create_user("gate_reader", "correct horse battery", "Gate Reader", cls.db)
        cls.token = auth.create_session(uid, cls.db)
        cls.httpd = server.ThreadingServer(("127.0.0.1", 0), server.BriefHTTPRequestHandler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for p in cls.patches:
            p.stop()
        CORPUS._sig = None
        BRIEF._sig = None
        cls.tmp.cleanup()

    def request(self, method, path, body=None, headers=None, signed_in=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = dict(headers or {})
        if signed_in:
            headers["Cookie"] = f"{auth.COOKIE_NAME}={self.token}"
        conn.putrequest(method, path, skip_accept_encoding=True)
        for k, v in headers.items():
            conn.putheader(k, v)
        if body is not None and "Content-Length" not in headers:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        return r.status, r, data

    def get(self, path, signed_in=False):
        return self.request("GET", path, signed_in=signed_in)

    def post_json(self, path, payload, signed_in=False, raw=None):
        body = raw if raw is not None else json.dumps(payload).encode()
        return self.request("POST", path, body, {"Content-Type": "application/json"}, signed_in)


class TestSignedOut(GateEnv):
    def test_about_and_its_assets_are_open(self):
        for path in ("/about", "/about.html", "/ABOUT", "/about/", "/style.css", "/app.js", "/favicon.svg"):
            status, _, _ = self.get(path)
            self.assertEqual(status, 200, path)
        status, r, body = self.get("/about")
        self.assertIn(b'data-session="out"', body)
        self.assertIn(b"Sign in to read Pith", body)
        self.assertEqual(r.getheader("Vary"), "Cookie")

    def test_member_pages_redirect_to_about_with_next(self):
        expect = {"/": "/about", "/index.html": "/about?next=/index.html#access",
                  "/ledger": "/about?next=/ledger#access", "/archive": "/about?next=/archive#access",
                  "/patterns.html": "/about?next=/patterns.html#access", "/foryou": "/about?next=/foryou#access",
                  "/for-you": "/about?next=/for-you#access", "/horizon": "/about"}
        for path, location in expect.items():
            status, r, _ = self.get(path)
            self.assertEqual((status, r.getheader("Location")), (302, location), path)
        status, r, _ = self.get("/login")
        self.assertEqual((status, r.getheader("Location")), (302, "/about#access"))

    def test_encoded_and_dotted_paths_cannot_bypass(self):
        for path in ("/l%65dger.html", "/%69ndex.html", "/about.html/../index.html", "/ABOUT.HTML/../LEDGER.HTML",
                     "//index.html", "/./ledger.html", "/static/../patterns.html", "/about%2f..%2findex.html",
                     "/index.html%00", "/style.css/../feed.json", "/LEDGER.HTML"):
            status, _, body = self.get(path)
            self.assertIn(status, (302, 401, 404), path)
            self.assertNotIn(b"Forecast Ledger</h1>", body, path)

    def test_data_files_and_apis_need_a_session(self):
        for path in ("/feed.json", "/rss.xml", "/email/latest.html", "/email/latest.txt",
                     "/audio/brief-developer.mp3", "/audio/script-developer.txt", "/foryou.js", "/foryou.html",
                     "/api/issue", "/api/ledger", "/api/votes?card_id=x", "/api/feed?tab=trending",
                     "/api/your5", "/api/profile", "/api/nope"):
            status, _, _ = self.get(path)
            self.assertIn(status, (302, 401), path)
        status, _, _ = self.post_json("/api/score", {"features": {}})
        self.assertEqual(status, 401)

    def test_head_gets_the_same_gate(self):
        status, r, body = self.request("HEAD", "/ledger.html")
        self.assertEqual((status, r.getheader("Location"), body), (302, "/about?next=/ledger.html#access", b""))
        status, _, _ = self.request("HEAD", "/feed.json")
        self.assertEqual(status, 401)
        status, r, body = self.request("HEAD", "/about")
        self.assertEqual((status, body), (200, b""))
        self.assertGreater(int(r.getheader("Content-Length")), 1000)

    def test_open_endpoints(self):
        status, _, body = self.get("/api/me")
        self.assertEqual((status, json.loads(body)), (200, {"user": None}))
        self.assertEqual(self.get("/api/auth/providers")[0], 200)
        self.assertEqual(self.get("/healthz")[0], 200)


class TestSignedIn(GateEnv):
    def test_everything_loads(self):
        for path in ("/", "/index.html", "/ledger", "/archive", "/patterns", "/foryou", "/feed.json",
                     "/rss.xml", "/email/latest.html", "/api/ledger"):
            status, _, _ = self.get(path, signed_in=True)
            self.assertEqual(status, 200, path)

    def test_about_marks_the_session_and_member_pages_are_not_cached(self):
        _, _, body = self.get("/about", signed_in=True)
        self.assertIn(b'data-session="in"', body)
        _, r, _ = self.get("/ledger", signed_in=True)
        self.assertEqual(r.getheader("Cache-Control"), "private, no-store")
        self.assertEqual(len(r.headers.get_all("Cache-Control")), 1)
        _, r, _ = self.get("/api/ledger", signed_in=True)
        self.assertIsNone(r.getheader("Access-Control-Allow-Origin"))

    def test_still_no_directory_listing(self):
        status, _, body = self.get("/audio/", signed_in=True)
        self.assertEqual(status, 404)
        self.assertNotIn(b"brief-developer.mp3", body)

    def test_api_me(self):
        status, _, body = self.get("/api/me", signed_in=True)
        self.assertEqual((status, json.loads(body)["user"]["username"]), (200, "gate_reader"))

    def test_odd_event_payloads_are_cleaned_not_crashed(self):
        events = [{"kind": "more_topic", "topic": ["AI"]}, {"kind": "mute_source", "publisher": {"x": 1}},
                  {"kind": "search", "query": 42}, {"kind": "dwell", "value": "NaN"}, "nope", {"kind": 5},
                  {"kind": "less_topic", "topic": "AI"}]
        status, _, body = self.post_json("/api/events", {"events": events}, signed_in=True)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["recorded"], 5)

    def test_follow_seen_with_non_text_key(self):
        status, _, _ = self.post_json("/api/follows", {"action": "seen", "kind": ["entity"], "key": {"a": 1}},
                                      signed_in=True)
        self.assertEqual(status, 200)


class TestRequestHardening(GateEnv):
    def test_negative_or_bad_content_length(self):
        for length in ("-1", "abc"):
            status, _, body = self.request("POST", "/api/auth/login", b"{}",
                                           {"Content-Type": "application/json", "Content-Length": length})
            self.assertEqual(status, 400, length)
            self.assertIn(b"Content-Length", body)

    def test_body_must_be_a_json_object(self):
        for raw in (b"[]", b'"x"', b"3"):
            status, _, _ = self.post_json("/api/auth/login", None, raw=raw)
            self.assertEqual(status, 400, raw)

    def test_non_text_credentials(self):
        status, _, body = self.post_json("/api/auth/login", {"username": ["a"], "password": "x" * 9})
        self.assertEqual(status, 400)
        self.assertIn("text", json.loads(body)["error"])
        with self.assertRaises(auth.AuthError):
            auth.create_user(123, "long enough pw", db_path=self.db)
        with self.assertRaises(auth.AuthError):
            auth.authenticate("gate_reader", None, db_path=self.db)

    def test_form_posts_still_refused(self):
        status, _, _ = self.request("POST", "/api/auth/login", b"username=a&password=b",
                                    {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(status, 400)

    def test_non_ascii_oauth_state_is_a_clean_refusal(self):
        keys = {"PITH_GITHUB_CLIENT_ID": "id", "PITH_GITHUB_CLIENT_SECRET": "secret"}
        with mock.patch.dict(os.environ, keys):
            status, r, _ = self.request("GET", "/api/auth/oauth/github/callback?code=c&state=%C3%A9",
                                        headers={"Cookie": "pith_oauth_state=%C3%A9x"})
        self.assertEqual(status, 302)
        self.assertTrue(r.getheader("Location").startswith("/about?auth_error="))

    def test_redirect_strips_control_characters(self):
        handler = server.BriefHTTPRequestHandler.__new__(server.BriefHTTPRequestHandler)
        sent = []
        handler.send_response = lambda code: sent.append(("status", code))
        handler.send_header = lambda k, v: sent.append((k, v))
        handler.end_headers = lambda: None
        handler._redirect("/x\r\nSet-Cookie: evil=1")
        self.assertIn(("Location", "/xSet-Cookie: evil=1"), sent)


class TestHelpers(unittest.TestCase):
    def test_normalise_path(self):
        cases = {"": "/", "/": "/", "/About/": "/about", "/l%65dger.html": "/ledger.html",
                 "/a/../b": "/b", "//index.html": "/index.html", "/./x/.": "/x", "/../../etc/passwd": "/etc/passwd"}
        for raw, want in cases.items():
            self.assertEqual(server.normalise_path(raw), want, raw)

    def test_clean_event(self):
        self.assertIsNone(server.clean_event({"kind": 3}))
        self.assertIsNone(server.clean_event(["click"]))
        ev = server.clean_event({"kind": "click", "article_id": "a", "topic": ["x"], "value": float("inf"),
                                 "local_hour": 9, "extra": "dropped", "query": "q" * 500})
        self.assertEqual(ev, {"kind": "click", "article_id": "a", "local_hour": 9, "query": "q" * 300})

    def test_rate_limiter_forgets_idle_keys(self):
        rl = RateLimiter(max_hits=1, window_seconds=10)
        for i in range(10_001):
            rl.allow(f"ip-{i}", now=0.0)
        rl.allow("fresh", now=100.0)
        self.assertLessEqual(len(rl._hits), 2)
        self.assertFalse(rl.allow("fresh", now=100.5))


class TestFeedFetchPinning(unittest.TestCase):
    def test_dns_answer_that_changes_after_the_check_is_refused(self):
        answers = iter(["93.184.216.34", "127.0.0.1"])

        def flip(host, port, *a, **k):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(answers), port))]
        with mock.patch.object(userfeeds.socket, "getaddrinfo", flip):
            with self.assertRaises(userfeeds.FeedError):
                userfeeds.safe_fetch("http://rebind.example/feed.xml")

    def test_entity_declarations_anywhere_are_refused(self):
        from core.newsfeed import parse_feed
        import xml.etree.ElementTree as ET
        bomb = b"<?xml version='1.0'?>" + b" " * 5000 + b"<!DOCTYPE r [<!ENTITY a 'x'>]><rss><channel></channel></rss>"
        with self.assertRaises(ET.ParseError):
            parse_feed(bomb, {"id": "f", "publisher": "p", "topic": None, "url": "https://x"})

    def test_only_web_links_are_kept(self):
        from core.newsfeed import parse_feed
        xml = (b"<rss><channel><item><title>Ok</title><link>https://ok.example/a</link></item>"
               b"<item><title>Bad</title><link>httpjavascript:alert(1)</link></item></channel></rss>")
        items = parse_feed(xml, {"id": "f", "publisher": "p", "topic": None, "url": "https://x"})
        self.assertEqual([i["title"] for i in items], ["Ok"])


if __name__ == "__main__":
    unittest.main()
