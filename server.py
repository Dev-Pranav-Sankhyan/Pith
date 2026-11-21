"""
Lightweight Python HTTP server and API for Daily Tech Intelligence Brief.
Provides static file serving and JSON APIs for the app and scoring engine.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from core.db import Database
from core.ledger import LedgerEngine
from core.scoring import ScoringEngine
from core import auth, newsfeed
from core.recommender import Recommender
from core.demo_news import seed_demo
import threading
import time


PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
FOR_YOU_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), newsfeed.FOR_YOU_DB)
REFRESH_MINUTES = int(os.environ.get("PITH_REFRESH_MINUTES", 30))
SECURE_COOKIES = os.environ.get("PITH_SECURE_COOKIES") == "1"
MAX_BODY = 64 * 1024
recommender = Recommender(FOR_YOU_DB)


class BriefHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower().rstrip("/")
        if not path:
            path = "/"
        user_agent = self.headers.get("User-Agent", "").lower()
        is_terminal = any(tool in user_agent for tool in ("curl", "wget", "httpie"))

        if path.startswith("/api/") and path.split("/")[2] in ("me", "feed", "profile"):
            return self._handle_foryou_get(path, parsed)
        elif path == "/api/issue":
            self._handle_api_issue()
            return
        elif path == "/api/ledger":
            self._handle_api_ledger()
            return

        # Always serve static assets (.css, .js, .png, .svg, etc.)
        if any(path.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".mp3", ".json", ".xml", ".woff2", ".txt")):
            return super().do_GET()

        # Public About & Login Gate Page (Always accessible)
        if path in ("/about", "/about.html"):
            self.path = "/about.html"
            return super().do_GET()

        # Decommissioned pages redirect to /
        if path in ("/horizon", "/bounty", "/matrix", "/economics", "/terminal"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        # Authentication Gate: Visiting internal site pages requires login
        user = self._current_user()
        if not user:
            self.send_response(302)
            self.send_header("Location", "/about.html")
            self.end_headers()
            return

        # Authenticated Member Routes
        if path in ("/", "/index.html", "/index"):
            self.path = "/index.html"
            return super().do_GET()
        elif path in ("/foryou", "/for-you", "/login", "/foryou.html"):
            self.path = "/foryou.html"
            return super().do_GET()
        elif path in ("/ledger", "/ledger.html"):
            self.path = "/ledger.html"
            return super().do_GET()
        elif path in ("/patterns", "/patterns.html"):
            self.path = "/patterns.html"
            return super().do_GET()
        elif path in ("/archive", "/archive.html"):
            self.path = "/archive.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def _send_text(self, text: str, status: int = 200):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/score":
            self._handle_api_score()
        elif parsed.path.startswith(("/api/auth/", "/api/events", "/api/onboard", "/api/profile/", "/api/refresh")):
            self._handle_foryou_post(parsed.path)
        else:
            self.send_error(404, "Endpoint not found")

    # ------------------------------------------------------------------ For You (personalised feed)
    def _session_token(self):
        return auth.parse_cookie(self.headers.get("Cookie"))

    def _current_user(self):
        return auth.user_for_token(self._session_token(), FOR_YOU_DB)

    def _json(self, data, status: int = 200, cookie: str = None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        # Requiring a JSON content type blocks cross-site <form> posts (CSRF) on top of SameSite cookies.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw) if raw else {}

    def _handle_foryou_get(self, path: str, parsed):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        user = self._current_user()
        if path == "/api/me":
            return self._json({"user": user, "articles": newsfeed.article_count(FOR_YOU_DB)})
        tab = q.get("tab", "foryou")
        if not user and not (path == "/api/feed" and tab == "trending"):
            return self._json({"error": "Login required"}, 401)
        try:
            hour = int(q["hour"]) if "hour" in q else None
            limit = max(1, min(int(q.get("limit", 30)), 60))
        except ValueError:
            return self._json({"error": "Bad query parameter"}, 400)
        exclude = [x for x in q.get("exclude", "").split(",") if x][:500]

        if path == "/api/profile":
            return self._json(recommender.profile(user["id"]))
        if path == "/api/feed":
            if tab == "trending":
                items = recommender.trending(user["id"] if user else None, limit, exclude)
            elif tab in ("saved", "history"):
                items = recommender.library(user["id"], tab)
            elif tab == "search":
                items = recommender.search(user["id"], q.get("q", ""), limit)
            else:
                items = recommender.rank(user["id"], limit, exclude, hour, topic=q.get("topic") or None)
            return self._json({"tab": tab, "items": items})
        return self._json({"error": "Not found"}, 404)

    def _handle_foryou_post(self, path: str):
        try:
            data = self._read_json_body()
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"error": str(e)}, 400)

        if path in ("/api/auth/signup", "/api/auth/login"):
            try:
                if path.endswith("signup"):
                    uid = auth.create_user(data.get("username", ""), data.get("password", ""),
                                           data.get("display_name", ""), FOR_YOU_DB)
                else:
                    uid = auth.authenticate(data.get("username", ""), data.get("password", ""), FOR_YOU_DB)
            except auth.AuthError as e:
                return self._json({"error": str(e)}, 400)
            token = auth.create_session(uid, FOR_YOU_DB)
            return self._json({"user": auth.user_for_token(token, FOR_YOU_DB)},
                              cookie=auth.session_cookie(token, SECURE_COOKIES))
        if path == "/api/auth/logout":
            auth.destroy_session(self._session_token(), FOR_YOU_DB)
            return self._json({"ok": True}, cookie=auth.clear_cookie())

        user = self._current_user()
        if not user:
            return self._json({"error": "Login required"}, 401)
        uid = user["id"]
        if path == "/api/onboard":
            recommender.onboard(uid, data.get("topics") or [], data.get("sources") or [])
            return self._json({"ok": True})
        if path == "/api/events":
            events = data.get("events") if isinstance(data.get("events"), list) else [data]
            for ev in events[:200]:
                if isinstance(ev, dict) and isinstance(ev.get("kind"), str):
                    recommender.record(uid, ev)
            return self._json({"ok": True, "recorded": min(len(events), 200)})
        if path == "/api/profile/reset":
            recommender.reset(uid)
            return self._json({"ok": True})
        if path == "/api/refresh":
            report = newsfeed.refresh_all(FOR_YOU_DB)
            return self._json(report)
        return self._json({"error": "Not found"}, 404)

    def _handle_api_issue(self):
        db = Database("brief.sqlite3")
        issue = db.get_latest_issue()
        if not issue:
            self.send_error(404, "No issue found")
            return
        self._send_json(issue.to_dict())

    def _handle_api_ledger(self):
        db = Database("brief.sqlite3")
        preds = db.get_all_predictions()
        stats = LedgerEngine.calculate_statistics(preds)
        self._send_json({
            "stats": stats,
            "predictions": [p.__dict__ for p in preds]
        })

    def _handle_api_score(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            features = data.get("features") or {}
            penalties = data.get("penalties") or {}
            engine = ScoringEngine()
            score, level, reason, breakdown = engine.compute_score(features, penalties)
            self._send_json({
                "score": score,
                "signal_level": level,
                "reason": reason,
                "is_selected": engine.is_selected(score),
                "breakdown": breakdown
            })
        except Exception as e:
            self.send_error(400, f"Error processing score request: {str(e)}")

    def _send_json(self, data: dict):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)


def _news_refresher():
    """Background loop: pull fresh RSS on boot and every REFRESH_MINUTES; demo-seed if offline."""
    while True:
        try:
            report = newsfeed.refresh_all(FOR_YOU_DB)
            print(f"[for-you] refreshed feeds: {report['ok']} ok, {report['failed']} failed, {report['inserted']} new articles")
            if newsfeed.article_count(FOR_YOU_DB) == 0:
                n = seed_demo(FOR_YOU_DB)
                print(f"[for-you] no live feeds reachable — seeded {n} offline demo articles")
            newsfeed.prune_old(FOR_YOU_DB)
        except Exception as e:  # keep the loop alive no matter what
            print(f"[for-you] refresh error: {e}")
        time.sleep(REFRESH_MINUTES * 60)


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server():
    newsfeed.init_schema(FOR_YOU_DB)
    threading.Thread(target=_news_refresher, daemon=True).start()
    for port in range(PORT, PORT + 20):
        try:
            httpd = ThreadingServer(("", port), BriefHTTPRequestHandler)
            print(f"Pith server running at http://localhost:{port}")
            try:
                httpd.serve_forever()
            finally:
                httpd.server_close()
            return
        except OSError as e:
            if e.errno == 48:  # Address already in use
                continue
            raise e
    print(f"Could not bind to any port between {PORT} and {PORT + 19}.")


if __name__ == "__main__":
    run_server()
