"""
Bridge between the Daily Brief (brief.sqlite3) and the For You recommender.

Brief cards are turned into the same article shape the recommender uses
(topics, TF-IDF keywords, entities, publisher), so a like, save, dwell or
"worth my time" on a brief card trains the same taste profile as a For You
article, and "Your 5" can score cards with the same maths as the feed.
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import threading
from collections import Counter
from typing import Any, Dict, List, Optional

from core.textfeatures import featurize, tfidf_keywords

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF_DB = os.path.join(ROOT, "brief.sqlite3")
BRIEF_DAYS = 3          # today's issue plus the two before it
BRIEF_TOPIC_HINT = "AI"  # the brief's beat is AI & developer infrastructure


def card_text(card) -> str:
    parts = [card.headline, card.what_happened, card.why_it_matters, " ".join(card.second_order or [])]
    parts += [rv.impact for rv in (card.role_views or {}).values()]
    return " ".join(p for p in parts if p)


class BriefCards:
    """In-memory, featurised cards from the latest few issues. Reloads when the DB changes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sig = None
        self.cards: Dict[str, Any] = {}          # card id -> Card
        self.articles: Dict[str, Dict[str, Any]] = {}  # card id -> article-shaped features
        self.dates: List[str] = []               # issue dates loaded, newest first

    def _signature(self, db_path: str):
        if not os.path.exists(db_path):
            return None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                row = conn.execute("SELECT COUNT(*), MAX(issue_date) FROM cards").fetchone()
            finally:
                conn.close()
            return tuple(row) + (os.path.getmtime(db_path),)
        except sqlite3.Error:
            return None

    def get(self, db_path: str = BRIEF_DB) -> "BriefCards":
        sig = self._signature(db_path)
        if sig is None:
            return self
        if sig != self._sig:
            with self._lock:
                if sig != self._sig:
                    self._load(db_path)
                    self._sig = sig
        return self

    def _load(self, db_path: str) -> None:
        from core.db import Database  # local import: core.db pulls in the models
        db = Database(db_path)
        with db.get_connection() as conn:
            dates = [r[0] for r in conn.execute(
                "SELECT date FROM daily_issues ORDER BY date DESC LIMIT ?", (BRIEF_DAYS,))]
        cards, tiers, issue_dates = {}, {}, {}
        for d in dates:
            issue = db.get_issue_by_date(d)
            if not issue:
                continue
            for tier, group in (("core", issue.cards), ("pool", getattr(issue, "pool", []) or [])):
                for c in group:
                    if c.id not in cards:
                        cards[c.id], tiers[c.id], issue_dates[c.id] = c, tier, d

        feats = {cid: featurize(c.headline, card_text(c), BRIEF_TOPIC_HINT) for cid, c in cards.items()}
        df: Counter = Counter()
        for tf, _, _ in feats.values():
            df.update(tf.keys())
        arts = {}
        for cid, c in cards.items():
            tf, topics, entities = feats[cid]
            kw = tfidf_keywords(tf, df, len(cards))
            link = c.evidence_links[0] if c.evidence_links else None
            text = card_text(c)
            arts[cid] = {
                "id": cid, "url": link.url if link else "", "title": c.headline, "summary": c.what_happened,
                "publisher": (link.publisher if link and link.publisher else "Pith Brief"),
                "feed_id": "pith-brief", "image_url": None,
                "published_at": c.published_at or f"{issue_dates[cid]}T05:00:00+00:00",
                "word_count": len(text.split()), "topics": topics, "keywords": kw,
                "kwset": set(list(kw)[:8]), "entities": entities, "is_demo": False,
                "kind": "brief", "tier": tiers[cid], "issue_date": issue_dates[cid],
                "signal_score": c.signal_score,
            }
        self.cards, self.articles, self.dates = cards, arts, dates

    def article(self, card_id: str, db_path: str = BRIEF_DB) -> Optional[Dict[str, Any]]:
        return self.get(db_path).articles.get(card_id)


BRIEF = BriefCards()


def today_iso() -> str:
    return dt.date.today().isoformat()
