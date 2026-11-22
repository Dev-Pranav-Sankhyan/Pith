"""
Accounts and sessions for the For You feed. Stdlib only.

* Passwords: PBKDF2-HMAC-SHA256, 240k iterations, per-user 16-byte salt.
* Sessions: random 256-bit token in an HttpOnly cookie; only its SHA-256 is stored.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from typing import Any, Dict, Optional

from core.newsfeed import FOR_YOU_DB, connect, init_schema, now_iso

PBKDF2_ITERATIONS = 240_000
SESSION_DAYS = 30
COOKIE_NAME = "pith_session"
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")

# Simple in-memory brute-force throttle: username -> [failures, first_failure_ts]
_failed: Dict[str, list] = {}
MAX_FAILURES, LOCK_WINDOW = 8, 300
# Checked when the username doesn't exist, so a wrong username takes as long as a wrong
# password and response timing doesn't reveal which accounts exist.
_DUMMY_HASH = None


class AuthError(Exception):
    pass


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, digest_hex = stored.split("$")
        salt, rounds = bytes.fromhex(salt_hex), int(iters)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _text(value: Any) -> str:
    if value is not None and not isinstance(value, str):
        raise AuthError("Username and password must be text.")
    return value or ""


def create_user(username: str, password: str, display_name: str = "", db_path: str = FOR_YOU_DB) -> int:
    init_schema(db_path)
    username, password, display_name = _text(username).strip(), _text(password), _text(display_name)
    if not _USERNAME_RE.match(username):
        raise AuthError("Username must be 3–32 characters: letters, numbers, _ . -")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if len(password) > 1024:  # PBKDF2 cost grows with length; nobody needs more
        raise AuthError("Password must be at most 1024 characters.")
    try:
        with connect(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, (display_name or username).strip()[:60], hash_password(password), now_iso()))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise AuthError("That username is taken.")


def authenticate(username: str, password: str, db_path: str = FOR_YOU_DB) -> int:
    global _DUMMY_HASH
    username, password = _text(username).strip(), _text(password)
    if len(password) > 1024:
        raise AuthError("Wrong username or password.")
    key = username.lower()
    rec = _failed.get(key)
    if rec and rec[0] >= MAX_FAILURES and time.time() - rec[1] < LOCK_WINDOW:
        raise AuthError("Too many attempts. Try again in a few minutes.")
    with connect(db_path) as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(16))
        verify_password(password, _DUMMY_HASH)
    if len(_failed) > 10_000:  # forget stale entries so random usernames can't grow this forever
        cutoff = time.time() - LOCK_WINDOW
        for k in [k for k, v in _failed.items() if v[1] < cutoff]:
            _failed.pop(k, None)
    if not row or not verify_password(password, row["password_hash"]):
        if not rec or time.time() - rec[1] >= LOCK_WINDOW:
            _failed[key] = [1, time.time()]
        else:
            rec[0] += 1
        raise AuthError("Wrong username or password.")
    _failed.pop(key, None)
    return row["id"]


def create_session(user_id: int, db_path: str = FOR_YOU_DB) -> str:
    token = secrets.token_urlsafe(32)
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=SESSION_DAYS)
    with connect(db_path) as conn:
        conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                     (_token_hash(token), user_id, now_iso(), expires.isoformat(timespec="seconds")))
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
    return token


def user_for_token(token: Optional[str], db_path: str = FOR_YOU_DB) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with connect(db_path) as conn:
        row = conn.execute("""
            SELECT u.id, u.username, u.display_name, u.onboarded, u.created_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
        """, (_token_hash(token), now_iso())).fetchone()
    return dict(row) if row else None


def destroy_session(token: Optional[str], db_path: str = FOR_YOU_DB) -> None:
    if token:
        with connect(db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def session_cookie(token: str, secure: bool = False) -> str:
    attrs = f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}"
    return attrs + ("; Secure" if secure else "")


def clear_cookie() -> str:
    return f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def parse_cookie(header: Optional[str]) -> Optional[str]:
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE_NAME and v:
            return v
    return None
