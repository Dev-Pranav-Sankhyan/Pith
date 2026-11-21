"""
Offline Personalization Evaluator for Pith.

Replays logged interaction events to rigorously evaluate recommendation quality:
- Splits user event histories chronologically (80% train, 20% test).
- Trains user affinities on past events.
- Evaluates top-K recommendations on held-out user interactions.
- Computes Hit Rate @ 5, Hit Rate @ 10, Mean Reciprocal Rank (MRR), and NDCG@10.
- Compares Pith Personalized Ranker against a Recency-Only Baseline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from core.newsfeed import FOR_YOU_DB, connect
from core.recommender import CORPUS, Recommender


def dcg_at_k(r: List[int], k: int) -> float:
    """Computes Discounted Cumulative Gain at rank k."""
    r = list(r)[:k]
    if not r:
        return 0.0
    return sum((val / math.log2(idx + 2)) for idx, val in enumerate(r))


def ndcg_at_k(r: List[int], k: int) -> float:
    """Computes Normalized Discounted Cumulative Gain at rank k."""
    dcg = dcg_at_k(r, k)
    ideal_r = sorted(r, reverse=True)
    idcg = dcg_at_k(ideal_r, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def evaluate_personalization(db_path: str = FOR_YOU_DB, min_events: int = 5) -> Dict[str, Any]:
    """
    Runs historical replay evaluation across all eligible users in the database.
    """
    corpus = CORPUS.get(db_path)
    rec = Recommender(db_path)

    # 1. Fetch user interactions (clicks, saves, likes)
    with connect(db_path) as conn:
        rows = conn.execute("""
            SELECT user_id, article_id, kind, value, created_at
            FROM events
            WHERE article_id IS NOT NULL AND kind IN ('click', 'like', 'save', 'dwell', 'worth_time')
            ORDER BY created_at ASC
        """).fetchall()

    events_by_user = defaultdict(list)
    for r in rows:
        events_by_user[r["user_id"]].append(dict(r))

    users_evaluated = 0
    metrics = {
        "personalized": {"hr_at_5": 0.0, "hr_at_10": 0.0, "mrr": 0.0, "ndcg_at_10": 0.0},
        "recency_baseline": {"hr_at_5": 0.0, "hr_at_10": 0.0, "mrr": 0.0, "ndcg_at_10": 0.0},
    }

    now = dt.datetime.now(dt.timezone.utc)
    for uid, evs in events_by_user.items():
        # Require minimum positive interactions for train/test split
        pos_events = [e for e in evs if e["kind"] in ("click", "like", "save", "worth_time")]
        if len(pos_events) < min_events:
            continue

        split_idx = int(len(pos_events) * 0.7)
        train_events = pos_events[:split_idx]
        test_events = pos_events[split_idx:]
        train_aids = {e["article_id"] for e in train_events}
        test_aids = {e["article_id"] for e in test_events if e["article_id"] not in train_aids}

        if not test_aids:
            continue

        # Train affinities solely on historical training events
        train_aff: Dict[str, Dict[str, float]] = defaultdict(dict)
        for ev in train_events:
            art = corpus.articles.get(ev["article_id"])
            if not art:
                continue
            delta = 3.5 if ev["kind"] == "worth_time" else (2.0 if ev["kind"] in ("like", "save") else 1.0)
            for t, s in art.get("topics", {}).items():
                train_aff["topic"][t] = train_aff["topic"].get(t, 0.0) + delta * s
            for k, s in art.get("keywords", {}).items():
                train_aff["keyword"][k] = train_aff["keyword"].get(k, 0.0) + delta * s
            for ent in art.get("entities", []):
                train_aff["entity"][ent] = train_aff["entity"].get(ent, 0.0) + delta * 0.8

        # Rank all candidate articles outside the training set
        p_scores = []
        b_scores = []
        for aid, a in corpus.articles.items():
            if aid in train_aids:
                continue
            content, _ = rec._content(a, train_aff, "afternoon")
            recency = rec._recency(a, now)
            p_scores.append((1.6 * content + 0.35 * recency, aid))
            b_scores.append((recency, aid))

        p_scores.sort(key=lambda x: -x[0])
        b_scores.sort(key=lambda x: -x[0])

        p_recs = [aid for _, aid in p_scores[:30]]
        b_recs = [aid for _, aid in b_scores[:30]]

        users_evaluated += 1

        for model_name, ranked_ids in [("personalized", p_recs), ("recency_baseline", b_recs)]:
            # Hit Rate @ 5
            top5 = ranked_ids[:5]
            if any(aid in test_aids for aid in top5):
                metrics[model_name]["hr_at_5"] += 1.0

            # Hit Rate @ 10
            top10 = ranked_ids[:10]
            if any(aid in test_aids for aid in top10):
                metrics[model_name]["hr_at_10"] += 1.0

            # MRR
            first_hit_rank = next((idx + 1 for idx, aid in enumerate(ranked_ids) if aid in test_aids), None)
            if first_hit_rank:
                metrics[model_name]["mrr"] += 1.0 / first_hit_rank

            # NDCG @ 10
            relevance = [1 if aid in test_aids else 0 for aid in top10]
            metrics[model_name]["ndcg_at_10"] += ndcg_at_k(relevance, 10)

    if users_evaluated > 0:
        for m in metrics.values():
            for k in m:
                m[k] = round(m[k] / users_evaluated, 4)

    # Compute percentage lifts
    lifts = {}
    for k in ["hr_at_5", "hr_at_10", "mrr", "ndcg_at_10"]:
        base = metrics["recency_baseline"][k]
        pers = metrics["personalized"][k]
        lift = ((pers - base) / base * 100.0) if base > 0 else 0.0
        lifts[k] = round(lift, 1)

    return {
        "users_evaluated": users_evaluated,
        "metrics": metrics,
        "lifts_pct": lifts,
    }


def print_evaluation_report(results: Dict[str, Any]) -> None:
    print("=" * 65)
    print("✦ PITH RECOMMENDATION SYSTEM — OFFLINE REPLAY EVALUATION")
    print("=" * 65)
    print(f"Users Evaluated: {results['users_evaluated']}")
    print("-" * 65)
    print(f"{'Metric':<15} | {'Recency Baseline':<18} | {'Personalized Ranker':<20} | {'Lift'}")
    print("-" * 65)
    m = results["metrics"]
    lifts = results["lifts_pct"]
    print(f"{'Hit Rate @ 5':<15} | {m['recency_baseline']['hr_at_5']:<18.4f} | {m['personalized']['hr_at_5']:<20.4f} | +{lifts['hr_at_5']}%")
    print(f"{'Hit Rate @ 10':<15} | {m['recency_baseline']['hr_at_10']:<18.4f} | {m['personalized']['hr_at_10']:<20.4f} | +{lifts['hr_at_10']}%")
    print(f"{'MRR':<15} | {m['recency_baseline']['mrr']:<18.4f} | {m['personalized']['mrr']:<20.4f} | +{lifts['mrr']}%")
    print(f"{'NDCG @ 10':<15} | {m['recency_baseline']['ndcg_at_10']:<18.4f} | {m['personalized']['ndcg_at_10']:<20.4f} | +{lifts['ndcg_at_10']}%")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Pith Recommender Personalization")
    parser.add_argument("--db", default=FOR_YOU_DB, help="Path to foryou.sqlite3")
    args = parser.parse_args()
    res = evaluate_personalization(args.db)
    print_evaluation_report(res)
