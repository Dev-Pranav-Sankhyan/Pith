"""
Follows: readers follow a person/company (entity), a phrase (keyword), or one developing
story. Followed items get a ranking boost, and new coverage of a followed story is
surfaced as an update ("Update on the story you read Tuesday").

Story matching reuses the clustering similarity (core/clustering.py) against a stored
snapshot of the story, so a thread survives after the original cluster ages out of the
48-hour clustering window.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from core.clustering import ClusterEngine, _content_tokens
from core.newsfeed import FOR_YOU_DB, _write_lock, connect, now_iso
from core.textfeatures import tokenize

KINDS = ("entity", "keyword", "story")
MAX_FOLLOWS = 50
MAX_KEY_LEN = 120
# A story update must look like the same event, by the same bar clustering uses.
STORY_MATCH = ClusterEngine.MATCH_THRESHOLD


def normalise_key(kind: str, key: str) -> str:
    key = " ".join(str(key or "").split())[:MAX_KEY_LEN]
    return key if kind == "story" else key.lower()


def story_seed(a: Dict[str, Any]) -> Dict[str, Any]:
    """The parts of an article needed to recognise later coverage of the same story."""
    return {
        "title": a.get("title", ""), "summary": a.get("summary", ""),
        "keywords": dict(list((a.get("keywords") or {}).items())[:12]),
        "entities": list(a.get("entities") or [])[:8], "published_at": a.get("published_at", ""),
    }


def follow(user_id: int, kind: str, key: str, label: Optional[str] = None,
           seed: Optional[Dict[str, Any]] = None, db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    key = normalise_key(kind, key)
    if not key or (kind == "keyword" and not tokenize(key)):
        raise ValueError("Nothing to follow")
    if kind == "story" and not seed:
        raise ValueError("A story follow needs the story it starts from")
    label = " ".join(str(label or key).split())[:MAX_KEY_LEN]
    ts = now_iso()
    with _write_lock, connect(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM follows WHERE user_id=?", (user_id,)).fetchone()[0]
        exists = conn.execute("SELECT 1 FROM follows WHERE user_id=? AND kind=? AND key=?",
                              (user_id, kind, key)).fetchone()
        if not exists and n >= MAX_FOLLOWS:
            raise ValueError(f"You can follow up to {MAX_FOLLOWS} things. Unfollow something first.")
        conn.execute("""INSERT INTO follows (user_id, kind, key, label, seed_json, created_at, last_checked)
                        VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(user_id, kind, key) DO UPDATE SET label=excluded.label""",
                     (user_id, kind, key, label, json.dumps(seed) if seed else None, ts, ts))
    return {"kind": kind, "key": key, "label": label}


def unfollow(user_id: int, kind: str, key: str, db_path: str = FOR_YOU_DB) -> bool:
    with _write_lock, connect(db_path) as conn:
        return conn.execute("DELETE FROM follows WHERE user_id=? AND kind=? AND key=?",
                            (user_id, kind, normalise_key(kind, key))).rowcount > 0


def list_follows(user_id: int, db_path: str = FOR_YOU_DB) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM follows WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    out = []
    for r in rows:
        f = {"kind": r["kind"], "key": r["key"], "label": r["label"], "created_at": r["created_at"],
             "last_checked": r["last_checked"]}
        if r["seed_json"]:
            f["seed"] = json.loads(r["seed_json"])
        if r["kind"] == "keyword":
            f["tokens"] = set(tokenize(r["key"]))
        out.append(f)
    return out


def mark_seen(user_id: int, kind: Optional[str] = None, key: Optional[str] = None,
              db_path: str = FOR_YOU_DB) -> None:
    ts = now_iso()
    with _write_lock, connect(db_path) as conn:
        if kind and key:
            conn.execute("UPDATE follows SET last_checked=? WHERE user_id=? AND kind=? AND key=?",
                         (ts, user_id, kind, normalise_key(kind, key)))
        else:
            conn.execute("UPDATE follows SET last_checked=? WHERE user_id=?", (ts, user_id))


def matches(f: Dict[str, Any], a: Dict[str, Any]) -> bool:
    kind = f["kind"]
    if kind == "entity":
        key = f["key"]
        if key in {e.lower() for e in a.get("entities", [])}:
            return True
        return re.search(rf"(?<!\w){re.escape(key)}(?!\w)", a.get("title", "").lower()) is not None
    if kind == "keyword":
        tokens = f.get("tokens") or set(tokenize(f["key"]))
        return bool(tokens) and tokens <= _content_tokens(a)
    if kind == "story":
        if a.get("id") == f["key"] or not f.get("seed"):
            return False
        return ClusterEngine.pair_similarity(a, f["seed"]) >= STORY_MATCH
    return False


def match_any(follows: Iterable[Dict[str, Any]], a: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Stories first: "an update on your story" is more specific than "mentions a company you follow".
    ordered = sorted(follows, key=lambda f: {"story": 0, "entity": 1, "keyword": 2}[f["kind"]])
    return next((f for f in ordered if matches(f, a)), None)


def describe(f: Dict[str, Any]) -> str:
    if f["kind"] == "story":
        title = f["label"]
        return f"Update on a story you follow: “{title[:70]}{'…' if len(title) > 70 else ''}”"
    return f"You follow {f['label']}"
