"""
Compare A/B variants of the For You ranker (core/experiments.py).

    python3 -m pipeline.experiment_report

Per variant:
  * readers exposed
  * satisfaction rate: "worth my time" / (worth + not worth), from current ratings
  * worth-my-time per 100 impressions
  * 7-day return: of readers first exposed 8+ days ago, the share active again on days 1-7
Differences in the two rates get a two-proportion z-test. Small samples are flagged rather
than declared: with fewer than MIN_READERS per variant the report says "not enough data".
Clicks are reported for context only; they are never the decision metric.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any, Dict, List, Optional

from core.experiments import EXPERIMENTS
from core.newsfeed import FOR_YOU_DB, connect

MIN_READERS = 30


def _z_test(s1: int, n1: int, s2: int, n2: int) -> Optional[float]:
    """Two-sided p-value for a difference in proportions, or None if undefined."""
    if not n1 or not n2:
        return None
    p = (s1 + s2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (s1 / n1 - s2 / n2) / se
    return round(math.erfc(abs(z) / math.sqrt(2)), 4)


def variant_metrics(experiment: str, db_path: str = FOR_YOU_DB, now: Optional[dt.datetime] = None) -> List[Dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    with connect(db_path) as conn:
        for variant in sorted(EXPERIMENTS[experiment]["variants"]):
            users = [dict(r) for r in conn.execute(
                "SELECT user_id, first_seen FROM experiment_exposures WHERE experiment=? AND variant=?",
                (experiment, variant))]
            ids = [u["user_id"] for u in users]
            m: Dict[str, Any] = {"variant": variant, "readers": len(ids)}
            if ids:
                marks = ",".join("?" * len(ids))
                worth = conn.execute(f"SELECT COUNT(*) FROM user_articles WHERE reaction=1 AND user_id IN ({marks})", ids).fetchone()[0]
                not_worth = conn.execute(f"SELECT COUNT(*) FROM user_articles WHERE reaction=-1 AND user_id IN ({marks})", ids).fetchone()[0]
                impressions = conn.execute(f"SELECT COUNT(*) FROM events WHERE kind='impression' AND user_id IN ({marks})", ids).fetchone()[0]
                clicks = conn.execute(f"SELECT COUNT(*) FROM events WHERE kind='click' AND user_id IN ({marks})", ids).fetchone()[0]
                eligible = returned = 0
                for u in users:
                    first = dt.datetime.fromisoformat(u["first_seen"])
                    if now - first < dt.timedelta(days=8):
                        continue
                    eligible += 1
                    start, end = first + dt.timedelta(days=1), first + dt.timedelta(days=8)
                    if conn.execute("SELECT 1 FROM events WHERE user_id=? AND created_at >= ? AND created_at < ? LIMIT 1",
                                    (u["user_id"], start.isoformat(timespec="seconds"),
                                     end.isoformat(timespec="seconds"))).fetchone():
                        returned += 1
                rated = worth + not_worth
                m.update({
                    "worth": worth, "rated": rated,
                    "satisfaction_rate": round(worth / rated, 3) if rated else None,
                    "worth_per_100_impressions": round(100 * worth / impressions, 2) if impressions else None,
                    "return_eligible": eligible, "returned": returned,
                    "return_7d": round(returned / eligible, 3) if eligible else None,
                    "clicks_context_only": clicks,
                })
            out.append(m)
    return out


def compare(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(metrics) != 2:
        return {"note": "comparison needs exactly two variants"}
    a, b = metrics
    if min(a["readers"], b["readers"]) < MIN_READERS:
        return {"note": f"not enough data: need {MIN_READERS} readers per variant "
                        f"(have {a['readers']} and {b['readers']})"}
    return {
        "satisfaction_p": _z_test(a.get("worth", 0), a.get("rated", 0), b.get("worth", 0), b.get("rated", 0)),
        "return_7d_p": _z_test(a.get("returned", 0), a.get("return_eligible", 0),
                               b.get("returned", 0), b.get("return_eligible", 0)),
    }


def main() -> None:
    for name, exp in EXPERIMENTS.items():
        print(f"\n{name}: {exp['description']}")
        metrics = variant_metrics(name)
        for m in metrics:
            print("  " + ", ".join(f"{k}={v}" for k, v in m.items()))
        print("  " + ", ".join(f"{k}={v}" for k, v in compare(metrics).items()))


if __name__ == "__main__":
    main()
