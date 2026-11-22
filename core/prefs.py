"""
Per-reader preferences (foryou.sqlite3, table user_prefs).

Explicit choices always win over inferred ones. Depth ("how much of each story do you
want?") is inferred from the reader's own dwell time until they pick one.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from core.newsfeed import FOR_YOU_DB, _write_lock, connect, now_iso

DEPTHS = ("auto", "headline", "standard", "deep")
REGIONS = ("global", "americas", "europe", "uk", "india", "asia", "africa", "middle-east")  # see FEED_REGIONS
DEFAULTS: Dict[str, Any] = {
    "depth": "auto",            # auto = inferred from reading behaviour
    "delivery_hour": None,      # local hour (0-23) the reader wants their brief; None = no schedule
    "tz_offset_minutes": 0,     # reader's UTC offset, sent by the browser, so delivery_hour is local
    "region": "global",         # boosts stories from that region's outlets
    "last_forecast_seen": None,  # ISO time the reader last looked at their forecast record
}
# Median seconds on a story -> depth. Below 25s people skim; past two minutes they read in full.
DEPTH_THRESHOLDS = (25.0, 120.0)
DEPTH_MIN_READS = 5


def _validate(key: str, value: Any) -> Any:
    if key == "depth":
        if value not in DEPTHS:
            raise ValueError(f"depth must be one of {DEPTHS}")
        return value
    if key == "delivery_hour":
        if value is None or value == "":
            return None
        try:
            hour = int(value)
        except (TypeError, ValueError):
            raise ValueError("delivery_hour must be 0-23 or empty")
        if not 0 <= hour <= 23:
            raise ValueError("delivery_hour must be 0-23 or empty")
        return hour
    if key == "tz_offset_minutes":
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            raise ValueError("tz_offset_minutes must be a whole number")
        if not -720 <= minutes <= 840:
            raise ValueError("tz_offset_minutes is out of range")
        return minutes
    if key == "region":
        if value not in REGIONS:
            raise ValueError(f"region must be one of {REGIONS}")
        return value
    if key == "last_forecast_seen":
        return None if value is None else str(value)[:40]
    raise ValueError(f"unknown preference: {key}")


def get_prefs(user_id: int, db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    with connect(db_path) as conn:
        for r in conn.execute("SELECT key, value FROM user_prefs WHERE user_id=?", (user_id,)):
            if r["key"] in DEFAULTS:
                try:
                    out[r["key"]] = json.loads(r["value"])
                except (TypeError, ValueError):
                    pass
    return out


def set_prefs(user_id: int, updates: Dict[str, Any], db_path: str = FOR_YOU_DB,
              allow_internal: bool = False) -> Dict[str, Any]:
    """Validates every key first, then writes them together. Raises ValueError on a bad value."""
    clean = {}
    for key, value in (updates or {}).items():
        if key == "last_forecast_seen" and not allow_internal:
            raise ValueError("last_forecast_seen is set by the server")
        clean[key] = _validate(key, value)
    ts = now_iso()
    with _write_lock, connect(db_path) as conn:
        for key, value in clean.items():
            conn.execute("""INSERT INTO user_prefs (user_id, key, value, updated_at) VALUES (?,?,?,?)
                            ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                         (user_id, key, json.dumps(value), ts))
    return get_prefs(user_id, db_path)


def infer_depth(user_id: int, db_path: str = FOR_YOU_DB) -> Tuple[str, str]:
    with connect(db_path) as conn:
        rows = conn.execute("""SELECT dwell_seconds FROM user_articles WHERE user_id=? AND dwell_seconds > 0
                               ORDER BY last_seen DESC LIMIT 40""", (user_id,)).fetchall()
    if len(rows) < DEPTH_MIN_READS:
        return "standard", f"Standard until you've read {DEPTH_MIN_READS} stories"
    vals = sorted(r[0] for r in rows)
    median = vals[len(vals) // 2]
    if median < DEPTH_THRESHOLDS[0]:
        return "headline", f"You usually skim (median {int(median)}s per story), so cards open as headlines"
    if median > DEPTH_THRESHOLDS[1]:
        return "deep", f"You read in depth (median {int(median // 60)}m per story), so cards open in full"
    return "standard", f"You read about {int(median)}s per story"


def effective_depth(user_id: Optional[int], db_path: str = FOR_YOU_DB) -> Dict[str, str]:
    if not user_id:
        return {"depth": "standard", "source": "default", "reason": "Default for visitors"}
    chosen = get_prefs(user_id, db_path)["depth"]
    if chosen != "auto":
        return {"depth": chosen, "source": "chosen", "reason": "Your setting"}
    depth, reason = infer_depth(user_id, db_path)
    return {"depth": depth, "source": "inferred", "reason": reason}
