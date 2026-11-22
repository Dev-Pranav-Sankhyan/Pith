"""
A personal spoken brief, built from the reader's own Your 5 and what they follow.

The brief is a list of chapters ("segments"): an intro, one per story, updates on stories the
reader follows, their forecast calls, and a sign-off. The For You player reads them with the
browser's speech synthesis (free, works offline) and highlights each story as it is read. When
ELEVENLABS_API_KEY is set, the server renders the same script once with the studio voice; those
files are private (PRIVATE_AUDIO_DIR is outside public/ and gitignored) and served only to the
reader they belong to.

Length follows the reader's depth setting: about 45 seconds for "headline", 90 for "standard",
and close to three minutes for "deep".
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_AUDIO_DIR = os.path.join(ROOT, "private_audio")
WORDS_PER_MINUTE = 160
WORD_BUDGET = 250          # about ninety seconds ("standard")
DEPTH_BUDGET = {"headline": 125, "standard": WORD_BUDGET, "deep": 440}
ACTION_PHRASE = {"DO": "Worth doing this week", "WATCH": "Keep an eye on it", "IGNORE": "You can let this one go"}
ORDINALS = ["First", "Second", "Third", "Fourth", "Finally"]


def _sentence(text: str, max_words: int) -> Optional[str]:
    """The first sentence, without parentheticals, or None if it is longer than max_words.

    Cutting a sentence short makes the voice read a fragment, so a long line is dropped instead."""
    text = re.sub(r"\s*\([^)]*\)", "", " ".join((text or "").split()))
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    sentence = (m.group(1) if m else text).strip().rstrip(".!?")
    if not sentence or len(sentence.split()) > max_words:
        return None
    return sentence + "."


def _lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def _greeting(local_hour: Optional[int]) -> str:
    h = dt.datetime.now().hour if local_hour is None else local_hour % 24
    return "Good morning" if 5 <= h < 12 else "Good afternoon" if 12 <= h < 17 else "Good evening"


def _join(items: List[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _short_label(headline: str, words: int = 7) -> str:
    parts = re.sub(r"\s*\([^)]*\)", "", headline).split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def build_segments(your5: Dict[str, Any], name: str = "", local_hour: Optional[int] = None,
                   depth: str = "standard", extras: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Chapters of the spoken brief. Each line carries a priority; when the script runs over the
    time budget, the highest-priority-number lines are dropped first (0 is always kept)."""
    extras = extras or {}
    cards = (your5.get("cards") or [])[:5]
    if not cards:
        return [{"id": "intro", "kind": "intro", "label": "Today", "card_id": None,
                 "text": "There's no brief yet today. Check back after the morning run."}]
    budget = DEPTH_BUDGET.get(depth, WORD_BUDGET)
    deep = depth == "deep"
    role = your5.get("inferred_role", "developer")
    who = f", {name}" if name else ""

    # (segment index, text, priority)
    lines: List[Tuple[int, str, int]] = []
    segments: List[Dict[str, Any]] = [{"id": "intro", "kind": "intro", "label": "Intro", "card_id": None}]
    lines.append((0, f"{_greeting(local_hour)}{who}. Here are your five from Pith, through the {role} lens.", 0))
    top = [t for t in (extras.get("top_topics") or []) if t][:2]
    if top:
        lines.append((0, f"They're tuned to what you read most: {_join(top)}.", 4))

    for i, c in enumerate(cards):
        seg = len(segments)
        segments.append({"id": f"story-{i + 1}", "kind": "story", "card_id": c.get("id"), "index": i,
                         "label": _short_label(c.get("headline", ""))})
        rv = c.get("role_view") or {}
        headline = re.sub(r"\s*\([^)]*\)", "", c.get("headline", "")).rstrip(".")
        lines.append((seg, f"{ORDINALS[i]}: {headline}.", 0))
        impact = _sentence(rv.get("impact") or "", 28) or _sentence(c.get("why_it_matters", ""), 28)
        if impact:
            lines.append((seg, impact, 1))
        action = _sentence(rv.get("action_text") or c.get("action_text") or "", 22)
        if action:
            phrase = ACTION_PHRASE.get(rv.get("action_type") or c.get("action_type"), "Next step")
            lines.append((seg, f"{phrase}: {_lower_first(action)}", 2 + i))  # later cards' actions go first
        pred = c.get("prediction")
        if pred and (i == 0 or deep):
            statement = _sentence(pred.get("statement", ""), 30)
            if statement:
                lines.append((seg, f"Pith puts it at {round(pred['probability'] * 100)} percent that "
                                   f"{_lower_first(statement)}", 2 if i == 0 else 6))
        if deep:
            second = (c.get("second_order") or [])
            so = _sentence(second[0], 26) if second else None
            if so:
                lines.append((seg, f"The knock-on effect: {_lower_first(so)}", 7))

    follows = [u for u in (extras.get("follow_updates") or []) if u.get("title")][:2]
    if follows:
        seg = len(segments)
        segments.append({"id": "follows", "kind": "follows", "label": "Stories you follow", "card_id": None})
        first = follows[0]
        lines.append((seg, f"On stories you follow: {first['title'].rstrip('.')}, from {first.get('publisher') or 'the wire'}.", 3))
        if len(follows) > 1:
            lines.append((seg, f"And {follows[1]['title'].rstrip('.')}.", 8))

    fc = extras.get("forecast") or {}
    resolved = fc.get("newly_resolved") or []
    if resolved or fc.get("open_calls"):
        seg = len(segments)
        segments.append({"id": "forecasts", "kind": "forecasts", "label": "Your forecast calls", "card_id": None})
        if resolved:
            r = resolved[0]
            outcome = "happened" if r.get("status") == "correct" else "didn't happen"
            verdict = "You beat Pith on that one." if r.get("beat_pith") else "Pith was closer on that one."
            stmt = _sentence(r.get("statement", ""), 24)
            if stmt:
                lines.append((seg, f"One of your forecast calls resolved. {stmt[:-1]}: it {outcome}. {verdict}", 3))
        elif fc.get("open_calls"):
            n = fc["open_calls"]
            lines.append((seg, f"You have {n} open forecast call{'' if n == 1 else 's'} waiting to resolve.", 9))

    segments.append({"id": "outro", "kind": "outro", "label": "Sign-off", "card_id": None})
    lines.append((len(segments) - 1, "That's your five. Everything else today, you can safely ignore.", 0))

    def words() -> int:
        return sum(len(t.split()) for _, t, _ in lines)

    while words() > budget:
        worst = max(range(len(lines)), key=lambda k: (lines[k][2], k))
        if lines[worst][2] == 0:
            break
        lines.pop(worst)

    out = []
    for idx, seg in enumerate(segments):
        text = " ".join(t for s, t, _ in lines if s == idx)
        if text:
            out.append(dict(seg, text=text))
    return out


def build_script(your5: Dict[str, Any], name: str = "", local_hour: Optional[int] = None,
                 depth: str = "standard", extras: Optional[Dict[str, Any]] = None) -> str:
    return "\n".join(s["text"] for s in build_segments(your5, name, local_hour, depth, extras))


def chapters(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Where each chapter starts, as a fraction of the whole (word-proportional), for seeking the MP3."""
    total = max(1, sum(len(s["text"].split()) for s in segments))
    out, done = [], 0
    for s in segments:
        out.append({"id": s["id"], "label": s["label"], "card_id": s.get("card_id"),
                    "start": round(done / total, 4)})
        done += len(s["text"].split())
    return out


def script_stats(script: str) -> Dict[str, int]:
    words = len(script.split())
    return {"words": words, "seconds": round(words / WORDS_PER_MINUTE * 60)}


def first_name(user: Dict[str, Any]) -> str:
    name = (user.get("display_name") or "").strip()
    return name.split()[0] if name else (user.get("username") or "")


def gather_extras(user_id: int, recommender, db_path: str) -> Dict[str, Any]:
    """Personal context for the script. Each part is optional, so one failing never breaks the brief."""
    out: Dict[str, Any] = {}
    try:
        out["top_topics"] = [t["key"] for t in recommender.profile(user_id)["topics"][:2]]
    except Exception:
        pass
    try:
        out["follow_updates"] = [{"title": u["title"], "publisher": u.get("publisher")}
                                 for u in recommender.following(user_id, 12) if u.get("is_new")][:2]
    except Exception:
        pass
    try:
        from core.personal_forecasts import forecast_record
        rec = forecast_record(user_id, db_path)
        out["forecast"] = {"open_calls": rec["stats"].get("open_calls", 0),
                           "newly_resolved": rec.get("newly_resolved", [])}
    except Exception:
        pass
    return out


def personal_brief(user: Dict[str, Any], local_hour: Optional[int], your5: Dict[str, Any], recommender,
                   db_path: str) -> Tuple[List[Dict[str, Any]], str, str]:
    """(segments, script, depth) for one reader. The server and the scheduled digest both use this,
    so a studio MP3 rendered at delivery time matches what the For You player asks for."""
    depth = (your5.get("depth") or {}).get("depth") or "standard"
    extras = gather_extras(user["id"], recommender, db_path)
    segments = build_segments(your5, first_name(user), local_hour, depth, extras)
    return segments, "\n".join(seg["text"] for seg in segments), depth


def studio_voice_available() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def audio_path(user_id: int, script: str, day: Optional[str] = None) -> str:
    day = day or dt.date.today().isoformat()
    digest = hashlib.sha1(script.encode()).hexdigest()[:10]
    return os.path.join(PRIVATE_AUDIO_DIR, f"{int(user_id)}-{day}-{digest}.mp3")


def latest_audio(user_id: int, day: Optional[str] = None) -> Optional[str]:
    day = day or dt.date.today().isoformat()
    if not os.path.isdir(PRIVATE_AUDIO_DIR):
        return None
    prefix = f"{int(user_id)}-{day}-"
    files = sorted((f for f in os.listdir(PRIVATE_AUDIO_DIR) if f.startswith(prefix) and f.endswith(".mp3")),
                   key=lambda f: os.path.getmtime(os.path.join(PRIVATE_AUDIO_DIR, f)), reverse=True)
    return os.path.join(PRIVATE_AUDIO_DIR, files[0]) if files else None


def render_studio_audio(user_id: int, script: str) -> Optional[str]:
    """Renders (or reuses) today's MP3 for this script. None if the studio voice isn't configured."""
    if not studio_voice_available():
        return None
    path = audio_path(user_id, script)
    if os.path.exists(path):
        return path
    from pipeline.audio_brief import clean_spoken_text, synthesize_speech_elevenlabs
    os.makedirs(PRIVATE_AUDIO_DIR, exist_ok=True)
    return path if synthesize_speech_elevenlabs(clean_spoken_text(script), path) else None
