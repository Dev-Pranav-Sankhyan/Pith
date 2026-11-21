"""
Your 5 Engine for Pith.

Unifies the Daily Brief and For You recommendation systems:
- Infers reader role (Developer, Founder, Investor, Everyday) from behavioral signals and affinities.
- Personalizes the top 5 high-signal shifts of the day matching the reader's learned taste profile.
- Delivers the full Pith rigor: What Happened, Why It Matters (to your inferred role),
  Falsifiable Prediction, Developer/Professional Action, and What You Can Safely Ignore.
- Captures explicit satisfaction feedback ('Worth my time?').
- Computes weekly reading digest and learned pattern summaries.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any, Dict, List, Optional, Tuple

from core.db import Database
from core.models import Card, DailyIssue
from core.newsfeed import FOR_YOU_DB, connect
from core.recommender import CORPUS, Recommender

# Keyword and topic indicators for behavioral role inference
ROLE_INDICATORS = {
    "developer": {
        "topics": {"Technology": 1.5, "AI": 1.5},
        "keywords": {
            "code", "github", "api", "rpc", "sdk", "inference", "cuda", "latency",
            "vllm", "python", "rust", "framework", "model", "open source", "postgres",
            "postgresql", "kubernetes", "standard", "specification", "benchmark", "compiler",
            "runtime", "endpoint", "architecture", "deprecat", "token"
        },
    },
    "founder": {
        "topics": {"Business": 1.5, "Technology": 1.0, "AI": 1.0},
        "keywords": {
            "startup", "pricing", "launch", "founder", "customer", "saas", "scale",
            "hiring", "product", "market", "cost", "margin", "growth", "revenue",
            "discount", "per-token", "competition", "strategy", "enterprise"
        },
    },
    "investor": {
        "topics": {"Markets": 2.0, "Business": 1.2},
        "keywords": {
            "valuation", "revenue", "funding", "ipo", "round", "shares", "merger",
            "acquisition", "venture", "capital", "stock", "investor", "hedge", "stake",
            "cap", "multiple", "deal", "sec", "earnings", "guidance"
        },
    },
    "everyday": {
        "topics": {"Science": 1.2, "Space": 1.2, "Health": 1.2, "World": 1.0, "Entertainment": 1.0},
        "keywords": {
            "discovery", "research", "climate", "health", "space", "telescope",
            "planet", "study", "general", "culture", "public", "policy"
        },
    },
}


def infer_role(affinities: Dict[str, Dict[str, float]]) -> Tuple[str, float, str]:
    """
    Infers the user's professional lens from their learned affinity vectors.
    Returns: (role, confidence_0_to_1, explanation)
    """
    topic_affs = affinities.get("topic", {})
    keyword_affs = affinities.get("keyword", {})
    entity_affs = affinities.get("entity", {})

    scores = {"developer": 1.0, "founder": 0.8, "investor": 0.6, "everyday": 0.5}

    # Score against topics
    for role, rules in ROLE_INDICATORS.items():
        for top, weight in rules["topics"].items():
            if top in topic_affs:
                scores[role] += max(0.0, topic_affs[top]) * weight

    # Score against keywords
    for role, rules in ROLE_INDICATORS.items():
        for kw, aff_val in keyword_affs.items():
            if any(term in kw.lower() for term in rules["keywords"]):
                scores[role] += max(0.0, aff_val) * 1.4

    total = sum(scores.values()) or 1.0
    sorted_roles = sorted(scores.items(), key=lambda kv: -kv[1])
    top_role, top_score = sorted_roles[0]
    confidence = min(0.95, round(top_score / total + 0.25, 2))

    reasons = {
        "developer": "Inferred from focus on code, APIs, inference runtimes, and engineering architecture",
        "founder": "Inferred from interest in startup pricing, SaaS economics, and product deployment",
        "investor": "Inferred from tracking venture funding, market capitalizations, and strategic acquisitions",
        "everyday": "Inferred from broad interest across technology, scientific exploration, and culture",
    }

    return top_role, confidence, reasons.get(top_role, "Based on your active reading pattern")


class Your5Engine:
    def __init__(self, brief_db_path: str = "brief.sqlite3", foryou_db_path: str = FOR_YOU_DB):
        self.brief_db_path = brief_db_path
        self.foryou_db_path = foryou_db_path
        self.brief_db = Database(brief_db_path)
        self.rec = Recommender(foryou_db_path)

    def get_weekly_digest(self, user_id: int) -> Dict[str, Any]:
        """
        Builds a weekly satisfaction and reading pattern digest.
        """
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

            worth_time_count = conn.execute("""
                SELECT COUNT(*) FROM events
                WHERE user_id=? AND kind='worth_time' AND created_at >= ?
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
            "summary_text": f"You read {minutes} min across {reads_count} shifts this week. Main focus: {', '.join(top_topics) or 'Technology'}.",
        }

    def get_your_5(self, user_id: Optional[int]) -> Dict[str, Any]:
        """
        Assembles the personalized 'Your 5' briefing:
        1. Infers reader role & confidence.
        2. Retrieves the latest verified daily cards and scores them against user affinities.
        3. Ranks and picks the 5 most critical shifts tailored to the user.
        4. Inlines role-specific impact views, falsifiable predictions, and developer actions.
        5. Attaches 'Safely Ignore Today' stories and satisfaction controls.
        """
        issue = self.brief_db.get_latest_issue()
        if not issue or not issue.cards:
            return {"error": "No daily issue available", "cards": []}

        # Anonymous or brand-new cold start default
        if not user_id:
            role = "developer"
            confidence = 0.70
            reason = "Default standard perspective for technology practitioners"
            digest = None
            affinities = {}
            user_state = {}
        else:
            affinities = self.rec.affinities(user_id)
            role, confidence, reason = infer_role(affinities)
            digest = self.get_weekly_digest(user_id)
            user_state = self.rec._user_state(user_id)

        scored_cards = []
        for card in issue.cards:
            score = card.signal_score
            why_match = "Essential high-signal industry shift"

            # Match against user affinities if authenticated
            if affinities:
                card_text = f"{card.headline} {card.what_happened} {card.why_it_matters}".lower()
                topic_bonus = sum(
                    affinities.get("topic", {}).get(t, 0.0) * 2.0
                    for t in affinities.get("topic", {})
                    if t.lower() in card_text
                )
                kw_bonus = sum(
                    affinities.get("keyword", {}).get(k, 0.0) * 1.5
                    for k in affinities.get("keyword", {})
                    if k.lower() in card_text
                )
                score += topic_bonus + kw_bonus
                if topic_bonus > 1.0:
                    matched_topic = next((t for t in affinities.get("topic", {}) if t.lower() in card_text), "")
                    why_match = f"Matched your focus on {matched_topic}"

            scored_cards.append((score, card, why_match))

        # Rank cards descending by combined signal & affinity score
        scored_cards.sort(key=lambda x: -x[0])
        top_5_tuples = scored_cards[:5]

        # Build unified presentation
        formatted_cards = []
        for s, card, why_match in top_5_tuples:
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
                "role_view": {
                    "impact": role_view.impact if role_view else "",
                    "action_type": role_view.action_type if role_view else card.action_type,
                    "action_text": role_view.action_text if role_view else card.action_text,
                    "stakes": role_view.stakes if role_view else None,
                },
                "all_role_views": {
                    r: {
                        "impact": rv.impact,
                        "action_type": rv.action_type,
                        "action_text": rv.action_text,
                        "stakes": rv.stakes
                    }
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
                "why_chosen": why_match,
                "user_state": {
                    "clicked": bool(st.get("clicked")),
                    "saved": bool(st.get("saved")),
                    "reaction": st.get("reaction", 0) or 0,
                }
            })

        # Not included / safely ignore stories
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
            "cards": formatted_cards,
            "not_included_today": not_included,
            "weekly_digest": digest,
        }
