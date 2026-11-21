"""
Story Clustering Engine for Pith.

Groups multi-source news coverage into distinct event clusters:
- Aggregates multi-outlet reports covering the same underlying shift.
- Solves duplicate article leakage in the feed.
- Merges multi-source text to enrich TF-IDF feature density.
- Tracks source diversity and corroboration count per story.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.textfeatures import jaccard, tokenize, tfidf_keywords

# Priority domains for selecting the primary/lead article in a cluster
AUTHORITATIVE_TIERS = {
    "arxiv.org": 100,
    "github.com": 95,
    "linuxfoundation.org": 90,
    "w3.org": 90,
    "postgresql.org": 90,
    "python.org": 90,
    "pytorch.org": 90,
    "sec.gov": 90,
    "ftc.gov": 90,
    "europa.eu": 90,
    "aws.amazon.com": 85,
    "cloud.google.com": 85,
    "openai.com": 85,
    "anthropic.com": 85,
    "deepmind.google": 85,
    "microsoft.com": 85,
    "Ars Technica": 75,
    "MIT Technology Review": 75,
    "Reuters": 75,
    "Bloomberg": 75,
    "BBC News": 70,
    "The Verge": 70,
    "TechCrunch": 65,
    "Hacker News": 65,
}


def _publisher_authority(publisher: str, url: str) -> int:
    for domain, score in AUTHORITATIVE_TIERS.items():
        if domain in url or domain.lower() in publisher.lower():
            return score
    return 50


@dataclass
class StoryCluster:
    id: str
    lead_title: str
    lead_article_id: str
    lead_publisher: str
    lead_url: str
    lead_image_url: Optional[str]
    published_at: str
    articles: List[Dict[str, Any]] = field(default_factory=list)
    publishers: List[str] = field(default_factory=list)
    publisher_count: int = 1
    topics: Dict[str, float] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    keywords: Dict[str, float] = field(default_factory=dict)
    kwset: Set[str] = field(default_factory=set)
    word_count: int = 0
    corroboration_score: float = 0.5  # 0.5 to 1.0 based on multi-outlet corroboration

    def add_article(self, a: Dict[str, Any]) -> None:
        self.articles.append(a)
        pub = a.get("publisher", "Unknown")
        if pub not in self.publishers:
            self.publishers.append(pub)
        self.publisher_count = len(self.publishers)

        # Update lead article if this article comes from a higher-authority source
        current_auth = _publisher_authority(self.lead_publisher, self.lead_url)
        new_auth = _publisher_authority(pub, a.get("url", ""))
        if new_auth > current_auth or (new_auth == current_auth and len(a.get("title", "")) > len(self.lead_title)):
            self.lead_title = a["title"]
            self.lead_article_id = a["id"]
            self.lead_publisher = pub
            self.lead_url = a.get("url", "")
            if a.get("image_url"):
                self.lead_image_url = a["image_url"]

        # Keep earliest published date as canonical event start
        if a.get("published_at") and (not self.published_at or a["published_at"] < self.published_at):
            self.published_at = a["published_at"]

        # Merge entities
        for ent in a.get("entities", []):
            if ent not in self.entities:
                self.entities.append(ent)

        # Merge topics
        for t, wt in a.get("topics", {}).items():
            self.topics[t] = max(self.topics.get(t, 0.0), wt)

        # Merge keyword representations
        for k, wt in a.get("keywords", {}).items():
            self.keywords[k] = max(self.keywords.get(k, 0.0), wt)
        self.kwset = set(list(self.keywords.keys())[:10])

        self.word_count += a.get("word_count", 0)
        # Multi-outlet corroboration score boosts with independent outlets
        self.corroboration_score = min(1.0, 0.4 + 0.15 * self.publisher_count)


_NUM_RE = re.compile(r"\b(?:v?\d+(?:\.\d+)+|\d+%|\$\d[\d,.]*[bmk]?)\b", re.IGNORECASE)


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(w * b.get(k, 0.0) for k, w in a.items())
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _content_tokens(a: Dict[str, Any]) -> Set[str]:
    if "_ctok" not in a:
        a["_ctok"] = set(tokenize(f"{a.get('title', '')} {a.get('summary', '')}"))
    return a["_ctok"]


def _specifics(a: Dict[str, Any]) -> Set[str]:
    """Version numbers, percentages and amounts: strong evidence of the same event."""
    if "_spec" not in a:
        text = f"{a.get('title', '')} {a.get('summary', '')}"
        a["_spec"] = {m.group(0).lower().lstrip("v") for m in _NUM_RE.finditer(text)}
    return a["_spec"]


class ClusterEngine:
    # Pair score needed to join a cluster. Calibrated on tests/fixtures/cluster_gold.json
    # (python3 -m core.cluster_eval); re-check precision there before changing it.
    MATCH_THRESHOLD = 0.18  # gold set: strongest wrong pair 0.064, typical true pair > 0.25

    @staticmethod
    def pair_similarity(a: Dict[str, Any], b: Dict[str, Any], common_entities: Set[str] = frozenset()) -> float:
        """
        0..1 evidence that two articles report the same event. Blends:
          - TF-IDF keyword cosine (rare shared words count most)
          - content-token Jaccard over title + summary
          - shared *distinctive* entities (entities seen across many unrelated stories,
            e.g. a big company name, are ignored so they cannot merge different stories)
          - shared specifics such as "1.35", "50%"
        """
        kw = _cosine(a.get("keywords", {}), b.get("keywords", {}))
        tok = jaccard(_content_tokens(a), _content_tokens(b))
        ents_a = {e.lower() for e in a.get("entities", [])} - common_entities
        ents_b = {e.lower() for e in b.get("entities", [])} - common_entities
        ent = min(1.0, len(ents_a & ents_b) / 2.0)
        spec = 1.0 if (_specifics(a) & _specifics(b)) else 0.0
        return 0.45 * kw + 0.30 * tok + 0.15 * ent + 0.10 * spec

    @staticmethod
    def _within_window(a: Dict[str, Any], cluster: StoryCluster, window_hours: int) -> bool:
        try:
            d_art = dt.datetime.fromisoformat(a.get("published_at", "")[:19].replace("Z", "+00:00"))
            d_cluster = dt.datetime.fromisoformat(cluster.published_at[:19].replace("Z", "+00:00"))
            return abs((d_art - d_cluster).total_seconds()) / 3600.0 <= window_hours
        except (ValueError, TypeError):
            return True

    @classmethod
    def cluster_score(cls, a: Dict[str, Any], cluster: StoryCluster, common_entities: Set[str] = frozenset(),
                      window_hours: int = 48) -> float:
        """Best pair similarity between `a` and any member (not just the lead headline)."""
        if not cls._within_window(a, cluster, window_hours):
            return 0.0
        return max((cls.pair_similarity(a, m, common_entities) for m in cluster.articles), default=0.0)

    @classmethod
    def is_match(cls, a: Dict[str, Any], cluster: StoryCluster, window_hours: int = 48,
                 common_entities: Set[str] = frozenset()) -> bool:
        return cls.cluster_score(a, cluster, common_entities, window_hours) >= cls.MATCH_THRESHOLD

    @staticmethod
    def common_entities(articles: List[Dict[str, Any]], share: float = 0.12, min_count: int = 3) -> Set[str]:
        """Entities appearing in many articles of the batch carry no story identity."""
        counts: Counter = Counter()
        for a in articles:
            counts.update({e.lower() for e in a.get("entities", [])})
        cutoff = max(min_count, share * len(articles))
        return {e for e, n in counts.items() if n >= cutoff}

    @classmethod
    def cluster_articles(cls, articles: List[Dict[str, Any]], window_hours: int = 48) -> List[StoryCluster]:
        """
        Clusters a stream of articles into deduplicated Story Clusters.
        """
        clusters: List[StoryCluster] = []
        # Sort articles by publication date (earliest first for chronological accumulation)
        sorted_articles = sorted(articles, key=lambda x: x.get("published_at", ""))

        common = cls.common_entities(articles)

        for a in sorted_articles:
            # Join the BEST matching cluster, not merely the first one over threshold.
            matched_cluster: Optional[StoryCluster] = None
            best = cls.MATCH_THRESHOLD
            for c in clusters:
                score = cls.cluster_score(a, c, common, window_hours)
                if score >= best:
                    best, matched_cluster = score, c

            if matched_cluster:
                matched_cluster.add_article(a)
            else:
                cid = hashlib.sha1(f"{a['id']}-{a.get('published_at', '')}".encode()).hexdigest()[:12]
                new_cluster = StoryCluster(
                    id=f"cluster-{cid}",
                    lead_title=a["title"],
                    lead_article_id=a["id"],
                    lead_publisher=a.get("publisher", "Unknown"),
                    lead_url=a.get("url", ""),
                    lead_image_url=a.get("image_url"),
                    published_at=a.get("published_at", ""),
                    articles=[a],
                    publishers=[a.get("publisher", "Unknown")],
                    publisher_count=1,
                    topics=dict(a.get("topics", {})),
                    entities=list(a.get("entities", [])),
                    keywords=dict(a.get("keywords", {})),
                    kwset=set(list(a.get("keywords", {}).keys())[:10]),
                    word_count=a.get("word_count", 0),
                    corroboration_score=0.5
                )
                clusters.append(new_cluster)

        # Sort clusters descending by latest publication date
        clusters.sort(key=lambda c: c.published_at, reverse=True)
        return clusters
