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


class ClusterEngine:
    @staticmethod
    def is_match(a: Dict[str, Any], cluster: StoryCluster, window_hours: int = 48) -> bool:
        """
        Determines whether article `a` belongs to existing `cluster`.
        Requires:
        1. Published within window_hours of cluster start
        2. AND either:
           - 2+ shared named entities AND keyword overlap > 0.25
           - Title token Jaccard similarity > 0.38
           - Keyword Jaccard overlap > 0.45
        """
        # Time window check
        try:
            d_art = dt.datetime.fromisoformat(a.get("published_at", "")[:19].replace("Z", "+00:00"))
            d_cluster = dt.datetime.fromisoformat(cluster.published_at[:19].replace("Z", "+00:00"))
            diff_hours = abs((d_art - d_cluster).total_seconds()) / 3600.0
            if diff_hours > window_hours:
                return False
        except (ValueError, TypeError):
            pass

        # 1. Entity overlap
        art_ents = set(a.get("entities", []))
        clust_ents = set(cluster.entities)
        shared_ents = art_ents & clust_ents

        # 2. Title token similarity
        title_tokens_a = set(tokenize(a.get("title", "")))
        title_tokens_c = set(tokenize(cluster.lead_title))
        title_sim = jaccard(title_tokens_a, title_tokens_c)

        # 3. Keyword similarity
        art_kw = a.get("kwset", set())
        clust_kw = cluster.kwset
        kw_sim = jaccard(art_kw, clust_kw)

        if len(shared_ents) >= 2 and (kw_sim > 0.22 or title_sim > 0.28):
            return True

        if title_sim >= 0.38:
            return True

        if kw_sim >= 0.45 and (len(shared_ents) >= 1 or title_sim > 0.20):
            return True

        return False

    @classmethod
    def cluster_articles(cls, articles: List[Dict[str, Any]], window_hours: int = 48) -> List[StoryCluster]:
        """
        Clusters a stream of articles into deduplicated Story Clusters.
        """
        clusters: List[StoryCluster] = []
        # Sort articles by publication date (earliest first for chronological accumulation)
        sorted_articles = sorted(articles, key=lambda x: x.get("published_at", ""))

        for a in sorted_articles:
            matched_cluster: Optional[StoryCluster] = None
            for c in clusters:
                if cls.is_match(a, c, window_hours=window_hours):
                    matched_cluster = c
                    break

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
