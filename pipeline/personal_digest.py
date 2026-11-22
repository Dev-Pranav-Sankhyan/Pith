"""
Personal delivery: writes each reader's Your 5 (plus any forecasts of theirs that just
resolved) to a private outbox at the hour they chose, in their own time zone.

Run it hourly (cron or a scheduled workflow):
    python3 -m pipeline.personal_digest            # readers whose local hour is now
    python3 -m pipeline.personal_digest --all      # everyone with a delivery hour, now

Output goes to outbox/<date>/<user_id>.txt and .html (gitignored, never under public/).
When ELEVENLABS_API_KEY is set, each reader's spoken brief is also recorded in the studio voice
(private_audio/, gitignored), so it is ready to play the moment they open For You.
Sending is deliberately not wired up: plug an email provider or push service into
`deliver()` once one is chosen. Until then nothing leaves the server.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
from typing import Any, Dict, List

from core.newsfeed import FOR_YOU_DB, connect
from core import personal_audio
from core.personal_forecasts import forecast_record
from core.prefs import get_prefs
from core.your5 import Your5Engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOX = os.path.join(ROOT, "outbox")


def due_users(now_utc: dt.datetime, db_path: str = FOR_YOU_DB, everyone: bool = False) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        users = [dict(r) for r in conn.execute("SELECT id, username, display_name FROM users")]
    due = []
    for u in users:
        p = get_prefs(u["id"], db_path)
        if p["delivery_hour"] is None:
            continue
        local = now_utc + dt.timedelta(minutes=p["tz_offset_minutes"] or 0)
        if everyone or local.hour == p["delivery_hour"]:
            due.append({**u, "local_hour": local.hour, "local_date": local.date().isoformat()})
    return due


def render(user: Dict[str, Any], your5: Dict[str, Any], record: Dict[str, Any], script: str = "") -> Dict[str, str]:
    name = user["display_name"] or user["username"]
    text = [script or personal_audio.build_script(your5, personal_audio.first_name(user), user["local_hour"]), ""]
    for i, c in enumerate(your5.get("cards", []), 1):
        text.append(f"{i}. {c['headline']}\n   Why it's here: {c['why_chosen']}")
    resolved = record.get("newly_resolved") or []
    if resolved:
        text.append("\nForecasts you called that just resolved:")
        for r in resolved:
            text.append(f"- {r['statement']} -> {r['status'].upper()} "
                        f"({'you beat Pith' if r['beat_pith'] else 'Pith was closer'})")
    body = "\n".join(text)
    items = "".join(f"<li><b>{html.escape(c['headline'])}</b><br><small>{html.escape(c['why_chosen'])}</small></li>"
                    for c in your5.get("cards", []))
    page = (f"<!doctype html><meta charset='utf-8'><title>Your 5 · Pith</title>"
            f"<h1>Your 5, {html.escape(name)}</h1><ol>{items}</ol>")
    return {"text": body, "html": page}


def deliver(user: Dict[str, Any], rendered: Dict[str, str]) -> str:
    """Writes to the outbox. Replace with a real sender (email/push) when one is configured."""
    folder = os.path.join(OUTBOX, user["local_date"])
    os.makedirs(folder, exist_ok=True)
    base = os.path.join(folder, str(int(user["id"])))
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(rendered["text"])
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(rendered["html"])
    return base


def run(everyone: bool = False, db_path: str = FOR_YOU_DB) -> int:
    from core.recommender import Recommender
    engine = Your5Engine(foryou_db_path=db_path)
    rec = Recommender(db_path)
    users = due_users(dt.datetime.now(dt.timezone.utc), db_path, everyone)
    for u in users:
        your5 = engine.get_your_5(u["id"], u["local_hour"])
        record = forecast_record(u["id"], db_path)
        _, script, _ = personal_audio.personal_brief(u, u["local_hour"], your5, rec, db_path)
        print(f"  wrote {deliver(u, render(u, your5, record, script))}.txt")
        if personal_audio.studio_voice_available():
            mp3 = personal_audio.render_studio_audio(u["id"], script)
            print(f"  {'recorded ' + mp3 if mp3 else 'studio voice failed for user ' + str(u['id'])}")
    print(f"{len(users)} personal brief(s) written to the outbox.")
    return len(users)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--all", action="store_true", help="write for every reader with a delivery hour")
    run(everyone=ap.parse_args().all)
