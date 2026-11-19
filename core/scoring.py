"""
Scoring Engine for Daily Tech Intelligence Brief.
Follows Section 6 (Content Pipeline - Scoring) and Section 1 (Signal Level).
"""

from typing import Dict, Tuple, List, Optional
from core.models import SignalLevel


DEFAULT_WEIGHTS = {
    "breadth_of_affected_users": 0.25,     # Developers or companies touched
    "switching_or_lockin_cost": 0.20,      # Prices, APIs, licences, standards
    "irreversibility": 0.15,               # One-way doors score higher
    "source_quality_corroboration": 0.15,  # Primary source present, independent confirmation
    "novelty_vs_trend": 0.15,              # Penalise rehashes
    "time_sensitivity": 0.10,              # Is there an action window?
}

# Penalty weights (subtracted from score)
PENALTIES = {
    "press_release_language": 12.0,
    "no_verifiable_facts": 25.0,
    "pure_product_review": 15.0,
}


class ScoringEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None, threshold: float = 60.0):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.threshold = threshold

    def compute_score(
        self,
        features: Dict[str, float],
        penalties: Optional[Dict[str, bool]] = None
    ) -> Tuple[float, SignalLevel, str, List[str]]:
        """
        Features are rated 0 to 100 on each dimension.
        Penalties are boolean flags indicating low-signal noise.
        
        Returns:
            (numeric_score, signal_level, primary_reason, applied_notes)
        """
        raw_score = 0.0
        breakdown_notes = []

        for key, weight in self.weights.items():
            val = float(features.get(key, 50.0))
            clamped_val = max(0.0, min(100.0, val))
            contribution = clamped_val * weight
            raw_score += contribution
            breakdown_notes.append(f"{key}: {clamped_val:.0f} (wt {weight:.0%}) -> +{contribution:.1f}")

        # Apply penalties
        penalty_total = 0.0
        if penalties:
            for p_key, applies in penalties.items():
                if applies and p_key in PENALTIES:
                    p_val = PENALTIES[p_key]
                    penalty_total += p_val
                    breakdown_notes.append(f"Penalty [{p_key}]: -{p_val:.1f}")

        final_score = max(0.0, min(100.0, raw_score - penalty_total))

        # Map to Signal Level (Section 1: High, Medium or Low plus main reason)
        if final_score >= 78.0:
            level: SignalLevel = "High"
        elif final_score >= self.threshold:
            level = "Medium"
        else:
            level = "Low"

        reason = self._determine_reason(features, level, final_score)
        return final_score, level, reason, breakdown_notes

    def _determine_reason(self, features: Dict[str, float], level: SignalLevel, score: float) -> str:
        # Determine dominant high or low factor
        sorted_factors = sorted(
            self.weights.keys(),
            key=lambda k: features.get(k, 50.0) * self.weights[k],
            reverse=True
        )
        top_factor = sorted_factors[0] if sorted_factors else ""

        factor_phrases = {
            "breadth_of_affected_users": "broad ecosystem-wide impact",
            "switching_or_lockin_cost": "alters switching costs and platform dependencies",
            "irreversibility": "irreversible architectural or strategic shift",
            "source_quality_corroboration": "authoritative primary confirmation",
            "novelty_vs_trend": "breaks from existing industry trajectory",
            "time_sensitivity": "immediate action window for engineering teams",
        }

        phrase = factor_phrases.get(top_factor, "material shift in AI/developer infrastructure")

        if level == "High":
            return f"Broad industry impact ({phrase})"
        elif level == "Medium":
            return f"Relevant architectural development ({phrase})"
        else:
            return f"Incremental update below cutoff threshold ({score:.0f}/100)"

    def is_selected(self, score: float) -> bool:
        """Section 6: Clusters above threshold qualify."""
        return score >= self.threshold
