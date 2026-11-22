"""
Your 5 Engine for Pith.

Unifies the Daily Brief and For You:
- Infers the reader's lens (Developer, Founder, Investor, Everyday) from learned affinities.
- Picks five cards for this reader from the brief's verified pool (today's 5 core cards, the
  extra cards that passed the same threshold and verification, and recent unread cards),
  using the same affinity maths as the For You feed, plus follows.
- Keeps one "must-know" slot: today's top shift is shown to everyone, so personalisation
  never hides the day's biggest story.
- Computes the weekly reading digest.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from core import follows as follows_mod
from core.brief_bridge import BRIEF, BRIEF_DB
from core.db import Database
from core.newsfeed import FOR_YOU_DB, connect
from core.prefs import effective_depth
from core.recommender import Recommender, daypart
from core.textfeatures import jaccard, tokenize

# Topic and keyword indicators for role inference. Keywords are matched as whole
# (stemmed) tokens against the reader's keyword affinities, never as substrings.
ROLE_INDICATORS = {
    "developer": {
        "topics": {"Technology": 1.5, "AI": 1.5},
        "keywords": ["code", "github", "api", "rpc", "sdk", "inference", "cuda", "latency", "vllm",
                     "python", "rust", "framework", "postgres", "postgresql", "kubernetes", "specification",
                     "benchmark", "compiler", "runtime", "endpoint", "architecture", "deprecation", "kernel",
                     "developer", "programming", "database", "linux"],
    },
    "founder": {
        "topics": {"Business": 1.5, "Technology": 1.0, "AI": 1.0},
        "keywords": ["startup", "pricing", "launch", "founder", "customer", "saas", "hiring", "product",
                     "margin", "growth", "discount", "competition", "strategy", "enterprise", "churn",
                     "subscription", "b2b"],
    },
    "investor": {
        "topics": {"Markets": 2.0, "Business": 1.2},
        "keywords": ["valuation", "revenue", "funding", "ipo", "shares", "merger", "acquisition", "venture",
                     "capital", "stock", "investor", "hedge", "stake", "earnings", "guidance", "dividend",
                     "bond", "nasdaq"],
    },
    "everyday": {
        "topics": {"Science": 1.2, "Space": 1.2, "Health": 1.2, "World": 1.0, "Entertainment": 1.0},
        "keywords": ["discovery", "research", "climate", "health", "space", "telescope", "planet", "study",
                     "culture", "public", "policy", "family", "school"],
    },
}
_ROLE_STEMS = {role: set(tokenize(" ".join(r["keywords"]))) for role, r in ROLE_INDICATORS.items()}
DEFAULT_ROLE = "developer"      # the brief's beat is developer infrastructure
MIN_ROLE_EVIDENCE = 2.0         # below this much positive affinity, don't claim to know the reader

ROLE_REASONS = {
    "developer": "Inferred from focus on code, APIs, inference runtimes, and engineering architecture",
    "founder": "Inferred from interest in startup pricing, SaaS economics, and product deployment",
    "investor": "Inferred from tracking venture funding, market capitalizations, and strategic acquisitions",
    "everyday": "Inferred from broad interest across technology, scientific exploration, and culture",
}


def infer_role(affinities: Dict[str, Dict[str, float]]) -> Tuple[str, float, str]:
    """
    Infers the reader's lens from learned affinities.
    Returns: (role, confidence_0_to_1, explanation)
    """
    topic_affs = affinities.get("topic", {})
    keyword_affs = affinities.get("keyword", {})
    scores = {role: 0.0 for role in ROLE_INDICATORS}
    for role, rules in ROLE_INDICATORS.items():
        for topic, weight in rules["topics"].items():
            scores[role] += max(0.0, topic_affs.get(topic, 0.0)) * weight
        for kw, aff in keyword_affs.items():
            if kw in _ROLE_STEMS[role]:
                scores[role] += max(0.0, aff) * 1.4

    total = sum(scores.values())
    if total < MIN_ROLE_EVIDENCE:
        return DEFAULT_ROLE, 0.3, "Not enough reading yet, so this is the default developer lens"
    top_role, top_score = max(scores.items(), key=lambda kv: kv[1])
    share = top_score / total
    confidence = round(min(0.95, 0.4 + 0.6 * share), 2)
    return top_role, confidence, ROLE_REASONS[top_role]


class Your5Engine:
    SLOTS = 5
    EDITORIAL_WEIGHT = 0.6      # signal score above the 60 threshold, scaled 0..1
    PERSONAL_WEIGHT = 1.6       # same scale the For You ranker gives content match
    FOLLOW_BONUS = 0.5
    AGE_PENALTY = 0.25          # per day older than today's issue
    READ_PENALTY = 0.35         # already opened: keep it out unless nothing else fits
    DIVERSITY = 0.3             # MMR penalty for repeating what is already picked

    def __init__(self, brief_db_path: str = BRIEF_DB, foryou_db_path: str = FOR_YOU_DB):
        self.brief_db_path = brief_db_path
        self.foryou_db_path = foryou_db_path
        self.brief_db = Database(brief_db_path)
        self.rec = Recommender(foryou_db_path, brief_db=brief_db_path)

    def get_weekly_digest(self, user_id: int) -> Dict[str, Any]:
        """Weekly reading and satisfaction digest."""
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat()
        with connect(self.foryou_db_path) as conn:
            reads_count = conn.execute("""
                SELECT COUNT(DISTINCT article_id) FROM events
                WHERE user_id=? AND kind='click' AND created_at >= ?
            """, (user_id, since)).fetchone()[0]
            dwell_total = conn.execute("""
                SELECT COALESCE(SUM(value), 0) FROM events
                WHERE user_id=? AND kind='dwell' AND created_at >= ?
            """, (user_id, since)).fetchone()[0]
            # Current ratings, not raw taps: toggling "worth my time" on and off must not count twice.
            worth_time_count = conn.execute("""
                SELECT COUNT(*) FROM user_articles WHERE user_id=? AND reaction=1 AND last_seen >= ?
            """, (user_id, since)).fetchone()[0]

        minutes = round(dwell_total / 60, 1)
        prof = self.rec.profile(user_id)
        top_topics = [t["key"] for t in prof.get("topics", [])[:3]]
        top_entities = [e["key"] for e in prof.get("entities", [])[:3]]
        return {
            "period": "Last 7 Days",
            "reads": reads_count,
            "minutes_read": minutes,
            "satisfaction_count": worth_time_count,
            "top_patterns": top_topics,
            "top_entities": top_entities,
            "summary_text": f"You read {minutes} min across {reads_count} stories this week. Main focus: {', '.join(top_topics) or 'Technology'}.",
        }

    # ------------------------------------------------------------------ selection
    @staticmethod
    def _editorial(signal_score: float) -> float:
        return max(0.0, min(1.0, ((signal_score or 0) - 60.0) / 40.0))

    @staticmethod
    def _similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
        ents = jaccard({e.lower() for e in a["entities"]}, {e.lower() for e in b["entities"]})
        return 0.7 * jaccard(a["kwset"], b["kwset"]) + 0.3 * ents

    def _days_old(self, issue_date: str, latest: str) -> int:
        try:
            return max(0, (dt.date.fromisoformat(latest) - dt.date.fromisoformat(issue_date)).days)
        except ValueError:
            return 0

    def select(self, user_id: Optional[int], local_hour: Optional[int] = None) -> Dict[str, Any]:
        """Scores every pooled card for this reader and picks five. Returns picks plus context."""
        bc = BRIEF.get(self.brief_db_path)
        if not bc.articles:
            return {"picks": [], "pool_size": 0, "latest": None}
        latest = bc.dates[0]
        part = daypart(local_hour)
        aff = self.rec.affinities(user_id) if user_id else {}
        state = self.rec._user_state(user_id) if user_id else {}
        fl = follows_mod.list_follows(user_id, self.foryou_db_path) if user_id else []
        confidence = self.rec.confidence(user_id) if user_id else 0.0

        scored = []
        for cid, a in bc.articles.items():
            st = state.get(cid, {})
            if st.get("hidden"):
                continue
            days_old = self._days_old(a["issue_date"], latest)
            if days_old and st.get("clicked"):
                continue  # read yesterday's card already: don't bring it back
            content, best = self.rec._content(a, aff, part) if aff else (0.0, {})
            followed = follows_mod.match_any(fl, a) if fl else None
            score = (self.EDITORIAL_WEIGHT * self._editorial(a["signal_score"])
                     + confidence * self.PERSONAL_WEIGHT * content
                     + (self.FOLLOW_BONUS if followed else 0.0)
                     - self.AGE_PENALTY * days_old
                     - (self.READ_PENALTY if st.get("clicked") else 0.0))
            scored.append({"id": cid, "a": a, "score": score, "personal": confidence * self.PERSONAL_WEIGHT * content,
                           "best": best, "followed": followed, "days_old": days_old})

        picks: List[Dict[str, Any]] = []
        # Must-know: today's top core card, for everyone.
        today_core = [x for x in scored if x["days_old"] == 0 and x["a"]["tier"] == "core"]
        if today_core:
            top = max(today_core, key=lambda x: x["a"]["signal_score"] or 0)
            top["slot"] = "must_know"
            picks.append(top)
        rest = [x for x in scored if not picks or x["id"] != picks[0]["id"]]
        while rest and len(picks) < self.SLOTS:
            def mmr(x):
                sim = max((self._similarity(x["a"], p["a"]) for p in picks), default=0.0)
                return x["score"] - self.DIVERSITY * sim
            best_x = max(rest, key=mmr)
            best_x["slot"] = "personal" if user_id else "editorial"
            picks.append(best_x)
            rest.remove(best_x)
        return {"picks": picks, "pool_size": len(scored), "latest": latest, "part": part}

    def _why(self, x: Dict[str, Any], part: str) -> str:
        if x.get("slot") == "must_know":
            why = "Today's top shift. Everyone gets this one"
        elif x["followed"]:
            why = follows_mod.describe(x["followed"])
        elif x["personal"] > 0.08:
            why = self.rec._explain(x["a"], x["best"], 0.0, None, part)["text"]
        elif x["a"]["tier"] == "pool":
            why = "Passed the same signal and verification bar as today's top 5"
        else:
            why = "High-signal shift"
        if x["days_old"]:
            why += f" · from {x['a']['issue_date']}"
        return why

    def get_your_5(self, user_id: Optional[int], local_hour: Optional[int] = None) -> Dict[str, Any]:
        """
        The personalised Your 5: role, five cards with the role's impact view, falsifiable
        prediction and action, plus "Safely Ignore Today" and satisfaction state.
        """
        issue = self.brief_db.get_latest_issue()
        if not issue or not issue.cards:
            return {"error": "No daily issue available", "cards": []}

        if not user_id:
            role, confidence, reason = DEFAULT_ROLE, 0.3, "Default perspective for visitors"
            digest, user_state = None, {}
        else:
            role, confidence, reason = infer_role(self.rec.affinities(user_id))
            digest = self.get_weekly_digest(user_id)
            user_state = self.rec._user_state(user_id)

        sel = self.select(user_id, local_hour)
        bc = BRIEF.get(self.brief_db_path)
        formatted_cards = []
        for x in sel["picks"]:
            card = bc.cards[x["id"]]
            role_view = card.role_views.get(role) or card.role_views.get("developer")
            st = user_state.get(card.id, {})
            formatted_cards.append({
                "id": card.id,
                "headline": card.headline,
                "what_happened": card.what_happened,
                "why_it_matters": card.why_it_matters,
                "second_order": card.second_order,
                "signal_score": card.signal_score,
                "signal_level": card.signal_level,
                "signal_reason": card.signal_reason,
                "confidence": card.confidence,
                "action_type": card.action_type,
                "action_text": card.action_text,
                "inferred_role": role,
                "slot": x["slot"],
                "tier": x["a"]["tier"],
                "issue_date": x["a"]["issue_date"],
                "topics": list(x["a"]["topics"].keys()),
                "entities": x["a"]["entities"][:4],
                "followed": x["followed"]["label"] if x["followed"] else None,
                "role_view": {
                    "impact": role_view.impact if role_view else "",
                    "action_type": role_view.action_type if role_view else card.action_type,
                    "action_text": role_view.action_text if role_view else card.action_text,
                    "stakes": role_view.stakes if role_view else None,
                },
                "all_role_views": {
                    r: {"impact": rv.impact, "action_type": rv.action_type,
                        "action_text": rv.action_text, "stakes": rv.stakes}
                    for r, rv in card.role_views.items()
                },
                "prediction": {
                    "id": card.prediction.id,
                    "statement": card.prediction.statement,
                    "probability": card.prediction.probability,
                    "resolves_at": card.prediction.resolves_at,
                    "resolution_criteria": card.prediction.resolution_criteria,
                    "status": card.prediction.status,
                    "category": card.prediction.category,
                } if card.prediction else None,
                "evidence_links": [
                    {"title": el.title, "url": el.url, "publisher": el.publisher, "tier": el.tier}
                    for el in card.evidence_links
                ],
                "why_chosen": self._why(x, sel["part"]),
                "user_state": {
                    "clicked": bool(st.get("clicked")),
                    "saved": bool(st.get("saved")),
                    "reaction": st.get("reaction", 0) or 0,
                },
            })

        not_included = [
            {"headline": ni.headline, "reason": ni.reason, "source_url": ni.source_url}
            for ni in issue.not_included_today
        ]
        return {
            "date": issue.date,
            "beat": issue.beat,
            "inferred_role": role,
            "role_confidence": confidence,
            "role_reason": reason,
            "pool_size": sel["pool_size"],
            "depth": effective_depth(user_id, self.foryou_db_path),
            "cards": formatted_cards,
            "not_included_today": not_included,
            "weekly_digest": digest,
        }
