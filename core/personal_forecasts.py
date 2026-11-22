"""
A reader's own forecast record ("Beat the Brief", personal edition).

Readers call each Pith forecast higher / agree / lower. Once a forecast resolves we score
the reader against Pith on the same questions with the Brier score.

Rules, in the spirit of the Ledger's integrity rules:
  * Only `live` predictions count; `illustrative` ones are never scored.
  * A reader's call counts only if it was last changed within CALL_WINDOW_DAYS of the
    forecast's publication, and before the resolution was recorded. Later calls are shown
    as "late" and never scored, so nobody can wait for the answer and then vote.
  * The reader's probability is *implied*: Pith's probability moved IMPLIED_SHIFT
    (15 points) toward their call. It is labelled as implied everywhere it is shown.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from core.brief_bridge import BRIEF_DB
from core.db import Database
from core.newsfeed import FOR_YOU_DB, connect, now_iso
from core import prefs as prefs_mod

IMPLIED_SHIFT = 0.15
CALL_WINDOW_DAYS = 3
MIN_SCORED_FOR_VERDICT = 5   # below this, show the numbers but don't declare a winner


def implied_probability(p: float, vote: str) -> float:
    q = p + {"higher": IMPLIED_SHIFT, "agree": 0.0, "lower": -IMPLIED_SHIFT}[vote]
    return round(max(0.02, min(0.98, q)), 3)


def _predictions_for_cards(card_ids: List[str], brief_db: str) -> Dict[str, Dict[str, Any]]:
    if not card_ids:
        return {}
    db = Database(brief_db)
    marks = ",".join("?" * len(card_ids))
    with db.get_connection() as conn:
        rows = conn.execute(f"""
            SELECT p.id, p.card_id, p.statement, p.probability, p.made_at, p.resolves_at, p.status,
                   p.provenance, p.evidence_url, c.headline,
                   (SELECT MAX(r.recorded_at) FROM prediction_resolutions r WHERE r.prediction_id = p.id) AS recorded_at
            FROM predictions p LEFT JOIN cards c ON c.id = p.card_id
            WHERE p.card_id IN ({marks})""", card_ids).fetchall()
    return {r["card_id"]: dict(r) for r in rows}


def vote_allowed(card_id: str, brief_db: str = BRIEF_DB) -> Tuple[bool, str]:
    """Calls are open only on a real, live, unresolved forecast whose date hasn't passed."""
    p = _predictions_for_cards([card_id], brief_db).get(card_id)
    if not p:
        return False, "No forecast found for that card"
    if p["provenance"] != "live":
        return False, "Illustrative forecasts can't be called"
    if p["status"] != "open":
        return False, "This forecast has resolved, so calls are closed"
    if p["resolves_at"] and p["resolves_at"] < dt.date.today().isoformat():
        return False, "This forecast's date has passed, so calls are closed"
    return True, ""


def _in_window(updated_at: str, made_at: str) -> bool:
    try:
        called = dt.date.fromisoformat(updated_at[:10])
        made = dt.date.fromisoformat(made_at[:10])
    except (TypeError, ValueError):
        return False
    return called <= made + dt.timedelta(days=CALL_WINDOW_DAYS)


def forecast_record(user_id: int, foryou_db: str = FOR_YOU_DB, brief_db: str = BRIEF_DB) -> Dict[str, Any]:
    with connect(foryou_db) as conn:
        votes = [dict(r) for r in conn.execute(
            "SELECT card_id, vote, created_at, updated_at FROM forecast_votes WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,))]
    preds = _predictions_for_cards([v["card_id"] for v in votes], brief_db)
    last_seen = prefs_mod.get_prefs(user_id, foryou_db)["last_forecast_seen"] or ""

    items: List[Dict[str, Any]] = []
    scored = []
    open_calls = late_calls = 0
    for v in votes:
        p = preds.get(v["card_id"])
        if not p or p["provenance"] != "live":
            continue
        counted = _in_window(v["updated_at"], p["made_at"])
        q = implied_probability(p["probability"], v["vote"])
        item = {
            "card_id": v["card_id"], "headline": p["headline"], "statement": p["statement"],
            "pith_probability": p["probability"], "your_vote": v["vote"], "your_implied_probability": q,
            "resolves_at": p["resolves_at"], "status": p["status"], "counted": counted,
            "evidence_url": p["evidence_url"],
        }
        resolved = p["status"] in ("correct", "wrong")
        if resolved and counted and p["recorded_at"] and v["updated_at"] < p["recorded_at"]:
            o = 1.0 if p["status"] == "correct" else 0.0
            item["your_error"] = round((q - o) ** 2, 4)
            item["pith_error"] = round((p["probability"] - o) ** 2, 4)
            item["beat_pith"] = item["your_error"] < item["pith_error"]
            item["is_new"] = p["recorded_at"] > last_seen
            scored.append(item)
        elif p["status"] == "open":
            if counted:
                open_calls += 1
            else:
                late_calls += 1
        items.append(item)

    n = len(scored)
    stats: Dict[str, Any] = {"scored": n, "open_calls": open_calls, "late_calls": late_calls}
    if n:
        yours = sum(i["your_error"] for i in scored) / n
        pith = sum(i["pith_error"] for i in scored) / n
        beat = sum(1 for i in scored if i["beat_pith"])
        tied = sum(1 for i in scored if i["your_error"] == i["pith_error"])
        stats.update({
            "your_brier": round(yours, 4), "pith_brier": round(pith, 4),
            "beat": beat, "tied": tied, "behind": n - beat - tied,
            "verdict": (None if n < MIN_SCORED_FOR_VERDICT
                        else "ahead" if yours < pith else "behind" if yours > pith else "level"),
        })
    return {
        "stats": stats,
        "newly_resolved": [i for i in scored if i.get("is_new")],
        "calls": items,
        "rules": {"implied_shift": IMPLIED_SHIFT, "call_window_days": CALL_WINDOW_DAYS,
                  "min_scored_for_verdict": MIN_SCORED_FOR_VERDICT},
    }


def mark_seen(user_id: int, foryou_db: str = FOR_YOU_DB) -> None:
    prefs_mod.set_prefs(user_id, {"last_forecast_seen": now_iso()}, foryou_db, allow_internal=True)
