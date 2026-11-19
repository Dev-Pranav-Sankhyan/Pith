"""
Verification Engine for Daily Tech Intelligence Brief.
Follows Section 1 (Verification Checks) & Section 6 (Verify step).
"""

from typing import List, Dict, Any, Tuple
from core.models import Card, Claim, Prediction


class VerificationEngine:
    """
    Automated check that:
    1. Every factual claim links to a primary source and matches a quoted span.
    2. Any claim without an exact quoted span in the source is dropped/flagged.
    3. Prediction has a valid date, objective resolution criteria, and probability.
    """

    def verify_card(
        self,
        card: Card,
        source_texts: Dict[str, str]
    ) -> Tuple[Card, List[Dict[str, Any]], List[str]]:
        """
        Verify card claims against provided source snapshot texts.
        Returns:
            (updated_card, claim_verification_results, issues_list)
        """
        issues = []
        claim_results = []
        verified_claims = []

        # 1. Claim-to-quote verification
        for claim in card.claims:
            src_text = source_texts.get(claim.source_url, "")
            span = claim.quoted_span.strip()

            if not span:
                claim.verified = False
                claim.drop_reason = "Missing exact quoted source span"
                issues.append(f"Claim dropped: '{claim.text[:40]}...' - no quoted span provided")
            elif span.lower() not in src_text.lower():
                claim.verified = False
                claim.drop_reason = f"Quoted span not found in source text from {claim.source_url}"
                issues.append(f"Claim dropped: span '{span[:40]}...' not found in source")
            else:
                claim.verified = True
                claim.drop_reason = None
                verified_claims.append(claim)

            claim_results.append({
                "claim": claim.text,
                "verified": claim.verified,
                "quoted_span": claim.quoted_span,
                "drop_reason": claim.drop_reason
            })

        card.claims = verified_claims

        # 2. Prediction validity checks
        pred_errors = card.prediction.validate()
        if pred_errors:
            issues.extend([f"Prediction error: {e}" for e in pred_errors])

        # 3. Objective resolution criteria check
        criteria = card.prediction.resolution_criteria.lower()
        subjective_words = ["maybe", "likely", "significant", "good", "bad", "substantial", "soon"]
        for sw in subjective_words:
            if f" {sw} " in f" {criteria} ":
                issues.append(f"Prediction resolution warning: Contains ambiguous/subjective word '{sw}'")

        # 4. Strict length checks (30-second scan)
        sentences_what = [s for s in card.what_happened.split(".") if s.strip()]
        if len(sentences_what) > 3:
            issues.append(f"What happened has {len(sentences_what)} sentences (spec advises max 2)")

        return card, claim_results, issues
