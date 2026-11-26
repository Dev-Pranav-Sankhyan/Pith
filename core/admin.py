"""
Admin access.

An admin is an ordinary account with a row in the `admins` table (foryou.sqlite3). Rights are
granted only from a shell on the machine that runs the server, never over HTTP, so nobody can
make themselves an admin through the site and no admin password ever sits in the repo.

    python3 -m core.admin create <username> [--display-name "Name"]   # asks for the password
    python3 -m core.admin grant <username>                            # existing account
    python3 -m core.admin revoke <username>
    python3 -m core.admin list

Admins get the /admin page: reader counts, feed health, the readers list and the forecasts
waiting for a verdict. A verdict goes through Database.record_resolution with the admin's name
as the reviewer, the same rule `pipeline.resolve_predictions resolve` follows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from core import auth
from core.newsfeed import FOR_YOU_DB, connect, init_schema, now_iso

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(ROOT, FOR_YOU_DB)
DEFAULT_BRIEF_DB = os.path.join(ROOT, "brief.sqlite3")
READER_LIMIT = 200
_URL_RE = re.compile(r"^https?://[^\s\x00-\x1f\x7f]{3,2000}$", re.IGNORECASE)


class AdminError(Exception):
    pass


# ---------------------------------------------------------------- rights

def is_admin(user_id: Optional[int], db_path: str = DEFAULT_DB) -> bool:
    if not user_id:
        return False
    with connect(db_path) as conn:
        return conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone() is not None


def _user_id(conn, username: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", ((username or "").strip(),)).fetchone()
    if not row:
        raise AdminError(f"No account called {username!r}.")
    return row["id"]


def grant(username: str, db_path: str = DEFAULT_DB, by: str = "cli") -> int:
    init_schema(db_path)
    with connect(db_path) as conn:
        uid = _user_id(conn, username)
        conn.execute("INSERT OR IGNORE INTO admins (user_id, granted_at, granted_by) VALUES (?, ?, ?)",
                     (uid, now_iso(), by))
    return uid


def revoke(username: str, db_path: str = DEFAULT_DB) -> bool:
    init_schema(db_path)
    with connect(db_path) as conn:
        uid = _user_id(conn, username)
        return conn.execute("DELETE FROM admins WHERE user_id = ?", (uid,)).rowcount > 0


def create(username: str, password: str, display_name: str = "", db_path: str = DEFAULT_DB) -> int:
    """A new account with admin rights. Same username and password rules as sign-up."""
    uid = auth.create_user(username, password, display_name, db_path)
    grant(username, db_path)
    return uid


def list_admins(db_path: str = DEFAULT_DB) -> List[Dict[str, Any]]:
    init_schema(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("""
            SELECT u.username, u.display_name, a.granted_at, a.granted_by
            FROM admins a JOIN users u ON u.id = a.user_id ORDER BY a.granted_at
        """).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- what the admin page shows

def readers(db_path: str = DEFAULT_DB, limit: int = READER_LIMIT) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute("""
            SELECT u.id, u.username, u.display_name, u.created_at, u.onboarded,
                   (SELECT COUNT(*) FROM events e WHERE e.user_id = u.id) AS events,
                   (SELECT MAX(e.created_at) FROM events e WHERE e.user_id = u.id) AS last_event,
                   (SELECT MAX(s.created_at) FROM sessions s WHERE s.user_id = u.id) AS last_sign_in,
                   (SELECT GROUP_CONCAT(i.provider, ',') FROM user_identities i WHERE i.user_id = u.id) AS providers,
                   EXISTS (SELECT 1 FROM admins a WHERE a.user_id = u.id) AS is_admin
            FROM users u ORDER BY u.created_at DESC, u.id DESC LIMIT ?
        """, (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["onboarded"] = bool(d["onboarded"])
        d["is_admin"] = bool(d["is_admin"])
        d["providers"] = sorted(set((d["providers"] or "").split(",")) - {""})
        last = [t for t in (d.pop("last_event"), d.pop("last_sign_in")) if t]
        d["last_active"] = max(last) if last else None
        out.append(d)
    return out


def reader_stats(db_path: str = DEFAULT_DB) -> Dict[str, Any]:
    week_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat(timespec="seconds")
    with connect(db_path) as conn:
        one = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
        return {
            "readers": one("SELECT COUNT(*) FROM users"),
            "new_this_week": one("SELECT COUNT(*) FROM users WHERE created_at >= ?", week_ago),
            "active_this_week": one("SELECT COUNT(DISTINCT user_id) FROM events WHERE created_at >= ?", week_ago),
            "signed_in_now": one("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE expires_at > ?", now_iso()),
            "admins": one("SELECT COUNT(*) FROM admins"),
            "articles": one("SELECT COUNT(*) FROM articles"),
            "demo_articles": one("SELECT COUNT(*) FROM articles WHERE is_demo = 1"),
            "last_fetch": one("SELECT MAX(fetched_at) FROM articles WHERE feed_id IS NULL OR feed_id NOT LIKE 'u-%'"),
        }


def _card_info(db) -> Dict[str, Dict[str, Any]]:
    with db.get_connection() as conn:
        rows = conn.execute("SELECT id, headline, evidence_links_json FROM cards").fetchall()
    out = {}
    for r in rows:
        try:
            links = json.loads(r["evidence_links_json"] or "[]")
        except ValueError:
            links = []
        first = links[0] if links else None
        url = first.get("url") if isinstance(first, dict) else first if isinstance(first, str) else None
        out[r["id"]] = {"headline": r["headline"], "source_url": url}
    return out


def _forecast(p, cards) -> Dict[str, Any]:
    card = cards.get(p.card_id or "", {})
    return {
        "id": p.id, "statement": p.statement, "probability": round(p.probability * 100),
        "made_at": p.made_at, "resolves_at": p.resolves_at, "criteria": p.resolution_criteria,
        "status": p.status, "resolved_at": p.resolved_at, "resolved_by": p.resolved_by,
        "evidence_url": p.evidence_url, "card_id": p.card_id,
        "headline": card.get("headline"), "source_url": card.get("source_url"),
    }


def forecasts(brief_db: str = DEFAULT_BRIEF_DB, as_of: Optional[str] = None) -> Dict[str, Any]:
    """Live forecasts only: illustrative examples are never scored, so they never need a verdict."""
    from core.db import Database
    from core.ledger import LedgerEngine
    db = Database(brief_db)
    preds = db.get_all_predictions()
    live = [p for p in preds if LedgerEngine.is_live(p)]
    cards = _card_info(db)
    due = sorted(LedgerEngine.get_due_predictions(live, as_of_date=as_of), key=lambda p: str(p.resolves_at))
    due_ids = {p.id for p in due}
    upcoming = sorted((p for p in live if p.status == "open" and p.id not in due_ids), key=lambda p: str(p.resolves_at))
    resolved = sorted((p for p in live if p.status != "open"),
                      key=lambda p: str(p.resolved_at or ""), reverse=True)
    stats = LedgerEngine.calculate_statistics(preds)
    return {
        "due": [_forecast(p, cards) for p in due],
        "upcoming": [_forecast(p, cards) for p in upcoming[:12]],
        "recent": [_forecast(p, cards) for p in resolved[:12]],
        "counts": {"live": len(live), "open": len(due) + len(upcoming), "due": len(due),
                   "resolved": len(resolved)},
        "brier": stats.get("brier_score"),
        "hit_rate_pct": stats.get("hit_rate_pct"),
    }


def overview(db_path: str = DEFAULT_DB, brief_db: str = DEFAULT_BRIEF_DB) -> Dict[str, Any]:
    return {"stats": reader_stats(db_path), "readers": readers(db_path), "forecasts": forecasts(brief_db)}


# ---------------------------------------------------------------- verdicts

def resolve(brief_db: str, prediction_id: Any, status: Any, evidence_url: Any, note: Any, reviewer: str) -> int:
    """Record an admin's verdict on a live forecast. Database.record_resolution enforces the rest
    (named reviewer, evidence for correct/wrong, append-only log)."""
    from core.db import Database
    from core.ledger import LedgerEngine
    for value in (prediction_id, status, evidence_url, note):
        if value is not None and not isinstance(value, str):
            raise AdminError("Every field must be text.")
    prediction_id, status = (prediction_id or "").strip(), (status or "").strip()
    evidence_url, note = (evidence_url or "").strip() or None, (note or "").strip()[:2000] or None
    if status not in ("correct", "wrong", "void"):
        raise AdminError("Verdict must be correct, wrong or void.")
    if evidence_url and not _URL_RE.match(evidence_url):
        raise AdminError("Evidence must be a web link (http or https).")
    if status in ("correct", "wrong") and not evidence_url:
        raise AdminError("A correct or wrong verdict needs an evidence link.")
    db = Database(brief_db)
    p = {x.id: x for x in db.get_all_predictions()}.get(prediction_id)
    if p is None:
        raise AdminError("Unknown forecast.")
    if not LedgerEngine.is_live(p):
        raise AdminError("Illustrative examples are never scored, so they take no verdict.")
    if p.status != "open":
        raise AdminError("This forecast already has a verdict. Corrections go through "
                         "`python3 -m pipeline.resolve_predictions resolve`, which keeps the earlier one.")
    return db.record_resolution(prediction_id, status, evidence_url, note, reviewer)


# ---------------------------------------------------------------- CLI

def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password (8+ characters): ")
    if getpass.getpass("Same password again: ") != first:
        raise AdminError("The passwords didn't match.")
    return first


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB, help="For You database (default: foryou.sqlite3 in the repo)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="Create a new admin account")
    c.add_argument("username")
    c.add_argument("--display-name", default="")
    c.add_argument("--password-stdin", action="store_true", help="Read the password from the first line of stdin")
    g = sub.add_parser("grant", help="Give an existing account admin rights")
    g.add_argument("username")
    r = sub.add_parser("revoke", help="Take admin rights away")
    r.add_argument("username")
    sub.add_parser("list", help="List admins")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "create":
            create(args.username, _read_password(args.password_stdin), args.display_name, args.db)
            print(f"Created admin account {args.username!r}. Sign in on the About page, then open /admin.")
        elif args.cmd == "grant":
            grant(args.username, args.db)
            print(f"{args.username!r} is an admin.")
        elif args.cmd == "revoke":
            print(f"{args.username!r} is no longer an admin." if revoke(args.username, args.db)
                  else f"{args.username!r} wasn't an admin.")
        else:
            rows = list_admins(args.db)
            for a in rows:
                print(f"{a['username']}  ({a['display_name']})  since {a['granted_at']} via {a['granted_by']}")
            if not rows:
                print("No admins yet. Create one with: python3 -m core.admin create <username>")
    except (AdminError, auth.AuthError) as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
