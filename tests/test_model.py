"""
Unit tests for Daily Tech Intelligence Brief domain models, scoring, verification, and ledger.
"""

import unittest
import os
from core.models import Card, RoleView, Prediction, Claim, DailyIssue, NotIncludedStory
from core.scoring import ScoringEngine
from core.verification import VerificationEngine
from core.ledger import LedgerEngine
from core.db import Database


class TestDomainModels(unittest.TestCase):
    def test_prediction_validation(self):
        # Valid prediction
        p = Prediction(
            id="p1",
            statement="By 2027-01-01, model price drops 20%",
            probability=0.70,
            resolves_at="2027-01-01",
            resolution_criteria="Pricing page shows $0.80 or lower"
        )
        self.assertEqual(p.validate(), [])

        # Invalid probability
        p_invalid = Prediction(
            id="p2",
            statement="Valid statement",
            probability=1.5,
            resolves_at="2027-01-01",
            resolution_criteria="Some criteria"
        )
        errors = p_invalid.validate()
        self.assertTrue(any("must be between 0.0 and 1.0" in e for e in errors))

    def test_card_validation(self):
        card = Card(
            id="c1",
            date="2026-11-19",
            headline="Sample Headline",
            what_happened="What happened text.",
            why_it_matters="Why it matters text.",
            second_order=["Effect 1", "Effect 2"],
            signal_score=80.0,
            signal_level="High",
            signal_reason="Broad ecosystem impact",
            confidence="High",
            action_type="DO",
            action_text="Action text",
            prediction=Prediction(
                id="pred1",
                statement="Pred statement",
                probability=0.7,
                resolves_at="2027-01-01",
                resolution_criteria="Criteria"
            ),
            role_views={
                "developer": RoleView(impact="dev", action_type="DO", action_text="act dev"),
                "founder": RoleView(impact="founder", action_type="WATCH", action_text="act founder"),
                "investor": RoleView(impact="investor", action_type="IGNORE", action_text="act investor"),
                "everyday": RoleView(impact="plain", action_type="WATCH", action_text="act everyday"),
            }
        )
        self.assertEqual(card.validate(), [])

    def test_daily_issue_max_cards(self):
        # Section 1 & Later: At most 5 cards
        issue = DailyIssue(
            issue_id="iss-1",
            date="2026-11-19",
            cards=[self._make_dummy_card(f"c{i}") for i in range(6)]
        )
        errors = issue.validate()
        self.assertTrue(any("allows at most 5 cards" in e for e in errors))

    def _make_dummy_card(self, cid: str) -> Card:
        return Card(
            id=cid,
            date="2026-11-19",
            headline="H",
            what_happened="W",
            why_it_matters="Y",
            second_order=["1", "2"],
            signal_score=80.0,
            signal_level="High",
            signal_reason="reason",
            confidence="High",
            action_type="DO",
            action_text="A",
            prediction=Prediction(
                id=f"p-{cid}",
                statement="S",
                probability=0.7,
                resolves_at="2027-01-01",
                resolution_criteria="R"
            ),
            role_views={
                "developer": RoleView(impact="i", action_type="DO", action_text="a"),
                "founder": RoleView(impact="i", action_type="DO", action_text="a"),
                "investor": RoleView(impact="i", action_type="DO", action_text="a"),
                "everyday": RoleView(impact="i", action_type="DO", action_text="a"),
            }
        )


class TestScoringEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ScoringEngine()

    def test_high_impact_story_score(self):
        features = {
            "breadth_of_affected_users": 90.0,
            "switching_or_lockin_cost": 85.0,
            "irreversibility": 80.0,
            "source_quality_corroboration": 95.0,
            "novelty_vs_trend": 80.0,
            "time_sensitivity": 70.0,
        }
        score, level, reason, breakdown = self.engine.compute_score(features)
        self.assertGreater(score, 78.0)
        self.assertEqual(level, "High")
        self.assertTrue(self.engine.is_selected(score))

    def test_low_impact_with_penalties(self):
        features = {
            "breadth_of_affected_users": 30.0,
            "switching_or_lockin_cost": 20.0,
            "irreversibility": 10.0,
            "source_quality_corroboration": 40.0,
            "novelty_vs_trend": 20.0,
            "time_sensitivity": 10.0,
        }
        penalties = {
            "press_release_language": True,
            "no_verifiable_facts": True
        }
        score, level, reason, breakdown = self.engine.compute_score(features, penalties)
        self.assertLess(score, 60.0)
        self.assertEqual(level, "Low")
        self.assertFalse(self.engine.is_selected(score))


class TestVerificationEngine(unittest.TestCase):
    def test_claim_quote_verification(self):
        engine = VerificationEngine()
        card = Card(
            id="c_verify",
            date="2026-11-19",
            headline="Headline",
            what_happened="Factual report.",
            why_it_matters="Why it matters.",
            second_order=["A", "B"],
            signal_score=80.0,
            signal_level="High",
            signal_reason="Reason",
            confidence="High",
            action_type="DO",
            action_text="Action",
            prediction=Prediction(
                id="p_v",
                statement="Pred",
                probability=0.7,
                resolves_at="2027-01-01",
                resolution_criteria="Objective criteria verified"
            ),
            role_views={
                "developer": RoleView(impact="dev", action_type="DO", action_text="act"),
                "founder": RoleView(impact="founder", action_type="DO", action_text="act"),
                "investor": RoleView(impact="investor", action_type="DO", action_text="act"),
                "everyday": RoleView(impact="plain", action_type="WATCH", action_text="act"),
            },
            claims=[
                Claim(
                    text="Provider slashed rates by 50%",
                    source_url="https://example.com/source1",
                    quoted_span="provider reduced pricing by 50% across models",
                    verified=True
                ),
                Claim(
                    text="Unverified claim without quote",
                    source_url="https://example.com/source1",
                    quoted_span="this phrase does not exist anywhere",
                    verified=True
                )
            ]
        )

        source_texts = {
            "https://example.com/source1": "Official release: provider reduced pricing by 50% across models effective immediately."
        }

        updated_card, claim_results, issues = engine.verify_card(card, source_texts)
        # One claim must pass and one must be dropped
        self.assertEqual(len(updated_card.claims), 1)
        self.assertEqual(claim_results[0]["verified"], True)
        self.assertEqual(claim_results[1]["verified"], False)
        self.assertIn("Missing" in claim_results[1]["drop_reason"] or "not found" in claim_results[1]["drop_reason"], [True])


class TestLedgerEngine(unittest.TestCase):
    def test_brier_score_and_stats(self):
        predictions = [
            Prediction(id="1", statement="S1", probability=0.8, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),  # error = 0.8 - 1 = -0.2 -> 0.04
            Prediction(id="2", statement="S2", probability=0.7, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),  # error = 0.7 - 1 = -0.3 -> 0.09
            Prediction(id="3", statement="S3", probability=0.6, resolves_at="2026-01-01", resolution_criteria="C", status="wrong"),    # error = 0.6 - 0 = 0.6  -> 0.36
            Prediction(id="4", statement="S4", probability=0.5, resolves_at="2027-01-01", resolution_criteria="C", status="open"),     # open (excluded)
        ]

        # Total sq error for 3 resolved = (0.04 + 0.09 + 0.36) / 3 = 0.49 / 3 = 0.1633
        brier = LedgerEngine.calculate_brier_score(predictions)
        self.assertIsNotNone(brier)
        self.assertAlmostEqual(brier, 0.49 / 3, places=4)

        stats = LedgerEngine.calculate_statistics(predictions)
        self.assertEqual(stats["resolved_count"], 3)
        self.assertEqual(stats["correct_count"], 2)
        self.assertEqual(stats["wrong_count"], 1)
        self.assertAlmostEqual(stats["hit_rate_pct"], 66.7, places=1)
        self.assertTrue(stats["is_preliminary"])  # < 20 sample threshold

    def test_calibration_bucket_boundaries(self):
        # Test boundary values (0.50, 0.60, 0.70, 0.80, 0.90, 1.0)
        predictions = [
            Prediction(id="b1", statement="S", probability=0.50, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
            Prediction(id="b2", statement="S", probability=0.60, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
            Prediction(id="b3", statement="S", probability=0.70, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
            Prediction(id="b4", statement="S", probability=0.80, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
            Prediction(id="b5", statement="S", probability=0.90, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
            Prediction(id="b6", statement="S", probability=1.00, resolves_at="2026-01-01", resolution_criteria="C", status="correct"),
        ]
        stats = LedgerEngine.calculate_statistics(predictions)
        bins = {b["bucket"]: b["count"] for b in stats["calibration"]}
        self.assertEqual(bins["50–59%"], 1)
        self.assertEqual(bins["60–69%"], 1)
        self.assertEqual(bins["70–79%"], 1)
        self.assertEqual(bins["80–89%"], 1)
        self.assertEqual(bins["90–100%"], 2)


class TestDatabaseIdempotency(unittest.TestCase):
    def test_repeated_issue_saves_do_not_duplicate_stories_or_claims(self):
        test_db = "test_idempotent.sqlite3"
        if os.path.exists(test_db):
            os.remove(test_db)
        try:
            db = Database(test_db)
            card = Card(
                id="c-test",
                date="2026-11-19",
                headline="Headline",
                what_happened="What happened",
                why_it_matters="Why it matters",
                second_order=["A", "B"],
                signal_score=85.0,
                signal_level="High",
                signal_reason="Reason",
                confidence="High",
                action_type="DO",
                action_text="Action",
                prediction=Prediction(
                    id="p-test",
                    statement="Statement",
                    probability=0.75,
                    resolves_at="2027-01-01",
                    resolution_criteria="Criteria"
                ),
                role_views={
                    "developer": RoleView(impact="dev", action_type="DO", action_text="act"),
                    "founder": RoleView(impact="founder", action_type="DO", action_text="act"),
                    "investor": RoleView(impact="investor", action_type="DO", action_text="act"),
                    "everyday": RoleView(impact="plain", action_type="WATCH", action_text="act"),
                },
                claims=[
                    Claim(text="Claim 1", source_url="https://example.com", quoted_span="Span 1")
                ]
            )
            issue = DailyIssue(
                issue_id="iss-test",
                date="2026-11-19",
                cards=[card],
                not_included_today=[
                    NotIncludedStory(headline="Noise 1", reason="Reason 1")
                ]
            )

            # Save once
            db.save_issue(issue)
            loaded_1 = db.get_latest_issue()
            self.assertEqual(len(loaded_1.not_included_today), 1)
            self.assertEqual(len(loaded_1.cards[0].claims), 1)

            # Save second time (must be idempotent, not append duplicate rows)
            db.save_issue(issue)
            loaded_2 = db.get_latest_issue()
            self.assertEqual(len(loaded_2.not_included_today), 1)
            self.assertEqual(len(loaded_2.cards[0].claims), 1)
        finally:
            if os.path.exists(test_db):
                os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
