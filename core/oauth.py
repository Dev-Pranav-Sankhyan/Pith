"""
Sign in with Google, GitHub, X and LinkedIn (OAuth 2.0 authorization-code flow). Stdlib only.

Configuration, per provider (unset = the button is hidden):
    PITH_GOOGLE_CLIENT_ID / PITH_GOOGLE_CLIENT_SECRET
    PITH_GITHUB_CLIENT_ID / PITH_GITHUB_CLIENT_SECRET
    PITH_X_CLIENT_ID / PITH_X_CLIENT_SECRET
    PITH_LINKEDIN_CLIENT_ID / PITH_LINKEDIN_CLIENT_SECRET
Register this redirect URI with each provider:
    <base>/api/auth/oauth/<provider>/callback
where <base> is PITH_AUTH_BASE_URL (for example https://pith.example.com). When that is unset
the request's own origin is used, which is fine for local development.

Security and privacy:
* state is a 256-bit random value, stored hashed for ten minutes, single use, and bound to the
  browser with a short-lived HttpOnly cookie, so a forged callback can't log someone in.
* PKCE (S256) is used where the provider supports it (Google, X).
* No email address is requested and no access token is stored. The profile is read once at
  sign-in; core/social_signals.py keeps only the interests derived from it.
* Accounts are never merged by email. A signed-in reader can connect more providers on purpose.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.newsfeed import FOR_YOU_DB, _write_lock, connect, init_schema, now_iso

STATE_TTL_SECONDS = 600
STATE_COOKIE = "pith_oauth_state"
HTTP_TIMEOUT = 10
_USERNAME_SAFE = re.compile(r"[^A-Za-z0-9_.\-]+")


class OAuthError(Exception):
    """Shown to the reader, so messages are plain and never include provider internals."""


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    authorize_url: str
    token_url: str
    scopes: Tuple[str, ...]
    pkce: bool
    token_auth: str                      # "body": secret in the form; "basic": HTTP Basic
    extra_authorize: Tuple[Tuple[str, str], ...] = ()


PROVIDERS: Dict[str, Provider] = {
    "google": Provider(
        "google", "Google",
        "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token",
        ("openid", "profile"), pkce=True, token_auth="body",
        extra_authorize=(("prompt", "select_account"),)),
    "github": Provider(
        "github", "GitHub",
        "https://github.com/login/oauth/authorize", "https://github.com/login/oauth/access_token",
        ("read:user",), pkce=False, token_auth="body",
        extra_authorize=(("allow_signup", "true"),)),
    # follows.read is asked for because who you follow is the best interest signal X has. On X's
    # free API tier the follows endpoint is refused; sign-in still works and that part is skipped.
    "x": Provider(
        "x", "X",
        "https://x.com/i/oauth2/authorize", "https://api.x.com/2/oauth2/token",
        ("users.read", "tweet.read", "follows.read"), pkce=True, token_auth="basic"),
    "linkedin": Provider(
        "linkedin", "LinkedIn",
        "https://www.linkedin.com/oauth/v2/authorization", "https://www.linkedin.com/oauth/v2/accessToken",
        ("openid", "profile"), pkce=False, token_auth="body"),
}


# ---------------------------------------------------------------- configuration
def credentials(provider_id: str) -> Tuple[Optional[str], Optional[str]]:
    prefix = f"PITH_{provider_id.upper()}_"
    return os.environ.get(prefix + "CLIENT_ID") or None, os.environ.get(prefix + "CLIENT_SECRET") or None


def configured(provider_id: str) -> bool:
    cid, secret = credentials(provider_id)
    return bool(cid and secret)


def provider_list() -> List[Dict[str, Any]]:
    return [{"id": p.id, "name": p.name, "configured": configured(p.id)} for p in PROVIDERS.values()]


def redirect_uri(provider_id: str, request_base: str) -> str:
    base = (os.environ.get("PITH_AUTH_BASE_URL") or request_base).rstrip("/")
    return f"{base}/api/auth/oauth/{provider_id}/callback"


def safe_next(path: Optional[str], default: str = "/") -> str:
    """Only same-site relative paths, so the callback can't be used as an open redirect."""
    path = (path or "").strip() if isinstance(path, str) else ""
    # Browsers drop tabs and newlines inside URLs ("/\t/evil.com" becomes "//evil.com"), and control
    # characters could split the Location header, so only plain printable ASCII is accepted.
    if not re.fullmatch(r"[\x21-\x7e]{1,200}", path):
        return default
    if not path.startswith("/") or path.startswith("//") or "\\" in path:
        return default
    return path


# ---------------------------------------------------------------- HTTP (tests swap HTTP for a fake)
def _http(method: str, url: str, data: Optional[Dict[str, str]] = None,
          headers: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", "Pith/1.0 (+personal news reader)")
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            status, raw = r.status, r.read(3_000_000)
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read(200_000)
    except (urllib.error.URLError, OSError, ValueError):
        return 0, {}
    try:
        return status, json.loads(raw or b"{}")
    except ValueError:
        return status, {}


HTTP: Callable[..., Tuple[int, Any]] = _http


def _get_json(url: str, token: str, extra: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
    return HTTP("GET", url, headers={"Authorization": f"Bearer {token}", **(extra or {})})


# ---------------------------------------------------------------- state
def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def start(provider_id: str, request_base: str, next_path: Optional[str] = None,
          link_user_id: Optional[int] = None, db_path: str = FOR_YOU_DB) -> Tuple[str, str]:
    """Returns (authorize_url, state). The caller sets `state` in the STATE_COOKIE."""
    p = PROVIDERS.get(provider_id)
    if not p:
        raise OAuthError("Unknown sign-in provider.")
    cid, _ = credentials(provider_id)
    if not configured(provider_id):
        raise OAuthError(f"Sign-in with {p.name} isn't set up on this server yet.")
    init_schema(db_path)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48) if p.pkce else None
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=STATE_TTL_SECONDS)).isoformat(timespec="seconds")
    with _write_lock, connect(db_path) as conn:
        conn.execute("DELETE FROM oauth_states WHERE created_at < ?", (cutoff,))
        conn.execute("""INSERT INTO oauth_states (state_hash, provider, verifier, next_path, link_user_id, created_at)
                        VALUES (?,?,?,?,?,?)""",
                     (_hash(state), provider_id, verifier, safe_next(next_path), link_user_id, now_iso()))
    params = {"response_type": "code", "client_id": cid, "redirect_uri": redirect_uri(provider_id, request_base),
              "scope": " ".join(p.scopes), "state": state}
    if verifier:
        params["code_challenge"] = _pkce_challenge(verifier)
        params["code_challenge_method"] = "S256"
    params.update(dict(p.extra_authorize))
    return f"{p.authorize_url}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}", state


def _consume_state(provider_id: str, state: str, cookie_state: Optional[str], db_path: str) -> Dict[str, Any]:
    # compare_digest on str raises for non-ASCII input, so compare the encoded bytes.
    if not state or not cookie_state or not hmac.compare_digest(state.encode(), cookie_state.encode()):
        raise OAuthError("That sign-in link expired or was opened in another browser. Please try again.")
    with _write_lock, connect(db_path) as conn:
        row = conn.execute("SELECT * FROM oauth_states WHERE state_hash = ?", (_hash(state),)).fetchone()
        conn.execute("DELETE FROM oauth_states WHERE state_hash = ?", (_hash(state),))
    if not row or row["provider"] != provider_id:
        raise OAuthError("That sign-in link expired. Please try again.")
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(row["created_at"])
    if age.total_seconds() > STATE_TTL_SECONDS:
        raise OAuthError("That sign-in took too long. Please try again.")
    return dict(row)


def _exchange(p: Provider, code: str, verifier: Optional[str], request_base: str) -> str:
    cid, secret = credentials(p.id)
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(p.id, request_base)}
    headers: Dict[str, str] = {}
    if p.token_auth == "basic":
        basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"
        form["client_id"] = cid
    else:
        form.update({"client_id": cid, "client_secret": secret})
    if verifier:
        form["code_verifier"] = verifier
    status, payload = HTTP("POST", p.token_url, data=form, headers=headers)
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if status != 200 or not token:
        raise OAuthError(f"{p.name} didn't confirm the sign-in. Please try again.")
    return token


# ---------------------------------------------------------------- provider profiles
def _locale_country(locale: Any) -> Optional[str]:
    if isinstance(locale, dict):
        return (locale.get("country") or "").upper() or None
    m = re.search(r"[-_]([A-Za-z]{2})$", str(locale or ""))
    return m.group(1).upper() if m else None


def _profile_google(token: str) -> Dict[str, Any]:
    status, u = _get_json("https://openidconnect.googleapis.com/v1/userinfo", token)
    if status != 200 or not u.get("sub"):
        raise OAuthError("Google didn't share your profile.")
    return {"subject": str(u["sub"]), "handle": None, "name": u.get("name") or u.get("given_name") or "",
            "avatar_url": u.get("picture"),
            "data": {"country": _locale_country(u.get("locale")), "locale": u.get("locale"), "hd": u.get("hd")}}


def _profile_linkedin(token: str) -> Dict[str, Any]:
    status, u = _get_json("https://api.linkedin.com/v2/userinfo", token)
    if status != 200 or not u.get("sub"):
        raise OAuthError("LinkedIn didn't share your profile.")
    return {"subject": str(u["sub"]), "handle": None, "name": u.get("name") or u.get("given_name") or "",
            "avatar_url": u.get("picture"), "data": {"country": _locale_country(u.get("locale"))}}


def _repo_summary(r: Dict[str, Any]) -> Dict[str, Any]:
    owner = r.get("owner") or {}
    return {"name": r.get("name") or "", "description": (r.get("description") or "")[:300],
            "language": r.get("language"), "topics": list(r.get("topics") or [])[:12],
            "fork": bool(r.get("fork")), "owner": owner.get("login") or "", "owner_type": owner.get("type") or ""}


def _profile_github(token: str) -> Dict[str, Any]:
    gh = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    status, u = _get_json("https://api.github.com/user", token, gh)
    if status != 200 or not u.get("id"):
        raise OAuthError("GitHub didn't share your profile.")
    login = u.get("login") or ""
    notes: List[str] = []
    repos: List[Dict[str, Any]] = []
    starred: List[Dict[str, Any]] = []
    q = urllib.parse.quote(login)
    s, data = _get_json(f"https://api.github.com/users/{q}/repos?per_page=100&sort=pushed&type=owner", token, gh)
    if s == 200 and isinstance(data, list):
        repos = [_repo_summary(r) for r in data[:100]]
    else:
        notes.append("GitHub didn't list your repositories.")
    s, data = _get_json(f"https://api.github.com/users/{q}/starred?per_page=100", token, gh)
    if s == 200 and isinstance(data, list):
        starred = [_repo_summary(r) for r in data[:100]]
    else:
        notes.append("GitHub didn't list your stars.")
    return {"subject": str(u["id"]), "handle": login, "name": u.get("name") or login,
            "avatar_url": u.get("avatar_url"),
            "data": {"bio": (u.get("bio") or "")[:400], "company": (u.get("company") or "")[:120],
                     "location": (u.get("location") or "")[:120], "repos": repos, "starred": starred,
                     "public_repos": u.get("public_repos") or len(repos), "notes": notes}}


def _profile_x(token: str) -> Dict[str, Any]:
    status, payload = _get_json(
        "https://api.x.com/2/users/me?user.fields=description,location,name,username,profile_image_url", token)
    u = payload.get("data") if isinstance(payload, dict) else None
    if status != 200 or not u or not u.get("id"):
        raise OAuthError("X didn't share your profile.")
    notes: List[str] = []
    following: List[Dict[str, str]] = []
    s, f = _get_json(f"https://api.x.com/2/users/{urllib.parse.quote(str(u['id']))}/following"
                     "?max_results=100&user.fields=description,name,username", token)
    if s == 200 and isinstance(f, dict) and isinstance(f.get("data"), list):
        following = [{"name": (a.get("name") or "")[:80], "username": a.get("username") or "",
                      "description": (a.get("description") or "")[:200]} for a in f["data"][:100]]
    else:
        notes.append("X didn't share who you follow (that needs a paid X API tier), so only your bio was used.")
    avatar = (u.get("profile_image_url") or "").replace("_normal.", "_200x200.") or None
    return {"subject": str(u["id"]), "handle": u.get("username"), "name": u.get("name") or u.get("username") or "",
            "avatar_url": avatar,
            "data": {"bio": (u.get("description") or "")[:400], "location": (u.get("location") or "")[:120],
                     "following": following, "notes": notes}}


PROFILE_FETCHERS = {"google": _profile_google, "github": _profile_github, "x": _profile_x,
                    "linkedin": _profile_linkedin}


def complete(provider_id: str, code: str, state: str, cookie_state: Optional[str], request_base: str,
             db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """Validates the callback, swaps the code for a token, reads the profile. The token is dropped here."""
    p = PROVIDERS.get(provider_id)
    if not p or not configured(provider_id):
        raise OAuthError("Unknown sign-in provider.")
    row = _consume_state(provider_id, state, cookie_state, db_path)
    if not code:
        raise OAuthError(f"{p.name} sign-in was cancelled.")
    token = _exchange(p, code, row["verifier"], request_base)
    profile = PROFILE_FETCHERS[provider_id](token)
    profile["provider"] = provider_id
    return {"profile": profile, "next": row["next_path"], "link_user_id": row["link_user_id"]}


# ---------------------------------------------------------------- accounts
def _unique_username(conn: sqlite3.Connection, profile: Dict[str, Any]) -> str:
    base = profile.get("handle") or (profile.get("name") or "").replace(" ", "_") or "reader"
    base = _USERNAME_SAFE.sub("", base)[:24].strip("._-") or "reader"
    if len(base) < 3:
        base = f"{base}_reader"
    candidate = base
    n = 1
    while conn.execute("SELECT 1 FROM users WHERE username = ?", (candidate,)).fetchone():
        n += 1
        candidate = f"{base}{n}"
    return candidate


def sign_in(profile: Dict[str, Any], link_user_id: Optional[int] = None,
            db_path: str = FOR_YOU_DB) -> Tuple[int, bool]:
    """Finds or creates the Pith account for this provider identity. Returns (user_id, is_new_account).

    With link_user_id (a reader who is already signed in and asked to connect), the identity is
    attached to that account instead."""
    provider, subject = profile["provider"], profile["subject"]
    now = now_iso()
    with _write_lock, connect(db_path) as conn:
        row = conn.execute("SELECT user_id FROM user_identities WHERE provider=? AND subject=?",
                           (provider, subject)).fetchone()
        if row:
            if link_user_id and row["user_id"] != link_user_id:
                raise OAuthError(f"That {PROVIDERS[provider].name} account is already connected to another Pith account.")
            conn.execute("""UPDATE user_identities SET handle=?, display_name=?, avatar_url=?, last_login=?
                            WHERE provider=? AND subject=?""",
                         (profile.get("handle"), profile.get("name"), profile.get("avatar_url"), now, provider, subject))
            return row["user_id"], False
        created = False
        if link_user_id:
            user_id = link_user_id
        else:
            name = (profile.get("name") or profile.get("handle") or "Reader").strip()[:60]
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (_unique_username(conn, profile), name, f"oauth${provider}", now))
            user_id, created = cur.lastrowid, True
        conn.execute("""INSERT INTO user_identities (provider, subject, user_id, handle, display_name, avatar_url,
                                                     created_at, last_login) VALUES (?,?,?,?,?,?,?,?)""",
                     (provider, subject, user_id, profile.get("handle"), profile.get("name"),
                      profile.get("avatar_url"), now, now))
        return user_id, created


def identities(user_id: int, db_path: str = FOR_YOU_DB) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(
            """SELECT provider, handle, display_name, avatar_url, created_at, last_login
               FROM user_identities WHERE user_id=? ORDER BY created_at""", (user_id,))]


def has_password(user_id: int, db_path: str = FOR_YOU_DB) -> bool:
    with connect(db_path) as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
    return bool(row and str(row["password_hash"]).startswith("pbkdf2_sha256$"))


def avatar_for(user_id: int, db_path: str = FOR_YOU_DB) -> Optional[str]:
    with connect(db_path) as conn:
        row = conn.execute("""SELECT avatar_url FROM user_identities WHERE user_id=? AND avatar_url IS NOT NULL
                              ORDER BY last_login DESC LIMIT 1""", (user_id,)).fetchone()
    return row["avatar_url"] if row else None


def disconnect(user_id: int, provider_id: str, db_path: str = FOR_YOU_DB) -> None:
    """Removes a connected provider. Refused when it is the reader's only way to sign in."""
    linked = identities(user_id, db_path)
    if not any(i["provider"] == provider_id for i in linked):
        raise OAuthError("That account isn't connected.")
    if len(linked) == 1 and not has_password(user_id, db_path):
        raise OAuthError("This is your only way to sign in, so it can't be disconnected.")
    with _write_lock, connect(db_path) as conn:
        conn.execute("DELETE FROM user_identities WHERE user_id=? AND provider=?", (user_id, provider_id))


def state_cookie(state: str, secure: bool = False) -> str:
    attrs = f"{STATE_COOKIE}={state}; Path=/api/auth/oauth; HttpOnly; SameSite=Lax; Max-Age={STATE_TTL_SECONDS}"
    return attrs + ("; Secure" if secure else "")


def clear_state_cookie() -> str:
    return f"{STATE_COOKIE}=; Path=/api/auth/oauth; HttpOnly; SameSite=Lax; Max-Age=0"


def parse_state_cookie(header: Optional[str]) -> Optional[str]:
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == STATE_COOKIE and v:
            return v
    return None
