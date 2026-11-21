"""
Prediction Ledger and Calibration Engine for Daily Tech Intelligence Brief.
Follows Section 1 (Prediction Ledger Rules), Section 5.4, and Section 11 (Success Metrics).
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import datetime
from core.models import Prediction


class LedgerEngine:
    """
    Computes public track record statistics:
    - Brier score (BS = 1/N * sum((p - outcome)^2))
    - Hit rate
    - Horizon breakdown (30-day, 90-day, 365-day)
    - Calibration curve across probability buckets
    - Due-prediction queue (resolution itself is human-approved, see pipeline/resolve_predictions.py)
    - Sample size safeguards

    Only predictions with provenance == "live" count toward the public record.
    Illustrative/seed predictions are summarised separately and never blended in.
    """

    MIN_CALIBRATION_SAMPLE = 20  # Section 1: threshold before calibration is marked definitive

    @staticmethod
    def get_horizon(p: Prediction) -> str:
        """
        Classifies prediction into 30-day, 90-day, or 365-day horizon based on resolves_at - made_at.
        """
        try:
            d_made = datetime.date.fromisoformat(str(p.made_at)[:10])
            d_resolves = datetime.date.fromisoformat(str(p.resolves_at)[:10])
            days = (d_resolves - d_made).days
            if days <= 45:
                return "30-day"
            elif days <= 120:
                return "90-day"
            else:
                return "365-day"
        except (ValueError, TypeError):
            return "365-day"

    @classmethod
    def calculate_horizon_breakdown(cls, predictions: List[Prediction]) -> Dict[str, Dict[str, Any]]:
        """
        Computes count, hit rate, and Brier score segmented by forecast horizon.
        """
        by_horizon: Dict[str, List[Prediction]] = {"30-day": [], "90-day": [], "365-day": []}
        for p in predictions:
            h = cls.get_horizon(p)
            by_horizon.setdefault(h, []).append(p)

        stats = {}
        for h, preds in by_horizon.items():
            resolved = [p for p in preds if p.status in ("correct", "wrong")]
            correct = [p for p in resolved if p.status == "correct"]
            brier = cls.calculate_brier_score(preds)
            stats[h] = {
                "total": len(preds),
                "resolved": len(resolved),
                "open": len([p for p in preds if p.status == "open"]),
                "correct": len(correct),
                "wrong": len(resolved) - len(correct),
                "hit_rate_pct": round(len(correct) / len(resolved) * 100, 1) if resolved else None,
                "brier_score": round(brier, 4) if brier is not None else None,
            }
        return stats

    @classmethod
    def get_due_predictions(cls, predictions: List[Prediction], as_of_date: Optional[str] = None) -> List[Prediction]:
        """
        Returns open predictions whose resolves_at date is due or past due as of a given date.
        """
        today = as_of_date or datetime.date.today().isoformat()
        return [p for p in predictions if p.status == "open" and str(p.resolves_at)[:10] <= today]

    @staticmethod
    def resolve_prediction(
        prediction: Prediction,
        status: str,
        evidence_url: str,
        postmortem: str,
        resolved_at: Optional[str] = None
    ) -> Prediction:
        """
        Resolves an open prediction with verifiable evidence and post-mortem audit notes.
        """
        if status not in ("correct", "wrong", "void"):
            raise ValueError(f"Invalid resolution status: {status}")
        prediction.status = status
        prediction.evidence_url = evidence_url
        prediction.postmortem = postmortem
        prediction.resolved_at = resolved_at or datetime.date.today().isoformat()
        return prediction

    @staticmethod
    def calculate_brier_score(predictions: List[Prediction]) -> Optional[float]:
        """
        Calculates the mean squared error between forecast probability and binary outcome.
        Outcome = 1.0 if 'correct', 0.0 if 'wrong'.
        Void predictions are excluded.
        """
        resolved = [p for p in predictions if p.status in ("correct", "wrong")]
        if not resolved:
            return None

        total_sq_error = 0.0
        for p in resolved:
            outcome = 1.0 if p.status == "correct" else 0.0
            error = p.probability - outcome
            total_sq_error += error * error

        return total_sq_error / len(resolved)

    @staticmethod
    def is_live(p: Prediction) -> bool:
        return getattr(p, "provenance", "live") == "live"

    @classmethod
    def calculate_statistics(cls, predictions: List[Prediction]) -> Dict[str, Any]:
        """
        Public track-record stats over LIVE predictions only, plus a clearly separate
        summary of illustrative predictions (never mixed into the headline numbers).
        """
        live = [p for p in predictions if cls.is_live(p)]
        illustrative = [p for p in predictions if not cls.is_live(p)]
        stats = cls._stats_for(live)
        ill_resolved = [p for p in illustrative if p.status in ("correct", "wrong")]
        stats["illustrative"] = {
            "count": len(illustrative),
            "resolved": len(ill_resolved),
            "note": "Hand-written examples to preview the Ledger. Not forecasts Pith published; excluded from all scores.",
        }
        return stats

    @classmethod
    def _stats_for(cls, predictions: List[Prediction]) -> Dict[str, Any]:
        total = len(predictions)
        open_preds = [p for p in predictions if p.status == "open"]
        correct_preds = [p for p in predictions if p.status == "correct"]
        wrong_preds = [p for p in predictions if p.status == "wrong"]
        void_preds = [p for p in predictions if p.status == "void"]

        resolved_count = len(correct_preds) + len(wrong_preds)
        hit_rate = (len(correct_preds) / resolved_count) if resolved_count > 0 else 0.0
        brier = cls.calculate_brier_score(predictions)

        # Build calibration buckets: 0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0
        buckets = [
            {"label": "50–59%", "min": 0.50, "max": 0.60, "predicted": [], "outcomes": []},
            {"label": "60–69%", "min": 0.60, "max": 0.70, "predicted": [], "outcomes": []},
            {"label": "70–79%", "min": 0.70, "max": 0.80, "predicted": [], "outcomes": []},
            {"label": "80–89%", "min": 0.80, "max": 0.90, "predicted": [], "outcomes": []},
            {"label": "90–100%", "min": 0.90, "max": 1.001, "predicted": [], "outcomes": []},
        ]

        for p in (correct_preds + wrong_preds):
            prob = p.probability
            outcome = 1 if p.status == "correct" else 0
            for b in buckets:
                if b["min"] <= prob < b["max"]:
                    b["predicted"].append(prob)
                    b["outcomes"].append(outcome)
                    break

        calibration_chart = []
        for b in buckets:
            count = len(b["predicted"])
            avg_pred = (sum(b["predicted"]) / count) if count > 0 else (b["min"] + b["max"]) / 2
            actual_rate = (sum(b["outcomes"]) / count) if count > 0 else 0.0
            calibration_chart.append({
                "bucket": b["label"],
                "count": count,
                "avg_forecast": round(avg_pred * 100, 1),
                "actual_rate": round(actual_rate * 100, 1) if count > 0 else None,
                "calibration_gap": round((actual_rate - avg_pred) * 100, 1) if count > 0 else None
            })

        is_preliminary = resolved_count < cls.MIN_CALIBRATION_SAMPLE

        # Skill vs. a naive forecaster that always says the observed base rate.
        # BSS > 0 means the probabilities carried information beyond "how often things happen".
        brier_skill = None
        if resolved_count and brier is not None:
            base = len(correct_preds) / resolved_count
            ref = base * (1 - base)
            brier_skill = round(1 - brier / ref, 3) if ref > 0 else None

        return {
            "total_predictions": total,
            "open_count": len(open_preds),
            "resolved_count": resolved_count,
            "correct_count": len(correct_preds),
            "wrong_count": len(wrong_preds),
            "void_count": len(void_preds),
            "hit_rate_pct": round(hit_rate * 100, 1) if resolved_count > 0 else None,
            "brier_score": round(brier, 4) if brier is not None else None,
            "brier_benchmark": "Target < 0.25 (better than chance)",
            "brier_skill_score": brier_skill,
            "is_preliminary": is_preliminary,
            "min_sample_threshold": cls.MIN_CALIBRATION_SAMPLE,
            "horizon_breakdown": cls.calculate_horizon_breakdown(predictions),
            "calibration": calibration_chart,
        }
