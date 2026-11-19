"""
Prediction Ledger and Calibration Engine for Daily Tech Intelligence Brief.
Follows Section 1 (Prediction Ledger Rules), Section 5.4, and Section 11 (Success Metrics).
"""

from typing import List, Dict, Any, Optional
import math
from core.models import Prediction


class LedgerEngine:
    """
    Computes public track record statistics:
    - Brier score (BS = 1/N * sum((p - outcome)^2))
    - Hit rate
    - Calibration curve across probability buckets
    - Sample size safeguards
    """

    MIN_CALIBRATION_SAMPLE = 20  # Section 1: threshold before calibration is marked definitive

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

    @classmethod
    def calculate_statistics(cls, predictions: List[Prediction]) -> Dict[str, Any]:
        """
        Aggregates summary stats, Brier score, and calibration bins.
        """
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
            "is_preliminary": is_preliminary,
            "min_sample_threshold": cls.MIN_CALIBRATION_SAMPLE,
            "calibration": calibration_chart,
        }
