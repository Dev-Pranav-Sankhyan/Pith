"""
Core domain models for Daily Tech Intelligence Brief.
Follows Product Spec Version 0.1 draft.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Literal
import datetime

ActionType = Literal["DO", "WATCH", "IGNORE"]
SignalLevel = Literal["High", "Medium", "Low"]
ConfidenceLevel = Literal["High", "Medium", "Low"]
PredictionStatus = Literal["open", "correct", "wrong", "void"]
SourceTier = Literal["primary", "secondary"]


@dataclass
class Source:
    id: str
    url: str
    publisher: str
    tier: SourceTier = "primary"
    fetched_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    snapshot_ref: Optional[str] = None


@dataclass
class Claim:
    text: str
    source_url: str
    quoted_span: str
    verified: bool = True
    drop_reason: Optional[str] = None


@dataclass
class HistoricalAnalogue:
    analogue: str
    where_it_breaks: str


@dataclass
class EvidenceLink:
    title: str
    url: str
    publisher: str = ""
    tier: SourceTier = "primary"
    quoted_span: Optional[str] = None


@dataclass
class Prediction:
    id: str
    statement: str
    probability: float  # 0.0 to 1.0
    resolves_at: str    # YYYY-MM-DD
    resolution_criteria: str
    status: PredictionStatus = "open"
    made_at: str = field(default_factory=lambda: datetime.date.today().isoformat())
    card_id: Optional[str] = None
    category: str = "technology"  # market, technology, adoption
    resolved_at: Optional[str] = None
    evidence_url: Optional[str] = None
    postmortem: Optional[str] = None

    def validate(self) -> List[str]:
        errors = []
        if not (0.0 <= self.probability <= 1.0):
            errors.append(f"Probability {self.probability} must be between 0.0 and 1.0")
        if not self.statement.strip():
            errors.append("Prediction statement cannot be empty")
        if not self.resolution_criteria.strip():
            errors.append("Resolution criteria must be specified (falsifiable standard)")
        if not self.resolves_at:
            errors.append("Resolution date resolves_at is required")
        return errors


@dataclass
class RoleView:
    impact: str
    action_type: ActionType
    action_text: str
    stakes: Optional[str] = None


@dataclass
class Card:
    id: str
    date: str
    headline: str
    what_happened: str
    why_it_matters: str
    second_order: List[str]
    signal_score: float
    signal_level: SignalLevel
    signal_reason: str
    confidence: ConfidenceLevel
    action_type: ActionType
    action_text: str
    prediction: Prediction
    role_views: Dict[str, RoleView]
    beat: str = "AI & Developer Infrastructure"
    cluster_id: Optional[str] = None
    historical_analogue: Optional[HistoricalAnalogue] = None
    evidence_links: List[EvidenceLink] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    published_at: Optional[str] = None

    def validate(self) -> List[str]:
        errors = []
        if not self.headline.strip():
            errors.append("Headline cannot be empty")
        if not self.what_happened.strip():
            errors.append("What happened cannot be empty")
        if self.signal_level not in ("High", "Medium", "Low"):
            errors.append(f"Invalid signal level {self.signal_level}")
        if self.confidence not in ("High", "Medium", "Low"):
            errors.append(f"Invalid confidence {self.confidence}")
        if self.action_type not in ("DO", "WATCH", "IGNORE"):
            errors.append(f"Invalid action type {self.action_type}")
        if not self.prediction:
            errors.append("Card must have an attached prediction")
        else:
            errors.extend(self.prediction.validate())
        for role in ("developer", "founder", "investor", "everyday"):
            if role not in self.role_views:
                errors.append(f"Missing role view: {role}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Card:
        data = data.copy()
        if "prediction" in data and isinstance(data["prediction"], dict):
            data["prediction"] = Prediction(**data["prediction"])
        if "historical_analogue" in data and isinstance(data["historical_analogue"], dict):
            data["historical_analogue"] = HistoricalAnalogue(**data["historical_analogue"])
        if "evidence_links" in data:
            data["evidence_links"] = [
                el if isinstance(el, EvidenceLink) else EvidenceLink(**el)
                for el in data["evidence_links"]
            ]
        if "claims" in data:
            data["claims"] = [
                c if isinstance(c, Claim) else Claim(**c)
                for c in data["claims"]
            ]
        if "role_views" in data:
            data["role_views"] = {
                k: v if isinstance(v, RoleView) else RoleView(**v)
                for k, v in data["role_views"].items()
            }
        return cls(**data)


@dataclass
class NotIncludedStory:
    headline: str
    reason: str
    source_url: Optional[str] = None


@dataclass
class DailyIssue:
    issue_id: str
    date: str
    beat: str = "AI & Developer Infrastructure"
    is_quiet_day: bool = False
    cards: List[Card] = field(default_factory=list)
    not_included_today: List[NotIncludedStory] = field(default_factory=list)
    published_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errors = []
        if len(self.cards) > 5:
            errors.append(f"Issue allows at most 5 cards per day, got {len(self.cards)}")
        if len(self.not_included_today) > 5:
            errors.append(f"Issue allows at most 5 'Not Included' stories, got {len(self.not_included_today)}")
        for c in self.cards:
            errors.extend(c.validate())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DailyIssue:
        data = data.copy()
        if "cards" in data:
            data["cards"] = [
                c if isinstance(c, Card) else Card.from_dict(c)
                for c in data["cards"]
            ]
        if "not_included_today" in data:
            data["not_included_today"] = [
                ni if isinstance(ni, NotIncludedStory) else NotIncludedStory(**ni)
                for ni in data["not_included_today"]
            ]
        return cls(**data)
