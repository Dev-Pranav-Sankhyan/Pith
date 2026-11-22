"""
Step 9: admin access.
  * rights live in the `admins` table and are granted only from the shell (core.admin CLI);
    no HTTP route can grant them
  * /admin, /admin.html, /admin.js and /api/admin/* are admin-only: signed out -> About / 401,
    signed in without rights -> 403
  * the overview lists readers (never password hashes) and live forecasts only
  * an admin verdict goes through Database.record_resolution, signed with the admin's name;
    illustrative examples, forecasts that already have a verdict, missing or non-web evidence
    and non-JSON posts are refused
Run: python3 -m unittest tests.test_step9
"""

import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import server
from core import admin, auth
from core.brief_bridge import BRIEF
from core.db import Database
from core.models import Prediction
from core.newsfeed import connect, init_schema
from core.ratelimit import RateLimiter
from core.recommender import CORPUS, Recommender
from pipeline.render_extended import get_nav_html


def _pred(pid, resolves, provenance="live"):
    return Prediction(id=pid, statement=f"Statement {pid}", probability=0.7, made_at="2026-01-01",
                      resolves_at=resolves, resolution_criteria="Official docs say so.", provenance=provenance)


class TestAdminRights(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "foryou.sqlite3")
        init_schema(self.db)
        self.uid = auth.create_user("reader_one", "correct horse battery", "", self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_grant_and_revoke(self):
        self.assertFalse(admin.is_admin(self.uid, self.db))
        admin.grant("READER_ONE", self.db)  # usernames are case-insensitive
        admin.grant("reader_one", self.db)  # idempotent
        self.assertTrue(admin.is_admin(self.uid, self.db))
        self.assertEqual([a["username"] for a in admin.list_admins(self.db)], ["reader_one"])
        self.assertTrue(admin.revoke("reader_one", self.db))
        self.assertFalse(admin.revoke("reader_one", self.db))
        self.assertFalse(admin.is_admin(self.uid, self.db))
        self.assertFalse(admin.is_admin(None, self.db))

    def test_unknown_account_is_refused(self):
        with self.assertRaises(admin.AdminError):
            admin.grant("nobody", self.db)

    def test_create_follows_sign_up_rules(self):
        with self.assertRaises(auth.AuthError):
            admin.create("boss", "short", "", self.db)
        self.assertEqual(admin.list_admins(self.db), [])
        uid = admin.create("boss", "a long enough password", "The Boss", self.db)
        self.assertTrue(admin.is_admin(uid, self.db))
        self.assertEqual(auth.authenticate("boss", "a long enough password", self.db), uid)

    def test_deleting_the_account_drops_the_right(self):
        admin.grant("reader_one", self.db)
        with connect(self.db) as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (self.uid,))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0], 0)

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch("sys.stdin", io.StringIO("cli password 123\n")):
            self.assertEqual(admin.main(["--db", self.db, "create", "cli_admin", "--password-stdin"]), 0)
            self.assertEqual(admin.main(["--db", self.db, "list"]), 0)
            self.assertEqual(admin.main(["--db", self.db, "grant", "ghost"]), 1)
            self.assertEqual(admin.main(["--db", self.db, "revoke", "cli_admin"]), 0)
        self.assertIn("cli_admin", out.getvalue())
        self.assertIn("Refused", err.getvalue())
        self.assertEqual(admin.list_admins(self.db), [])
        self.assertEqual(auth.authenticate("cli_admin", "cli password 123", self.db) > 0, True)

    def test_nav_link_is_hidden_until_app_js_reveals_it(self):
        nav = get_nav_html("index.html")
        self.assertIn('href="admin.html" class="nav-link" data-members data-admin hidden', nav)


class AdminEnv(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "foryou.sqlite3")
        cls.brief = os.path.join(cls.tmp.name, "brief.sqlite3")
        init_schema(cls.db)
        bdb = Database(cls.brief)
        for p in (_pred("due-live", "2026-02-01"), _pred("later-live", "2099-01-01"),
                  _pred("hist-pred-x", "2026-02-01", provenance="illustrative"),
                  _pred("due-live-2", "2026-03-01")):
            bdb.save_prediction(p)
        cls.rerender = mock.MagicMock()
        cls.patches = [mock.patch.object(server, "FOR_YOU_DB", cls.db),
                       mock.patch.object(server, "BRIEF_DB", cls.brief),
                       mock.patch.object(server, "recommender", Recommender(cls.db)),
                       mock.patch.object(server, "WRITE_LIMITER", RateLimiter(max_hits=1000, window_seconds=60)),
                       mock.patch.object(server, "_rerender_site", cls.rerender)]
        for p in cls.patches:
            p.start()
        CORPUS._sig = None
        BRIEF._sig = None
        reader = auth.create_user("plain_reader", "correct horse battery", "Plain Reader", cls.db)
        boss = admin.create("desk_admin", "another long password", "Desk Admin", cls.db)
        cls.tokens = {"reader": auth.create_session(reader, cls.db), "admin": auth.create_session(boss, cls.db)}
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

    def request(self, method, path, body=None, headers=None, who=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = dict(headers or {})
        if who:
            headers["Cookie"] = f"{auth.COOKIE_NAME}={self.tokens[who]}"
        if body is not None:
            headers.setdefault("Content-Length", str(len(body)))
        conn.request(method, path, body, headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        return r.status, r, data

    def resolve(self, payload, who="admin", ctype="application/json"):
        return self.request("POST", "/api/admin/resolve", json.dumps(payload).encode(),
                            {"Content-Type": ctype}, who)


class TestAdminGate(AdminEnv):
    def test_signed_out(self):
        status, r, _ = self.request("GET", "/admin")
        self.assertEqual((status, r.getheader("Location")), (302, "/about?next=/admin#access"))
        for path in ("/admin.js", "/api/admin/overview"):
            self.assertEqual(self.request("GET", path)[0], 401, path)
        self.assertEqual(self.resolve({"prediction_id": "due-live", "status": "void"}, who=None)[0], 401)

    def test_reader_without_rights(self):
        for path in ("/admin", "/admin.html", "/ADMIN", "/admin/", "/%61dmin.js", "/api/admin/overview"):
            status, _, body = self.request("GET", path, who="reader")
            self.assertEqual(status, 403, path)
            self.assertNotIn(b"Admin desk", body)
        self.assertEqual(self.request("HEAD", "/admin.js", who="reader")[0], 403)
        self.assertEqual(self.resolve({"prediction_id": "due-live", "status": "void"}, who="reader")[0], 403)
        me = json.loads(self.request("GET", "/api/me", who="reader")[2])
        self.assertFalse(me["user"]["is_admin"])

    def test_no_route_grants_rights(self):
        for who, expected in (("reader", 403), ("admin", 404)):
            status, _, _ = self.request("POST", "/api/admin/grant", b'{"username": "plain_reader"}',
                                        {"Content-Type": "application/json"}, who)
            self.assertEqual(status, expected, who)
        self.assertFalse(admin.is_admin(auth.authenticate("plain_reader", "correct horse battery", self.db), self.db))

    def test_admin_sees_the_desk(self):
        status, r, body = self.request("GET", "/admin", who="admin")
        self.assertEqual(status, 200)
        self.assertIn(b"Admin <em>desk</em>", body)
        self.assertIn("no-store", r.getheader("Cache-Control"))
        self.assertEqual(self.request("GET", "/admin.js", who="admin")[0], 200)
        me = json.loads(self.request("GET", "/api/me", who="admin")[2])
        self.assertTrue(me["user"]["is_admin"])

    def test_overview(self):
        status, _, body = self.request("GET", "/api/admin/overview", who="admin")
        self.assertEqual(status, 200)
        self.assertNotIn(b"password", body.lower())
        data = json.loads(body)
        self.assertEqual({r["username"] for r in data["readers"]}, {"plain_reader", "desk_admin"})
        self.assertTrue(next(r for r in data["readers"] if r["username"] == "desk_admin")["is_admin"])
        self.assertGreaterEqual(data["stats"]["readers"], 2)
        fc = data["forecasts"]
        ids = {f["id"] for group in ("due", "upcoming", "recent") for f in fc[group]}
        self.assertNotIn("hist-pred-x", ids)  # illustrative examples never need a verdict
        self.assertIn("later-live", {f["id"] for f in fc["upcoming"]})
        self.assertEqual(self.request("GET", "/api/admin/nope", who="admin")[0], 404)


class TestAdminVerdicts(AdminEnv):
    def history(self, pid):
        return Database(self.brief).get_resolution_history(pid)

    def test_refusals(self):
        cases = [
            {"prediction_id": "due-live", "status": "correct"},                                  # no evidence
            {"prediction_id": "due-live", "status": "wrong", "evidence_url": "javascript:alert(1)"},
            {"prediction_id": "due-live", "status": "maybe", "evidence_url": "https://e.com/x"},
            {"prediction_id": "hist-pred-x", "status": "void"},                                  # illustrative
            {"prediction_id": "ghost", "status": "void"},
            {"prediction_id": ["due-live"], "status": "void"},
            {"prediction_id": "due-live", "status": "void", "note": 5},
        ]
        for payload in cases:
            status, _, body = self.resolve(payload)
            self.assertEqual(status, 400, payload)
            self.assertIn("error", json.loads(body))
        # The JSON content-type check is the CSRF guard: a form post is refused.
        self.assertEqual(self.resolve({"prediction_id": "due-live", "status": "void"},
                                      ctype="application/x-www-form-urlencoded")[0], 400)
        self.assertEqual(self.history("due-live"), [])

    def test_verdict_is_recorded_signed_and_final(self):
        self.rerender.reset_mock()
        status, _, body = self.resolve({"prediction_id": "due-live", "status": "correct",
                                        "evidence_url": "https://example.com/proof", "note": "  Shipped.  "})
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["resolved_by"], "Desk Admin")
        hist = self.history("due-live")
        self.assertEqual(len(hist), 1)
        self.assertEqual((hist[0]["status"], hist[0]["resolved_by"], hist[0]["evidence_url"], hist[0]["postmortem"]),
                         ("correct", "Desk Admin", "https://example.com/proof", "Shipped."))
        self.rerender.assert_called_once()
        # A second verdict from the web is refused; corrections go through the CLI.
        self.assertEqual(self.resolve({"prediction_id": "due-live", "status": "wrong",
                                       "evidence_url": "https://example.com/other"})[0], 400)
        self.assertEqual(len(self.history("due-live")), 1)
        recent = json.loads(self.request("GET", "/api/admin/overview", who="admin")[2])["forecasts"]["recent"]
        self.assertIn("due-live", {f["id"] for f in recent})

    def test_void_needs_no_evidence(self):
        status, _, body = self.resolve({"prediction_id": "due-live-2", "status": "void", "evidence_url": ""})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.history("due-live-2")[0]["evidence_url"], None)


if __name__ == "__main__":
    unittest.main()
