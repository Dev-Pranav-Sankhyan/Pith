"""
Lightweight Python HTTP server and API for Daily Tech Intelligence Brief.
Provides static file serving and JSON APIs for the app and scoring engine.
"""

import http.server
import socketserver
import json
import os
import re
import urllib.parse
from core.db import Database
from core.ledger import LedgerEngine
from core.scoring import ScoringEngine
from core import auth, newsfeed
from core.recommender import Recommender
from core.your5 import Your5Engine
from core.demo_news import seed_demo
from core import votes
from core import follows as follows_mod, personal_audio, personal_forecasts, prefs as prefs_mod, userfeeds
from core import oauth, social_signals
from core.ratelimit import RateLimiter
import threading
import time


PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
FOR_YOU_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), newsfeed.FOR_YOU_DB)
REFRESH_MINUTES = int(os.environ.get("PITH_REFRESH_MINUTES", 30))
SECURE_COOKIES = os.environ.get("PITH_SECURE_COOKIES") == "1"
MAX_BODY = 64 * 1024
recommender = Recommender(FOR_YOU_DB)
AUTH_LIMITER = RateLimiter(max_hits=10, window_seconds=300)     # login/signup attempts per IP
WRITE_LIMITER = RateLimiter(max_hits=120, window_seconds=60)    # other POSTs per IP
REFRESH_LIMITER = RateLimiter(max_hits=2, window_seconds=600)   # manual feed refreshes per IP
FEED_ADD_LIMITER = RateLimiter(max_hits=10, window_seconds=3600)  # reader-added feed fetches per IP
AUDIO_LIMITER = RateLimiter(max_hits=3, window_seconds=86400)    # studio-voice renders per reader per day
FORYOU_GET_ROOTS = ("me", "feed", "profile", "your5", "digest", "follows", "forecasts", "prefs", "onboard", "feeds")
FORYOU_POST_PREFIXES = ("/api/auth/", "/api/events", "/api/onboard", "/api/profile/", "/api/refresh", "/api/vote",
                        "/api/follows", "/api/forecasts/", "/api/prefs", "/api/your5/", "/api/feeds", "/api/connections")
OAUTH_PATH = re.compile(r"^/api/auth/oauth/(google|github|x|linkedin)/(start|callback)$")
_HOST_SAFE = re.compile(r"^[A-Za-z0-9.\-]+(:\d{1,5})?$|^\[[0-9a-fA-F:]+\](:\d{1,5})?$")

# Pages anyone can read. For You is served to everyone too, but logged out it only shows its
# sign-in screen: every personal API below refuses requests without a session.
PUBLIC_PAGES = {
    "/": "/index.html", "/index": "/index.html", "/index.html": "/index.html",
    "/ledger": "/ledger.html", "/ledger.html": "/ledger.html",
    "/archive": "/archive.html", "/archive.html": "/archive.html",
    "/patterns": "/patterns.html", "/patterns.html": "/patterns.html",
    "/about": "/about.html", "/about.html": "/about.html",
}
MEMBER_PAGES = {"/foryou", "/for-you", "/login", "/foryou.html"}


class BriefHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def list_directory(self, path):
        # Never expose directory listings (e.g. /audio/).
        self.send_error(404, "Not found")
        return None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower().rstrip("/")
        if not path:
            path = "/"
        if path == "/healthz":
            return self._json({"ok": True})
        if path == "/api/votes":
            q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            card_id = q.get("card_id", "")
            if not card_id:
                return self._json({"error": "card_id required"}, 400)
            return self._json({"card_id": card_id, "counts": votes.counts(card_id, FOR_YOU_DB)})

        if path == "/api/auth/providers":
            return self._json({"providers": oauth.provider_list()})
        m = OAUTH_PATH.match(path)
        if m:
            return self._handle_oauth(m.group(1), m.group(2), parsed)

        if path.startswith("/api/") and path.split("/")[2] in FORYOU_GET_ROOTS:
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

        # Decommissioned pages redirect to /
        if path in ("/horizon", "/bounty", "/matrix", "/economics", "/terminal"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        if path in PUBLIC_PAGES:
            self.path = PUBLIC_PAGES[path]
            return super().do_GET()

        if path in MEMBER_PAGES:
            self.path = "/foryou.html"
            return super().do_GET()

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
        if not WRITE_LIMITER.allow(self._client_ip()):
            return self._json({"error": "Too many requests"}, 429)
        if parsed.path == "/api/score":
            self._handle_api_score()
        elif parsed.path.startswith(FORYOU_POST_PREFIXES):
            self._handle_foryou_post(parsed.path)
        else:
            self.send_error(404, "Endpoint not found")

    # ------------------------------------------------------------------ For You (personalised feed)
    def _client_ip(self) -> str:
        return self.client_address[0] if self.client_address else "unknown"

    def _session_token(self):
        return auth.parse_cookie(self.headers.get("Cookie"))

    def _request_base(self) -> str:
        """This server's own origin, for OAuth redirect URIs when PITH_AUTH_BASE_URL is unset."""
        proto = (self.headers.get("X-Forwarded-Proto") or ("https" if SECURE_COOKIES else "http")).split(",")[0].strip()
        host = (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "").split(",")[0].strip()
        if proto not in ("http", "https"):
            proto = "http"
        if not _HOST_SAFE.match(host):
            host = f"localhost:{self.server.server_address[1]}"
        return f"{proto}://{host}"

    def _redirect(self, location: str, cookies=()):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        for c in cookies:
            self.send_header("Set-Cookie", c)
        self.end_headers()

    def _handle_oauth(self, provider: str, step: str, parsed):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

        def fail(message: str):
            return self._redirect("/foryou?auth_error=" + urllib.parse.quote(message),
                                  [oauth.clear_state_cookie()])

        if not AUTH_LIMITER.allow(self._client_ip()):
            return fail("Too many sign-in attempts. Try again in a few minutes.")
        base = self._request_base()
        if step == "start":
            user = self._current_user()
            link = user["id"] if user and q.get("link") == "1" else None
            try:
                url, state = oauth.start(provider, base, q.get("next"), link, FOR_YOU_DB)
            except oauth.OAuthError as e:
                return fail(str(e))
            return self._redirect(url, [oauth.state_cookie(state, SECURE_COOKIES)])

        name = oauth.PROVIDERS[provider].name
        if q.get("error"):
            return fail(f"{name} sign-in was cancelled.")
        try:
            result = oauth.complete(provider, q.get("code", ""), q.get("state", ""),
                                    oauth.parse_state_cookie(self.headers.get("Cookie")), base, FOR_YOU_DB)
            current = self._current_user()
            link = result["link_user_id"] if current and current["id"] == result["link_user_id"] else None
            uid, _created = oauth.sign_in(result["profile"], link, FOR_YOU_DB)
        except oauth.OAuthError as e:
            return fail(str(e))
        try:
            social_signals.sync(uid, result["profile"], FOR_YOU_DB)
        except Exception as e:  # personalisation is a bonus; never block the sign-in on it
            print(f"[auth] couldn't import {provider} interests for user {uid}: {e}")
        cookies = [oauth.clear_state_cookie()]
        if not link:
            cookies.append(auth.session_cookie(auth.create_session(uid, FOR_YOU_DB), SECURE_COOKIES))
        target = result["next"]
        target += ("&" if "?" in target else "?") + "connected=" + provider
        return self._redirect(target, cookies)

    def _personal_brief(self, user, hour):
        """Today's spoken brief for this reader: chapters, the joined script and its MP3 path."""
        your5 = Your5Engine().get_your_5(user["id"], hour)
        return personal_audio.personal_brief(user, hour, your5, recommender, FOR_YOU_DB)

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
            if user:
                user = dict(user, avatar_url=oauth.avatar_for(user["id"], FOR_YOU_DB),
                            providers=[i["provider"] for i in oauth.identities(user["id"], FOR_YOU_DB)])
            return self._json({"user": user, "articles": newsfeed.article_count(FOR_YOU_DB)})
        hour = None
        if q.get("hour", "").lstrip("-").isdigit():
            hour = int(q["hour"]) % 24
        if path == "/api/your5":
            engine = Your5Engine()
            return self._json(engine.get_your_5(user["id"] if user else None, hour))
        if path == "/api/digest":
            if not user:
                return self._json({"error": "Login required"}, 401)
            engine = Your5Engine()
            return self._json(engine.get_weekly_digest(user["id"]))
        tab = q.get("tab", "foryou")
        if not user and not (path == "/api/feed" and tab == "trending"):
            return self._json({"error": "Login required"}, 401)
        try:
            limit = max(1, min(int(q.get("limit", 30)), 60))
        except ValueError:
            return self._json({"error": "Bad query parameter"}, 400)
        exclude = [x for x in q.get("exclude", "").split(",") if x][:500]

        uid = user["id"] if user else None  # only the public Trending tab gets here without a user
        if path == "/api/profile":
            prof = recommender.profile(uid)
            prof.update({
                "prefs": prefs_mod.get_prefs(uid, FOR_YOU_DB),
                "depth": prefs_mod.effective_depth(uid, FOR_YOU_DB),
                "follows": [{k: f[k] for k in ("kind", "key", "label")} for f in follows_mod.list_follows(uid, FOR_YOU_DB)],
                "feeds": userfeeds.list_feeds(uid, FOR_YOU_DB),
                "regions": list(prefs_mod.REGIONS),
                "depths": list(prefs_mod.DEPTHS),
                "connections": social_signals.connections(uid, FOR_YOU_DB),
                "imported_topics": social_signals.imported_topics(uid, FOR_YOU_DB),
            })
            return self._json(prof)
        if path == "/api/your5/script":
            segments, script, depth = self._personal_brief(user, hour)
            return self._json({"script": script, "segments": segments, "chapters": personal_audio.chapters(segments),
                               "depth": depth, **personal_audio.script_stats(script),
                               "studio_voice": personal_audio.studio_voice_available(),
                               "studio_audio_ready": os.path.exists(personal_audio.audio_path(uid, script))})
        if path == "/api/your5/audio.mp3":
            _, script, _ = self._personal_brief(user, hour)
            current = personal_audio.audio_path(uid, script)
            return self._send_private_audio(current if os.path.exists(current) else personal_audio.latest_audio(uid))
        if path == "/api/follows":
            return self._json({"follows": [{k: f[k] for k in ("kind", "key", "label", "created_at")}
                                           for f in follows_mod.list_follows(uid, FOR_YOU_DB)],
                               "updates": recommender.following(uid, limit)})
        if path == "/api/forecasts/me":
            return self._json(personal_forecasts.forecast_record(uid, FOR_YOU_DB))
        if path == "/api/prefs":
            return self._json({"prefs": prefs_mod.get_prefs(uid, FOR_YOU_DB),
                               "depth": prefs_mod.effective_depth(uid, FOR_YOU_DB)})
        if path == "/api/onboard/pairs":
            return self._json({"pairs": recommender.onboarding_pairs()})
        if path == "/api/feeds":
            return self._json({"feeds": userfeeds.list_feeds(uid, FOR_YOU_DB),
                               "max": userfeeds.MAX_FEEDS_PER_USER})
        if path == "/api/feed":
            if tab == "following":
                items = recommender.following(uid, limit)
            elif tab == "trending":
                items = recommender.trending(uid, limit, exclude)
            elif tab in ("saved", "history"):
                items = recommender.library(uid, tab)
            elif tab == "search":
                items = recommender.search(uid, q.get("q", ""), limit)
            else:
                items = recommender.rank(uid, limit, exclude, hour, topic=q.get("topic") or None)
            return self._json({"tab": tab, "items": items})
        return self._json({"error": "Not found"}, 404)

    def _handle_foryou_post(self, path: str):
        try:
            data = self._read_json_body()
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"error": str(e)}, 400)

        if path in ("/api/auth/signup", "/api/auth/login"):
            if not AUTH_LIMITER.allow(self._client_ip()):
                return self._json({"error": "Too many attempts. Try again in a few minutes."}, 429)
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
            choices = data.get("choices") if isinstance(data.get("choices"), list) else []
            recommender.onboard(uid, data.get("topics") or [], data.get("sources") or [], choices)
            return self._json({"ok": True})
        if path == "/api/follows":
            action, kind = data.get("action"), data.get("kind")
            try:
                if action == "follow":
                    result = recommender.follow(uid, str(kind or ""), str(data.get("key") or ""),
                                                data.get("label"), data.get("article_id"))
                    return self._json({"ok": True, "follow": result})
                if action == "unfollow":
                    return self._json({"ok": follows_mod.unfollow(uid, str(kind or ""), str(data.get("key") or ""), FOR_YOU_DB)})
                if action == "seen":
                    follows_mod.mark_seen(uid, kind, data.get("key"), FOR_YOU_DB)
                    return self._json({"ok": True})
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            return self._json({"error": "action must be follow, unfollow or seen"}, 400)
        if path == "/api/forecasts/seen":
            personal_forecasts.mark_seen(uid, FOR_YOU_DB)
            return self._json({"ok": True})
        if path == "/api/prefs":
            try:
                return self._json({"prefs": prefs_mod.set_prefs(uid, data, FOR_YOU_DB),
                                   "depth": prefs_mod.effective_depth(uid, FOR_YOU_DB)})
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
        if path == "/api/feeds":
            try:
                if data.get("action") == "add":
                    if not FEED_ADD_LIMITER.allow(self._client_ip()):
                        return self._json({"error": "Too many feeds added recently. Try again later."}, 429)
                    return self._json({"ok": True, "feed": userfeeds.add_feed(uid, str(data.get("url") or ""), FOR_YOU_DB)})
                if data.get("action") == "remove":
                    return self._json({"ok": userfeeds.remove_feed(uid, str(data.get("feed_id") or ""), FOR_YOU_DB)})
            except userfeeds.FeedError as e:
                return self._json({"error": str(e)}, 400)
            return self._json({"error": "action must be add or remove"}, 400)
        if path == "/api/connections":
            provider = str(data.get("provider") or "")
            try:
                if data.get("action") == "disconnect":
                    oauth.disconnect(uid, provider, FOR_YOU_DB)
                    social_signals.forget(uid, provider, FOR_YOU_DB)
                elif data.get("action") == "forget":
                    social_signals.forget(uid, provider, FOR_YOU_DB)
                else:
                    return self._json({"error": "action must be forget or disconnect"}, 400)
            except oauth.OAuthError as e:
                return self._json({"error": str(e)}, 400)
            return self._json({"ok": True, "connections": social_signals.connections(uid, FOR_YOU_DB)})
        if path == "/api/your5/audio":
            if not personal_audio.studio_voice_available():
                return self._json({"error": "The studio voice isn't configured on this server. Use the browser voice."}, 503)
            hour = data.get("hour") if isinstance(data.get("hour"), int) else None
            _, script, _ = self._personal_brief(user, None if hour is None else hour % 24)
            cached = os.path.exists(personal_audio.audio_path(uid, script))
            if not cached and not AUDIO_LIMITER.allow(f"user:{uid}"):
                return self._json({"error": "You've used today's studio renders. The browser voice still works."}, 429)
            path_mp3 = personal_audio.render_studio_audio(uid, script)
            if not path_mp3:
                return self._json({"error": "The studio voice couldn't render this brief right now."}, 502)
            return self._json({"ok": True, "url": "/api/your5/audio.mp3" + ("" if hour is None else f"?hour={hour % 24}")})
        if path == "/api/events":
            events = data.get("events") if isinstance(data.get("events"), list) else [data]
            for ev in events[:200]:
                if isinstance(ev, dict) and isinstance(ev.get("kind"), str):
                    recommender.record(uid, ev)
            return self._json({"ok": True, "recorded": min(len(events), 200)})
        if path == "/api/profile/reset":
            recommender.reset(uid)
            return self._json({"ok": True})
        if path == "/api/vote":
            allowed, why = personal_forecasts.vote_allowed(str(data.get("card_id", "")))
            if not allowed:
                return self._json({"error": why}, 400)
            try:
                votes.cast_vote(uid, str(data.get("card_id", "")), str(data.get("vote", "")), FOR_YOU_DB)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            card_id = str(data.get("card_id"))
            return self._json({"ok": True, "card_id": card_id, "counts": votes.counts(card_id, FOR_YOU_DB)})
        if path == "/api/refresh":
            if not REFRESH_LIMITER.allow(self._client_ip()):
                return self._json({"error": "Refresh already ran recently"}, 429)
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
            data = self._read_json_body()
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
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            self._json({"error": f"Bad score request: {e}"}, 400)

    def _send_private_audio(self, file_path):
        """Streams a reader's own studio-voice MP3. Never cached by shared caches."""
        if not file_path or not os.path.isfile(file_path):
            return self._json({"error": "No studio audio for today yet"}, 404)
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, no-store")
        self.end_headers()
        self.wfile.write(data)

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
            custom = userfeeds.refresh_custom(FOR_YOU_DB)
            if custom["ok"] or custom["failed"]:
                print(f"[for-you] reader feeds: {custom['ok']} ok, {custom['failed']} failed, {custom['inserted']} new")
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
