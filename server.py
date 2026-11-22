"""
Lightweight Python HTTP server and API for Pith.

Access model: the About page is the front door and the only page anyone can open. It carries
sign-in and account creation. Every other page, file and API (Daily News, the Ledger, the
Archive, Patterns, For You, feed.json, rss.xml, the email edition, the audio briefs) needs a
session. Requests are checked deny-by-default on the decoded, normalised path, so encodings like
/l%65dger.html or /about.html/../index.html can't slip past the gate.
"""

import errno
import http.server
import socketserver
import json
import os
import posixpath
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
from core import oauth, social_signals, admin
from core.ratelimit import RateLimiter
import threading
import time


ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(ROOT, "public")
BRIEF_DB = os.path.join(ROOT, "brief.sqlite3")
FOR_YOU_DB = os.path.join(ROOT, newsfeed.FOR_YOU_DB)
REFRESH_MINUTES = int(os.environ.get("PITH_REFRESH_MINUTES", 30))
SECURE_COOKIES = os.environ.get("PITH_SECURE_COOKIES") == "1"
MAX_BODY = 64 * 1024
recommender = Recommender(FOR_YOU_DB)
AUTH_LIMITER = RateLimiter(max_hits=10, window_seconds=300)     # login/signup attempts per IP
WRITE_LIMITER = RateLimiter(max_hits=120, window_seconds=60)    # other POSTs per IP
REFRESH_LIMITER = RateLimiter(max_hits=2, window_seconds=600)   # manual feed refreshes per IP
FEED_ADD_LIMITER = RateLimiter(max_hits=10, window_seconds=3600)  # reader-added feed fetches per IP
AUDIO_LIMITER = RateLimiter(max_hits=3, window_seconds=86400)    # studio-voice renders per reader per day
FORYOU_GET_ROOTS = ("feed", "profile", "your5", "digest", "follows", "forecasts", "prefs", "onboard", "feeds")
FORYOU_POST_PREFIXES = ("/api/events", "/api/onboard", "/api/profile/", "/api/refresh", "/api/vote",
                        "/api/follows", "/api/forecasts/", "/api/prefs", "/api/your5/", "/api/feeds", "/api/connections")
AUTH_POSTS = ("/api/auth/signup", "/api/auth/login", "/api/auth/logout")
OAUTH_PATH = re.compile(r"^/api/auth/oauth/(google|github|x|linkedin)/(start|callback)$")
_HOST_SAFE = re.compile(r"^[A-Za-z0-9.\-]+(:\d{1,5})?$|^\[[0-9a-fA-F:]+\](:\d{1,5})?$")

# Anyone may load these: the About page (with sign-in) and the shell assets it needs. Nothing in
# this list carries news content. Everything else needs a session.
ABOUT_PATHS = {"/about", "/about.html"}
OPEN_ASSETS = {"/style.css", "/app.js", "/favicon.svg", "/favicon.png", "/favicon.ico", "/apple-touch-icon.png"}
# Pretty paths for the member pages.
MEMBER_PAGES = {
    "/": "/index.html", "/index": "/index.html", "/index.html": "/index.html",
    "/ledger": "/ledger.html", "/ledger.html": "/ledger.html",
    "/archive": "/archive.html", "/archive.html": "/archive.html",
    "/patterns": "/patterns.html", "/patterns.html": "/patterns.html",
    "/foryou": "/foryou.html", "/for-you": "/foryou.html", "/foryou.html": "/foryou.html",
}
# Admin-only (core/admin.py): signed-in readers without admin rights get a 403.
ADMIN_PAGES = {"/admin": "/admin.html", "/admin.html": "/admin.html"}
ADMIN_FILES = set(ADMIN_PAGES) | {"/admin.js"}
DECOMMISSIONED = {"/horizon", "/bounty", "/matrix", "/economics", "/terminal"}
EVENT_TEXT_FIELDS = ("kind", "article_id", "topic", "query", "publisher")
EVENT_NUMBER_FIELDS = ("value", "local_hour")


def normalise_path(raw: str) -> str:
    """The path the file server would actually resolve: percent-decoded, dot segments collapsed,
    lower-cased, no trailing slash. Every access decision is made on this."""
    path = posixpath.normpath(urllib.parse.unquote(raw or "/")).lower()
    path = "/" + path.lstrip("/")
    if path in ("/.", "/"):
        return "/"
    return path.rstrip("/") or "/"


def clean_event(ev):
    """Only the known fields, and only as plain scalars, so odd client payloads can't crash the recorder."""
    if not isinstance(ev, dict) or not isinstance(ev.get("kind"), str):
        return None
    out = {}
    for k in EVENT_TEXT_FIELDS:
        if isinstance(ev.get(k), str):
            out[k] = ev[k][:300]
    for k in EVENT_NUMBER_FIELDS:
        v = ev.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf"):
            out[k] = v
    return out


class BriefHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._head_only = False
        self._cache_sent = False
        self._private = False
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_header(self, keyword, value):
        if keyword.lower() == "cache-control":
            self._cache_sent = True
        super().send_header(keyword, value)

    def end_headers(self):
        if not self._cache_sent:
            # Member content must not outlive the session in the browser cache (back button after sign-out).
            self.send_header("Cache-Control", "private, no-store" if self._private else "no-cache, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def list_directory(self, path):
        # Never expose directory listings (e.g. /audio/).
        self.send_error(404, "Not found")
        return None

    # ------------------------------------------------------------------ dispatch
    def do_GET(self):
        self._guard(self._route_get)

    def do_HEAD(self):
        # Same gate as GET, headers only.
        self._head_only = True
        self._guard(self._route_get)

    def do_POST(self):
        self._guard(self._route_post)

    def _guard(self, route):
        """Any unexpected error becomes a JSON 500 instead of a dropped connection."""
        try:
            route()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[server] {self.command} {urllib.parse.urlparse(self.path).path} failed: {type(e).__name__}: {e}")
            try:
                self._json({"error": "Something went wrong on our side."}, 500)
            except Exception:
                pass

    def _write(self, data: bytes):
        if not self._head_only:
            self.wfile.write(data)

    def _serve_static(self, path=None):
        if path is not None:
            self.path = path
        return super().do_HEAD() if self._head_only else super().do_GET()

    def _route_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = normalise_path(parsed.path)
        if path == "/healthz":
            return self._json({"ok": True})
        if path == "/api/auth/providers":
            return self._json({"providers": oauth.provider_list()})
        m = OAUTH_PATH.match(path)
        if m:
            return self._handle_oauth(m.group(1), m.group(2), parsed)
        if path == "/login":
            return self._redirect("/about#access")

        user = self._current_user()
        if path in ABOUT_PATHS:
            return self._serve_about(user)
        if path in OPEN_ASSETS:
            return self._serve_static(path)  # canonical path, so what's served is exactly what was checked
        if path == "/api/me":
            return self._handle_me(user)
        if not user:
            return self._deny(path)

        # ---- signed in from here on
        self._private = True
        if path in ADMIN_FILES or path.startswith("/api/admin/"):
            return self._route_admin_get(path, user)
        if path.startswith("/api/"):
            root = path.split("/")[2]
            if root in FORYOU_GET_ROOTS:
                return self._handle_foryou_get(path, parsed, user)
            if path == "/api/issue":
                return self._handle_api_issue()
            if path == "/api/ledger":
                return self._handle_api_ledger()
            if path == "/api/votes":
                card_id = urllib.parse.parse_qs(parsed.query).get("card_id", [""])[0]
                if not card_id:
                    return self._json({"error": "card_id required"}, 400)
                return self._json({"card_id": card_id, "counts": votes.counts(card_id, FOR_YOU_DB)})
            return self._json({"error": "Not found"}, 404)
        if path in DECOMMISSIONED:
            return self._redirect("/")
        if path in MEMBER_PAGES:
            return self._serve_static(MEMBER_PAGES[path])
        return self._serve_static()

    def _deny(self, path: str):
        """Signed out: pages send the reader to the About page to sign in; data gets a 401."""
        if path.startswith("/api/"):
            return self._json({"error": "Login required"}, 401)
        if posixpath.splitext(path)[1] in ("", ".html"):
            target = "/about"
            if (path in MEMBER_PAGES or path in ADMIN_PAGES) and path != "/":
                target += "?next=" + urllib.parse.quote(path)
            return self._redirect(target + "#access" if target != "/about" else target)
        return self._json({"error": "Login required"}, 401)

    def _serve_about(self, user):
        """The About page, marked signed in or out before it's sent so the nav never flashes links
        a signed-out visitor can't open."""
        with open(os.path.join(PUBLIC_DIR, "about.html"), "rb") as f:
            data = f.read()
        if user:
            data = data.replace(b'data-session="out"', b'data-session="in"', 1)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, no-cache")
        self.send_header("Vary", "Cookie")
        self.end_headers()
        self._write(data)

    def _route_post(self):
        path = urllib.parse.urlparse(self.path).path
        if not WRITE_LIMITER.allow(self._client_ip()):
            return self._json({"error": "Too many requests"}, 429)
        if path == "/api/score":
            if not self._current_user():
                return self._json({"error": "Login required"}, 401)
            return self._handle_api_score()
        if path.startswith("/api/admin/"):
            user = self._current_user()
            if not user:
                return self._json({"error": "Login required"}, 401)
            if not admin.is_admin(user["id"], FOR_YOU_DB):
                return self._json({"error": "Admins only"}, 403)
            return self._handle_admin_post(path, user)
        if path in AUTH_POSTS or path.startswith(FORYOU_POST_PREFIXES):
            return self._handle_foryou_post(path)
        return self._json({"error": "Not found"}, 404)

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
        # Header injection guard: a Location never carries control characters.
        self.send_header("Location", re.sub(r"[\x00-\x1f\x7f]", "", location))
        self.send_header("Cache-Control", "no-store")
        for c in cookies:
            self.send_header("Set-Cookie", c)
        self.end_headers()

    def _handle_oauth(self, provider: str, step: str, parsed):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

        def fail(message: str):
            # Signed-in readers were connecting another account from For You; everyone else
            # was signing in on the About page.
            where = "/foryou?auth_error=" if self._current_user() else "/about?auth_error="
            suffix = "" if where.startswith("/foryou") else "#access"
            return self._redirect(where + urllib.parse.quote(message) + suffix, [oauth.clear_state_cookie()])

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
        if target.split("?")[0] in ("/foryou", "/foryou.html", "/for-you"):  # For You shows a welcome note
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
        self._write(body)

    def _read_json_body(self):
        # Requiring a JSON content type blocks cross-site <form> posts (CSRF) on top of SameSite cookies.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValueError("Bad Content-Length")
        if length < 0:  # rfile.read(-1) would read until the client hangs up
            raise ValueError("Bad Content-Length")
        if length > MAX_BODY:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length) if length else b""
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _handle_me(self, user):
        """Works signed out too (user is null), so the About page can tell which card to show."""
        if user:
            user = dict(user, avatar_url=oauth.avatar_for(user["id"], FOR_YOU_DB),
                        providers=[i["provider"] for i in oauth.identities(user["id"], FOR_YOU_DB)],
                        is_admin=admin.is_admin(user["id"], FOR_YOU_DB))
            return self._json({"user": user, "articles": newsfeed.article_count(FOR_YOU_DB)})
        return self._json({"user": None})

    def _handle_foryou_get(self, path: str, parsed, user):
        """Personal reads. The router only calls this with a signed-in reader."""
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        uid = user["id"]
        hour = None
        if re.fullmatch(r"-?\d{1,3}", q.get("hour", "")):
            hour = int(q["hour"]) % 24
        if path == "/api/your5":
            return self._json(Your5Engine().get_your_5(uid, hour))
        if path == "/api/digest":
            return self._json(Your5Engine().get_weekly_digest(uid))
        tab = q.get("tab", "foryou")
        try:
            limit = max(1, min(int(q.get("limit", 30)), 60))
        except ValueError:
            return self._json({"error": "Bad query parameter"}, 400)
        exclude = [x for x in q.get("exclude", "").split(",") if x][:500]
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
            if not all(isinstance(data.get(k, ""), str) for k in ("username", "password", "display_name")):
                return self._json({"error": "Username, password and display name must be text."}, 400)
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
                    follows_mod.mark_seen(uid, str(kind or ""), str(data.get("key") or ""), FOR_YOU_DB)
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
            recorded = 0
            for ev in events[:200]:
                ev = clean_event(ev)
                if ev:
                    recommender.record(uid, ev)
                    recorded += 1
            return self._json({"ok": True, "recorded": recorded})
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
        issue = Database(BRIEF_DB).get_latest_issue()
        if not issue:
            return self._json({"error": "No issue found"}, 404)
        self._send_json(issue.to_dict())

    # ------------------------------------------------------------------ admin
    def _route_admin_get(self, path: str, user):
        if not admin.is_admin(user["id"], FOR_YOU_DB):
            if path.startswith("/api/"):
                return self._json({"error": "Admins only"}, 403)
            return self.send_error(403, "Admins only")
        if path == "/api/admin/overview":
            return self._json(admin.overview(FOR_YOU_DB, BRIEF_DB))
        if path.startswith("/api/"):
            return self._json({"error": "Not found"}, 404)
        return self._serve_static(ADMIN_PAGES.get(path, path))

    def _handle_admin_post(self, path: str, user):
        try:
            data = self._read_json_body()
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"error": str(e)}, 400)
        if path != "/api/admin/resolve":
            return self._json({"error": "Not found"}, 404)
        reviewer = (user.get("display_name") or user["username"]).strip()
        try:
            rid = admin.resolve(BRIEF_DB, data.get("prediction_id"), data.get("status"),
                                data.get("evidence_url"), data.get("note"), reviewer)
        except (admin.AdminError, ValueError, KeyError) as e:
            return self._json({"error": str(e).strip("'\"")}, 400)
        print(f"[admin] {user['username']} recorded verdict #{rid}: {data.get('prediction_id')} -> {data.get('status')}")
        _rerender_site()
        return self._json({"ok": True, "resolution_id": rid, "resolved_by": reviewer})

    def _handle_api_ledger(self):
        preds = Database(BRIEF_DB).get_all_predictions()
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
        self._write(data)

    def _send_json(self, data: dict):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Cache-Control", "private, no-store")
        self.end_headers()
        self._write(response_bytes)


_render_lock = threading.Lock()


def _rerender_site():
    """Rebuild the static pages in the background after an admin verdict, so the Ledger page
    shows it without anyone running pipeline.render_html by hand."""
    def work():
        with _render_lock:
            try:
                from pipeline.render_html import render_all
                render_all(BRIEF_DB, PUBLIC_DIR)
            except Exception as e:
                print(f"[admin] re-render failed; run python3 -m pipeline.render_html: {e}")
    threading.Thread(target=work, daemon=True).start()


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
            if e.errno == errno.EADDRINUSE:  # 48 on macOS, 98 on Linux
                continue
            raise e
    print(f"Could not bind to any port between {PORT} and {PORT + 19}.")


if __name__ == "__main__":
    run_server()
