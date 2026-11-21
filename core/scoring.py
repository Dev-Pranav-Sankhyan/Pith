"""
Scoring Engine for Daily Tech Intelligence Brief.
Follows Section 6 (Content Pipeline - Scoring) and Section 1 (Signal Level).
"""

from typing import Dict, Tuple, List, Optional
import json
import os
import re
from urllib.parse import urlparse
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

# Domains considered authoritative primary sources
PRIMARY_DOMAINS = {
    "github.com", "arxiv.org", "linuxfoundation.org", "w3.org", "ietf.org",
    "postgresql.org", "python.org", "pytorch.org", "kernel.org", "sec.gov",
    "ftc.gov", "europa.eu", "aws.amazon.com", "cloud.google.com", "openai.com",
    "anthropic.com", "deepmind.google", "developer.apple.com", "developer.nvidia.com"
}

# Regex patterns for empirical signal grounding
_PRICE_RE = re.compile(r"(\$\d+|\bpricing\b|\bdiscount\b|\bper[\s-]token\b|\bcost[\s-]reduction\b|\brate[\s-]limit\b|\bfree[\s-]tier\b)", re.IGNORECASE)
_API_RE = re.compile(r"(\bv\d+\.\d+|\bdeprecat\b|\bbreaking[\s-]change\b|\brfc\b|\bjson-rpc\b|\bprotocol\b|\bspecification\b|\bstandard\b|\bsdk\b|\bendpoint\b)", re.IGNORECASE)
_ECOSYSTEM_RE = re.compile(r"\b(pytorch|kubernetes|postgres|postgresql|sqlite|chromium|cuda|docker|linux|rust|golang|vllm|sglang|huggingface)\b", re.IGNORECASE)
_FLUFF_RE = re.compile(r"\b(thrilled to announce|game[\s-]changer|next[\s-]gen revolution|paradigm shift|seamlessly empower|unparalleled synergy)\b", re.IGNORECASE)


def extract_grounded_features(
    text: str,
    url: str = "",
    publisher: str = "",
    outlet_count: int = 1,
    llm_features: Optional[Dict[str, float]] = None
) -> Tuple[Dict[str, float], Dict[str, bool]]:
    """
    Extracts empirical, measurable indicators to ground the 6-factor signal score:
    - Primary source domain authority (arxiv, github, official RFC, cloud docs)
    - Multi-outlet independent corroboration count
    - Verifiable API, price, standard, or architectural changes
    - Automated detection of marketing/PR fluff penalties
    """
    domain = urlparse(url).netloc.lower().replace("www.", "")
    is_primary_domain = any(p in domain for p in PRIMARY_DOMAINS)

    # 1. Source Quality Corroboration (Anchored empirically)
    base_source_quality = 90.0 if is_primary_domain else 60.0
    outlet_boost = min(30.0, max(0, outlet_count - 1) * 12.0)
    empirical_source_quality = min(100.0, base_source_quality + outlet_boost)

    # 2. Switching or Lock-in Cost (Detected from pricing / API / licensing text)
    has_price_change = bool(_PRICE_RE.search(text))
    has_api_change = bool(_API_RE.search(text))
    empirical_lockin = 50.0
    if has_price_change and has_api_change:
        empirical_lockin = 88.0
    elif has_price_change or has_api_change:
        empirical_lockin = 76.0

    # 3. Breadth of Impact (Detected from major platforms / ecosystems affected)
    ecosystem_matches = len(set(_ECOSYSTEM_RE.findall(text.lower())))
    empirical_breadth = min(95.0, 50.0 + ecosystem_matches * 15.0)

    # 4. Irreversibility & Novelty
    empirical_irreversibility = 75.0 if ("standard" in text.lower() or "protocol" in text.lower()) else 55.0
    empirical_novelty = 70.0 if is_primary_domain else 55.0
    empirical_time_sensitivity = 75.0 if has_price_change or has_api_change else 50.0

    empirical_features = {
        "source_quality_corroboration": empirical_source_quality,
        "switching_or_lockin_cost": empirical_lockin,
        "breadth_of_affected_users": empirical_breadth,
        "irreversibility": empirical_irreversibility,
        "novelty_vs_trend": empirical_novelty,
        "time_sensitivity": empirical_time_sensitivity,
    }

    # Blend empirical signals with LLM features (50/50) if provided, grounding the model in data
    final_features = {}
    for key, emp_val in empirical_features.items():
        if llm_features and key in llm_features:
            final_features[key] = round(0.5 * emp_val + 0.5 * float(llm_features[key]), 1)
        else:
            final_features[key] = emp_val

    # Penalties
    penalties = {
        "press_release_language": bool(_FLUFF_RE.search(text)),
        "no_verifiable_facts": (not has_price_change and not has_api_change and ecosystem_matches == 0),
        "pure_product_review": bool("review:" in text.lower() or "hands-on with" in text.lower())
    }

    return final_features, penalties


TUNED_WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scoring_weights.json")


def load_weights(path: str = TUNED_WEIGHTS_PATH) -> Dict[str, float]:
    """Outcome-tuned weights from pipeline/tune_scoring.py if present and valid, else defaults."""
    try:
        with open(path) as fh:
            w = json.load(fh).get("weights", {})
        if set(w) == set(DEFAULT_WEIGHTS) and abs(sum(w.values()) - 1.0) < 0.02 and min(w.values()) > 0:
            return {k: float(v) for k, v in w.items()}
    except (OSError, ValueError, AttributeError):
        pass
    return DEFAULT_WEIGHTS.copy()


class ScoringEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None, threshold: float = 60.0):
        self.weights = weights or load_weights()
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

    def tune_weights(self, correlations: Dict[str, float]) -> None:
        """
        Nudges weights by per-factor correlations (see outcome_correlations) and
        re-normalizes so they sum to 1.0. Feed it outcome data only, never clicks
        or saves: ranking for engagement is what Pith exists to avoid.
        """
        for factor, delta in correlations.items():
            if factor in self.weights:
                self.weights[factor] = max(0.05, self.weights[factor] + delta * 0.05)
        # Re-normalize
        total = sum(self.weights.values())
        if total > 0:
            for factor in self.weights:
                self.weights[factor] = round(self.weights[factor] / total, 3)


MIN_TUNING_SAMPLE = 20


def outcome_correlations(rows: List[Dict], min_sample: int = MIN_TUNING_SAMPLE) -> Dict[str, float]:
    """
    Pearson correlation (point-biserial) between each factor rating and whether the
    story's forecast resolved correct. Returns {} below `min_sample` resolved
    forecasts, so weights never move on noise.

    rows: [{"outcome": 0.0|1.0, "factors": {factor: 0-100}}], e.g. Database.get_factor_outcomes().
    """
    if len(rows) < min_sample:
        return {}
    ys = [r["outcome"] for r in rows]
    out: Dict[str, float] = {}
    for factor in DEFAULT_WEIGHTS:
        xs = [float(r["factors"].get(factor, 50.0)) for r in rows]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        if sxx == 0 or syy == 0:
            continue
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        out[factor] = round(sxy / (sxx * syy) ** 0.5, 3)
    return out
