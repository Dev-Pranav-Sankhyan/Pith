"""
Pith For You: a hyper-personalised news ranker built from classic, explainable
information-retrieval and recommender techniques. No AI / no trained models.

How it learns
-------------
1. Implicit + explicit signals are logged as events (impression, click, dwell
   time, like, dislike, save, share, hide, mute source, more/less of a topic,
   search queries).
2. Each event updates a per-user *affinity* for every feature of the article:
   its topics, TF-IDF keywords, named entities, publisher, and the topic for
   the reader's current time of day. Affinities decay exponentially
   (half-life 21 days) so the profile tracks changing tastes.

How it ranks
------------
  score = confidence * personal + (1 - confidence) * baseline
  personal = content match (affinity · article features)
           + collaborative filtering (user-user cosine on engagement)
           + recency + popularity − repeat-impression fatigue
  baseline = recency + popularity (used while the profile is still young)

Then:
  * MMR re-ranking for diversity and near-duplicate collapse
  * Thompson-sampling exploration slots for under-explored topics
  * an explanation ("Because you read about …") for every item
"""

from __future__ import annotations

import datetime as dt
import json
import math
import random
import threading
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.newsfeed import FOR_YOU_DB, _write_lock, connect, init_schema, now_iso
from core.clustering import ClusterEngine, StoryCluster
from core.textfeatures import (TOPICS, display_term, estimate_read_seconds, jaccard,
                               tfidf_keywords, tokenize)

# ---------------------------------------------------------------- tunables
HALF_LIFE_DAYS = 21.0
WEIGHT_CLAMP = (-15.0, 25.0)
KIND_LR = {"topic": 1.0, "keyword": 1.0, "entity": 0.8, "source": 0.6, "daypart": 0.5}
CONTENT_MIX = {"topic": 0.34, "keyword": 0.30, "entity": 0.14, "source": 0.12, "daypart": 0.10}
SQUASH = {"topic": 5.0, "keyword": 2.5, "entity": 2.0, "source": 4.0, "daypart": 3.0}

SIGNALS = {
    "impression": -0.04,
    "click": 1.0,
    "like": 2.0,
    "dislike": -2.5,
    "save": 2.5,
    "unsave": -1.0,
    "share": 3.0,
    "hide": -3.0,
    "worth_time": 3.5,
    "not_worth_time": -3.0,
}
EXPLORE_EVERY = 6          # one exploration slot per N items
MMR_LAMBDA = 0.78
RECENCY_HOURS = 30.0
CORPUS_DAYS = 7


def daypart(local_hour: Optional[int]) -> str:
    h = dt.datetime.now().hour if local_hour is None else int(local_hour) % 24
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"


def _parse(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def _decay(weight: float, updated_at: str, now: dt.datetime) -> float:
    days = max(0.0, (now - _parse(updated_at)).total_seconds() / 86400)
    return weight * 0.5 ** (days / HALF_LIFE_DAYS)


# ---------------------------------------------------------------- corpus cache
class Corpus:
    """In-memory article features with TF-IDF computed over the live corpus."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sig = None
        self.articles: Dict[str, Dict[str, Any]] = {}
        self.order: List[str] = []
        self.clusters: List[StoryCluster] = []
        self.cluster_by_aid: Dict[str, StoryCluster] = {}

    def get(self, db_path: str = FOR_YOU_DB) -> "Corpus":
        with connect(db_path) as conn:
            sig = tuple(conn.execute("SELECT COUNT(*), MAX(fetched_at) FROM articles").fetchone())
        if sig == self._sig:
            return self
        with self._lock:
            if sig != self._sig:
                self._load(db_path)
                self._sig = sig
        return self

    def _load(self, db_path: str):
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=CORPUS_DAYS)).isoformat()
        with connect(db_path) as conn:
            rows = conn.execute("SELECT * FROM articles WHERE published_at >= ? ORDER BY published_at DESC LIMIT 3000",
                                (cutoff,)).fetchall()
            if len(rows) < 60:  # sparse / offline: fall back to the most recent articles of any age
                rows = conn.execute("SELECT * FROM articles ORDER BY published_at DESC LIMIT 3000").fetchall()
        tfs = [Counter(json.loads(r["tf_json"] or "{}")) for r in rows]
        df: Counter = Counter()
        for tf in tfs:
            df.update(tf.keys())
        arts, order = {}, []
        for r, tf in zip(rows, tfs):
            entities = json.loads(r["entities_json"] or "[]")
            kw = tfidf_keywords(tf, df, len(rows))
            arts[r["id"]] = {
                "id": r["id"], "url": r["url"], "title": r["title"], "summary": r["summary"] or "",
                "publisher": r["publisher"] or "Unknown", "image_url": r["image_url"],
                "published_at": r["published_at"], "word_count": r["word_count"] or 0,
                "topics": json.loads(r["topics_json"] or "{}"),
                "keywords": kw, "kwset": set(list(kw)[:8]),
                "entities": entities, "is_demo": bool(r["is_demo"]),
            }
            order.append(r["id"])
        self.articles, self.order = arts, order
        self.clusters = ClusterEngine.cluster_articles(list(arts.values()))
        self.cluster_by_aid = {}
        for c in self.clusters:
            for art in c.articles:
                self.cluster_by_aid[art["id"]] = c

    def article(self, aid: str, db_path: str = FOR_YOU_DB) -> Optional[Dict[str, Any]]:
        a = self.get(db_path).articles.get(aid)
        if a:
            return a
        # Older (e.g. saved) article outside the window: featurise on demand.
        with connect(db_path) as conn:
            r = conn.execute("SELECT * FROM articles WHERE id = ?", (aid,)).fetchone()
        if not r:
            return None
        tf = Counter(json.loads(r["tf_json"] or "{}"))
        kw = tfidf_keywords(tf, {}, 1)
        return {"id": r["id"], "url": r["url"], "title": r["title"], "summary": r["summary"] or "",
                "publisher": r["publisher"] or "Unknown", "image_url": r["image_url"],
                "published_at": r["published_at"], "word_count": r["word_count"] or 0,
                "topics": json.loads(r["topics_json"] or "{}"), "keywords": kw, "kwset": set(list(kw)[:8]),
                "entities": json.loads(r["entities_json"] or "[]"), "is_demo": bool(r["is_demo"])}


CORPUS = Corpus()


def article_features(a: Dict[str, Any], part: str) -> List[Tuple[str, str, float]]:
    feats: List[Tuple[str, str, float]] = []
    for t, s in a["topics"].items():
        feats.append(("topic", t, s))
        feats.append(("daypart", f"{part}:{t}", s))
    for k, s in a["keywords"].items():
        feats.append(("keyword", k, s))
    ents = a["entities"][:5]
    for e in ents:
        feats.append(("entity", e, 1 / math.sqrt(len(ents))))
    feats.append(("source", a["publisher"], 1.0))
    return feats


# ---------------------------------------------------------------- learning
class Recommender:
    def __init__(self, db_path: str = FOR_YOU_DB):
        self.db = db_path
        init_schema(db_path)

    # ---- profile storage
    def _apply(self, conn, user_id: int, updates: Iterable[Tuple[str, str, float]]):
        now = dt.datetime.now(dt.timezone.utc)
        ts = now.isoformat(timespec="seconds")
        for kind, key, delta in updates:
            if abs(delta) < 1e-4:
                continue
            row = conn.execute("SELECT weight, updated_at FROM affinities WHERE user_id=? AND kind=? AND key=?",
                               (user_id, kind, key)).fetchone()
            base = _decay(row["weight"], row["updated_at"], now) if row else 0.0
            w = max(WEIGHT_CLAMP[0], min(WEIGHT_CLAMP[1], base + delta))
            conn.execute("""INSERT INTO affinities (user_id, kind, key, weight, updated_at) VALUES (?,?,?,?,?)
                            ON CONFLICT(user_id, kind, key) DO UPDATE SET weight=excluded.weight, updated_at=excluded.updated_at""",
                         (user_id, kind, key, w, ts))

    def _learn_article(self, conn, user_id: int, a: Dict[str, Any], signal: float, part: str):
        self._apply(conn, user_id, ((k, key, KIND_LR[k] * signal * s) for k, key, s in article_features(a, part)))

    def _bandit(self, conn, user_id: int, topic: str, success: float = 0.0, failure: float = 0.0):
        conn.execute("""INSERT INTO topic_bandit (user_id, topic, successes, failures) VALUES (?,?,?,?)
                        ON CONFLICT(user_id, topic) DO UPDATE SET successes=successes+excluded.successes,
                        failures=failures+excluded.failures""", (user_id, topic, success, failure))

    def _ua(self, conn, user_id: int, aid: str, **fields):
        conn.execute("INSERT OR IGNORE INTO user_articles (user_id, article_id) VALUES (?, ?)", (user_id, aid))
        allowed_cols = {"impressions", "clicked", "dwell_seconds", "reaction", "saved", "hidden", "last_seen"}
        set_clauses = []
        params = []
        for col, val in fields.items():
            if col not in allowed_cols:
                continue
            if col == "impressions" and val == "+1":
                set_clauses.append("impressions = COALESCE(impressions, 0) + 1")
            elif col == "dwell_seconds" and isinstance(val, (int, float)):
                set_clauses.append("dwell_seconds = COALESCE(dwell_seconds, 0) + ?")
                params.append(float(val))
            else:
                set_clauses.append(f"{col} = ?")
                params.append(val)
        if set_clauses:
            params.extend([user_id, aid])
            sql = f"UPDATE user_articles SET {', '.join(set_clauses)} WHERE user_id=? AND article_id=?"
            conn.execute(sql, params)

    def onboard(self, user_id: int, topics: List[str], sources: Optional[List[str]] = None):
        topics = [t for t in topics if t in TOPICS]
        with _write_lock, connect(self.db) as conn:
            self._apply(conn, user_id, [("topic", t, 3.0) for t in topics])
            self._apply(conn, user_id, [("source", s, 2.0) for s in (sources or [])])
            for t in topics:
                self._bandit(conn, user_id, t, success=2.0)
            conn.execute("UPDATE users SET onboarded = 1 WHERE id = ?", (user_id,))
            conn.execute("INSERT INTO events (user_id, kind, meta, created_at) VALUES (?,?,?,?)",
                         (user_id, "onboard", json.dumps({"topics": topics}), now_iso()))

    def record(self, user_id: int, ev: Dict[str, Any]) -> None:
        """Record one behavioural event and update the taste profile."""
        kind = ev.get("kind")
        aid = ev.get("article_id")
        part = daypart(ev.get("local_hour"))
        value = float(ev.get("value") or 0)
        a = CORPUS.article(aid, self.db) if aid else None

        with _write_lock, connect(self.db) as conn:
            conn.execute("INSERT INTO events (user_id, article_id, kind, value, meta, created_at) VALUES (?,?,?,?,?,?)",
                         (user_id, aid, kind, value, json.dumps({k: ev[k] for k in ("topic", "query", "publisher", "local_hour") if k in ev}), now_iso()))

            if kind in ("more_topic", "less_topic") and ev.get("topic") in TOPICS:
                sign = 1 if kind == "more_topic" else -1
                self._apply(conn, user_id, [("topic", ev["topic"], 3.0 * sign)])
                self._bandit(conn, user_id, ev["topic"], success=2.0 if sign > 0 else 0, failure=2.0 if sign < 0 else 0)
                return
            if kind in ("mute_source", "unmute_source") and ev.get("publisher"):
                pub = ev["publisher"]
                if kind == "mute_source":
                    conn.execute("INSERT OR IGNORE INTO muted_sources VALUES (?, ?)", (user_id, pub))
                    self._apply(conn, user_id, [("source", pub, -8.0)])
                else:
                    conn.execute("DELETE FROM muted_sources WHERE user_id=? AND publisher=?", (user_id, pub))
                    self._apply(conn, user_id, [("source", pub, 6.0)])
                return
            if kind == "search" and ev.get("query"):
                terms = list(dict.fromkeys(tokenize(ev["query"])))[:6]
                self._apply(conn, user_id, [("keyword", t, 0.6) for t in terms])
                return
            if not a:
                return

            primary = next(iter(a["topics"]), None)
            now_str = now_iso()
            if kind == "impression":
                row = conn.execute("SELECT impressions, clicked FROM user_articles WHERE user_id=? AND article_id=?",
                                   (user_id, aid)).fetchone()
                self._ua(conn, user_id, aid, impressions="+1", last_seen=now_str)
                # Skips only count as weak negatives, and only the first couple of times.
                if not row or (row["impressions"] < 2 and not row["clicked"]):
                    self._learn_article(conn, user_id, a, SIGNALS["impression"], part)
                    if primary:
                        self._bandit(conn, user_id, primary, failure=0.15)
            elif kind == "click":
                row = conn.execute("SELECT clicked FROM user_articles WHERE user_id=? AND article_id=?",
                                   (user_id, aid)).fetchone()
                self._ua(conn, user_id, aid, clicked=1, last_seen=now_str)
                if not row or not row["clicked"]:
                    self._learn_article(conn, user_id, a, SIGNALS["click"], part)
                    if primary:
                        self._bandit(conn, user_id, primary, success=1.0)
            elif kind == "dwell":
                secs = max(0.0, min(value, 900.0))
                self._ua(conn, user_id, aid, dwell_seconds=secs, last_seen=now_str)
                if secs < 8:  # bounced straight back: the headline over-promised
                    # Net must be negative: click added +1.0, so -1.5 results in a net -0.5 penalty
                    self._learn_article(conn, user_id, a, -1.5, part)
                    if primary:
                        self._bandit(conn, user_id, primary, failure=1.2)
                else:
                    ratio = secs / estimate_read_seconds(a["word_count"])
                    self._learn_article(conn, user_id, a, 0.8 * min(ratio, 2.0), part)
            elif kind in ("like", "dislike"):
                self._ua(conn, user_id, aid, reaction=1 if kind == "like" else -1, last_seen=now_str)
                self._learn_article(conn, user_id, a, SIGNALS[kind], part)
                if primary:
                    self._bandit(conn, user_id, primary, success=2.0 if kind == "like" else 0, failure=2.0 if kind == "dislike" else 0)
            elif kind in ("save", "unsave"):
                self._ua(conn, user_id, aid, saved=1 if kind == "save" else 0, last_seen=now_str)
                self._learn_article(conn, user_id, a, SIGNALS[kind], part)
            elif kind == "share":
                self._learn_article(conn, user_id, a, SIGNALS["share"], part)
            elif kind in ("worth_time", "not_worth_time"):
                sat_val = 1 if kind == "worth_time" else -1
                self._ua(conn, user_id, aid, reaction=sat_val, last_seen=now_str)
                self._learn_article(conn, user_id, a, SIGNALS[kind], part)
                if primary:
                    self._bandit(conn, user_id, primary, success=3.0 if sat_val == 1 else 0, failure=3.0 if sat_val == -1 else 0)
            elif kind == "hide":
                self._ua(conn, user_id, aid, hidden=1, last_seen=now_str)
                self._learn_article(conn, user_id, a, SIGNALS["hide"], part)
                if primary:
                    self._bandit(conn, user_id, primary, failure=1.5)

    # ---- profile reading
    def affinities(self, user_id: int) -> Dict[str, Dict[str, float]]:
        now = dt.datetime.now(dt.timezone.utc)
        out: Dict[str, Dict[str, float]] = defaultdict(dict)
        with connect(self.db) as conn:
            for r in conn.execute("SELECT kind, key, weight, updated_at FROM affinities WHERE user_id=?", (user_id,)):
                w = _decay(r["weight"], r["updated_at"], now)
                if abs(w) > 0.01:
                    out[r["kind"]][r["key"]] = w
        return out

    def _user_state(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        with connect(self.db) as conn:
            return {r["article_id"]: dict(r) for r in
                    conn.execute("SELECT * FROM user_articles WHERE user_id=?", (user_id,))}

    def _muted(self, user_id: int) -> set:
        with connect(self.db) as conn:
            return {r[0] for r in conn.execute("SELECT publisher FROM muted_sources WHERE user_id=?", (user_id,))}

    def _positive_count(self, user_id: int) -> int:
        with connect(self.db) as conn:
            return conn.execute("""SELECT COUNT(*) FROM user_articles WHERE user_id=? AND
                (clicked=1 OR reaction=1 OR saved=1)""", (user_id,)).fetchone()[0] + \
                   conn.execute("SELECT COUNT(*) FROM events WHERE user_id=? AND kind IN ('onboard','more_topic')",
                                (user_id,)).fetchone()[0] * 3

    # ---- collaborative filtering (user-user cosine over positive engagement)
    def _collaborative(self, user_id: int) -> Dict[str, float]:
        with connect(self.db) as conn:
            rows = conn.execute("""SELECT user_id, article_id FROM user_articles
                                   WHERE (clicked=1 AND reaction>=0) OR reaction=1 OR saved=1""").fetchall()
        by_user: Dict[int, set] = defaultdict(set)
        for r in rows:
            by_user[r["user_id"]].add(r["article_id"])
        mine = by_user.get(user_id, set())
        if not mine:
            return {}
        scores: Dict[str, float] = defaultdict(float)
        for other, theirs in by_user.items():
            if other == user_id:
                continue
            overlap = len(mine & theirs)
            if not overlap:
                continue
            sim = overlap / math.sqrt(len(mine) * len(theirs))
            for aid in theirs - mine:
                scores[aid] += sim
        top = max(scores.values(), default=0)
        return {k: v / top for k, v in scores.items()} if top else {}

    def _popularity(self) -> Dict[str, float]:
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=72)).isoformat()
        with connect(self.db) as conn:
            rows = conn.execute("""SELECT article_id, SUM(CASE kind WHEN 'click' THEN 1 WHEN 'like' THEN 2
                                   WHEN 'save' THEN 2 WHEN 'share' THEN 3 WHEN 'dislike' THEN -1 WHEN 'hide' THEN -1 ELSE 0 END) s
                                   FROM events WHERE created_at >= ? AND article_id IS NOT NULL GROUP BY article_id""",
                                (since,)).fetchall()
        top = max((r["s"] for r in rows), default=0)
        return {r["article_id"]: math.log1p(max(r["s"], 0)) / math.log1p(top) for r in rows} if top > 0 else {}

    @staticmethod
    def _recency(a: Dict[str, Any], now: dt.datetime) -> float:
        age_h = max(0.0, (now - _parse(a["published_at"])).total_seconds() / 3600)
        return math.exp(-age_h / RECENCY_HOURS)

    # ---- scoring
    def _content(self, a: Dict[str, Any], aff: Dict[str, Dict[str, float]], part: str) -> Tuple[float, Dict[str, Tuple[float, str]]]:
        """Returns content score and the best-contributing feature per kind (for explanations)."""
        per_kind: Dict[str, float] = defaultdict(float)
        best: Dict[str, Tuple[float, str]] = {}
        # Topic & daypart matches are averaged over the article's topic strengths, so a story
        # tagged with several topics isn't rewarded just for being multi-tagged.
        topic_norm = sum(a["topics"].values()) or 1.0
        for kind, key, strength in article_features(a, part):
            if kind in ("topic", "daypart"):
                strength /= topic_norm
            w = aff.get(kind, {}).get(key)
            if w is None:
                continue
            c = strength * math.tanh(w / SQUASH[kind])
            per_kind[kind] += c
            if c > best.get(kind, (0, ""))[0]:
                best[kind] = (c, key)
        total = sum(CONTENT_MIX[k] * max(-1.5, min(1.5, v)) for k, v in per_kind.items())
        return total, best

    def _explain(self, a, best, cf: float, explore_topic: Optional[str], part: str) -> Dict[str, str]:
        if explore_topic:
            return {"type": "explore", "text": f"Exploring {explore_topic} — tap ♥ or ✕ to teach your feed"}
        candidates = []
        if "keyword" in best:
            candidates.append((best["keyword"][0] * CONTENT_MIX["keyword"] * 1.2, "keyword",
                               f"Because you read about “{display_term(best['keyword'][1])}”"))
        if "entity" in best:
            candidates.append((best["entity"][0] * CONTENT_MIX["entity"] * 1.6, "entity", f"More on {best['entity'][1]}"))
        if "topic" in best:
            candidates.append((best["topic"][0] * CONTENT_MIX["topic"], "topic", f"You follow {best['topic'][1]}"))
        if "source" in best:
            candidates.append((best["source"][0] * CONTENT_MIX["source"] * 1.3, "source", f"You often read {best['source'][1]}"))
        if "daypart" in best:
            candidates.append((best["daypart"][0] * CONTENT_MIX["daypart"] * 1.5, "daypart",
                               f"You usually read {best['daypart'][1].split(':', 1)[1]} in the {part}"))
        if cf > 0.2:
            candidates.append((cf * 0.3, "collab", "Readers with similar taste read this"))
        if not candidates or max(candidates)[0] < 0.02:
            return {"type": "fresh", "text": "Fresh and widely read right now"}
        _, typ, text = max(candidates)
        return {"type": typ, "text": text}

    def _similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        kw = jaccard(a["kwset"], b["kwset"])
        topic = 1.0 if next(iter(a["topics"]), None) == next(iter(b["topics"]), None) else 0.0
        src = 1.0 if a["publisher"] == b["publisher"] else 0.0
        return 0.6 * kw + 0.25 * topic + 0.15 * src

    def rank(self, user_id: int, limit: int = 30, exclude: Iterable[str] = (), local_hour: Optional[int] = None,
             topic: Optional[str] = None, rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
        rng = rng or random.Random()
        corpus = CORPUS.get(self.db)
        now = dt.datetime.now(dt.timezone.utc)
        part = daypart(local_hour)
        aff = self.affinities(user_id)
        state = self._user_state(user_id)
        muted = self._muted(user_id)
        cf = self._collaborative(user_id)
        pop = self._popularity()
        exclude = set(exclude)
        confidence = 1 - math.exp(-self._positive_count(user_id) / 12)

        scored = []
        for aid in corpus.order:
            a = corpus.articles[aid]
            st = state.get(aid, {})
            if aid in exclude or st.get("hidden") or st.get("clicked") or a["publisher"] in muted:
                continue
            if topic and topic not in a["topics"]:
                continue
            content, best = self._content(a, aff, part)
            rec = self._recency(a, now)
            p = pop.get(aid, 0.0)
            fatigue = 0.12 * min(st.get("impressions", 0), 5)
            c = corpus.cluster_by_aid.get(aid)
            corroboration = (c.corroboration_score - 0.5) * 0.4 if c else 0.0
            personal = 1.6 * content + 0.35 * cf.get(aid, 0) + 0.35 * rec + 0.12 * p + corroboration - fatigue
            baseline = 0.6 * rec + 0.4 * p + corroboration - fatigue
            score = confidence * personal + (1 - confidence) * baseline + 0.4 * content * (1 - confidence)
            scored.append((score, aid, best))
        scored.sort(key=lambda x: -x[0])

        # ---- MMR diversity re-rank over the head of the list (+ near-duplicate collapse)
        pool = scored[: max(limit * 4, 80)]
        chosen: List[Tuple[float, str, dict]] = []
        chosen_clusters: Set[str] = set()
        while pool and len(chosen) < limit:
            best_i, best_val = 0, -1e9
            for i, (s, aid, _) in enumerate(pool):
                a = corpus.articles[aid]
                sim = max((self._similarity(a, corpus.articles[c[1]]) for c in chosen[-6:]), default=0.0)
                val = MMR_LAMBDA * s - (1 - MMR_LAMBDA) * sim
                if val > best_val:
                    best_i, best_val = i, val
            pick = pool.pop(best_i)
            # Story cluster deduplication: avoid duplicate coverage of the same event
            clust = corpus.cluster_by_aid.get(pick[1])
            if clust and clust.id in chosen_clusters:
                continue
            if any(jaccard(corpus.articles[pick[1]]["kwset"], corpus.articles[c[1]]["kwset"]) > 0.55 for c in chosen):
                continue  # same story from another outlet
            chosen.append(pick)
            if clust:
                chosen_clusters.add(clust.id)

        # ---- Thompson-sampling exploration slots (personal feed only)
        explore_ids: Dict[str, str] = {}
        if not topic and confidence > 0.05:
            top_topics = {t for t, _ in sorted(aff.get("topic", {}).items(), key=lambda kv: -kv[1])[:3]}
            with connect(self.db) as conn:
                arms = {r["topic"]: (r["successes"], r["failures"]) for r in
                        conn.execute("SELECT * FROM topic_bandit WHERE user_id=?", (user_id,))}
            used = {c[1] for c in chosen} | exclude
            for slot in range(EXPLORE_EVERY - 2, len(chosen), EXPLORE_EVERY):
                samples = {t: rng.betavariate(arms.get(t, (0, 0))[0] + 1, arms.get(t, (0, 0))[1] + 1)
                           for t in TOPICS if t not in top_topics and aff.get("topic", {}).get(t, 0) > -4}
                if not samples:
                    break
                t = max(samples, key=samples.get)
                # Pick the highest-scoring candidate for this topic from scored, rather than raw newest
                cand_match = next((item for item in scored if item[1] not in used
                                   and t in corpus.articles[item[1]]["topics"]
                                   and not state.get(item[1], {}).get("hidden")
                                   and not state.get(item[1], {}).get("clicked")
                                   and corpus.articles[item[1]]["publisher"] not in muted
                                   and (not corpus.cluster_by_aid.get(item[1]) or corpus.cluster_by_aid[item[1]].id not in chosen_clusters)), None)
                if cand_match:
                    s_score, cand, best_why = cand_match
                    chosen.insert(slot, (s_score, cand, best_why))
                    explore_ids[cand] = t
                    used.add(cand)
                    c_cand = corpus.cluster_by_aid.get(cand)
                    if c_cand:
                        chosen_clusters.add(c_cand.id)
            chosen = chosen[:limit]

        out = []
        for s, aid, best in chosen:
            a = corpus.articles[aid]
            clust = corpus.cluster_by_aid.get(aid)
            out.append(self._card(a, state.get(aid, {}), score=round(s, 4),
                                  why=self._explain(a, best, cf.get(aid, 0), explore_ids.get(aid), part),
                                  cluster=clust))
        return out

    def trending(self, user_id: Optional[int], limit: int = 30, exclude: Iterable[str] = ()) -> List[Dict[str, Any]]:
        corpus = CORPUS.get(self.db)
        now = dt.datetime.now(dt.timezone.utc)
        pop = self._popularity()
        state = self._user_state(user_id) if user_id else {}
        exclude = set(exclude)
        scored = sorted(((0.55 * self._recency(a, now) + 0.45 * pop.get(aid, 0), aid)
                         for aid, a in corpus.articles.items() if aid not in exclude and not state.get(aid, {}).get("hidden")),
                        reverse=True)
        out, per_source = [], Counter()
        for s, aid in scored:
            a = corpus.articles[aid]
            if per_source[a["publisher"]] >= 3:
                continue
            per_source[a["publisher"]] += 1
            clust = corpus.cluster_by_aid.get(aid)
            out.append(self._card(a, state.get(aid, {}), score=round(s, 4),
                                  why={"type": "trending", "text": "Trending across Pith"},
                                  cluster=clust))
            if len(out) >= limit:
                break
        return out

    def search(self, user_id: int, query: str, limit: int = 30) -> List[Dict[str, Any]]:
        corpus = CORPUS.get(self.db)
        terms = set(tokenize(query))
        if not terms:
            return []
        state = self._user_state(user_id)
        now = dt.datetime.now(dt.timezone.utc)
        hits = []
        for aid, a in corpus.articles.items():
            title_terms = set(tokenize(a["title"]))
            s = sum(a["keywords"].get(t, 0) for t in terms) + 0.5 * len(terms & title_terms)
            if s > 0:
                hits.append((s + 0.2 * self._recency(a, now), aid))
        hits.sort(reverse=True)
        return [self._card(corpus.articles[aid], state.get(aid, {}), score=round(s, 4),
                           why={"type": "search", "text": f"Matches “{query.strip()[:40]}”"},
                           cluster=corpus.cluster_by_aid.get(aid)) for s, aid in hits[:limit]]

    def library(self, user_id: int, which: str, limit: int = 60) -> List[Dict[str, Any]]:
        corpus = CORPUS.get(self.db)
        sql = ("SELECT * FROM user_articles WHERE user_id=? AND saved = 1 ORDER BY last_seen DESC LIMIT ?"
               if which == "saved" else
               "SELECT * FROM user_articles WHERE user_id=? AND clicked = 1 ORDER BY last_seen DESC LIMIT ?")
        with connect(self.db) as conn:
            rows = conn.execute(sql, (user_id, limit)).fetchall()
        out = []
        for r in rows:
            a = corpus.article(r["article_id"], self.db)
            if a:
                label = "Saved" if which == "saved" else f"Read · {int(r['dwell_seconds'] // 60)}m {int(r['dwell_seconds'] % 60)}s"
                clust = corpus.cluster_by_aid.get(a["id"])
                out.append(self._card(a, dict(r), score=0, why={"type": which, "text": label}, cluster=clust))
        return out

    @staticmethod
    def _card(a: Dict[str, Any], st: Dict[str, Any], score: float, why: Dict[str, str], cluster: Optional[StoryCluster] = None) -> Dict[str, Any]:
        source_count = cluster.publisher_count if cluster else 1
        sources = cluster.publishers if cluster else [a["publisher"]]
        cluster_id = cluster.id if cluster else None
        corroboration_score = cluster.corroboration_score if cluster else 0.5
        return {
            "id": a["id"], "url": a["url"], "title": a["title"], "summary": a["summary"],
            "publisher": a["publisher"], "image_url": a["image_url"], "published_at": a["published_at"],
            "topics": list(a["topics"].keys()), "entities": a["entities"][:4],
            "read_minutes": max(1, round(estimate_read_seconds(a["word_count"]) / 60)),
            "is_demo": a["is_demo"], "score": score, "why": why,
            "source_count": source_count,
            "sources": sources,
            "cluster_id": cluster_id,
            "corroboration_score": corroboration_score,
            "state": {"saved": bool(st.get("saved")), "reaction": st.get("reaction", 0) or 0,
                      "clicked": bool(st.get("clicked"))},
        }

    # ---- transparency
    def profile(self, user_id: int) -> Dict[str, Any]:
        aff = self.affinities(user_id)

        def top(kind, n, fmt=lambda k: k):
            items = sorted(aff.get(kind, {}).items(), key=lambda kv: -kv[1])
            return [{"key": k, "label": fmt(k), "weight": round(w, 3)} for k, w in items[:n] if w > 0.05]

        dayparts: Dict[str, Dict[str, float]] = defaultdict(dict)
        for k, w in aff.get("daypart", {}).items():
            p, t = k.split(":", 1)
            if w > 0.05:
                dayparts[p][t] = round(w, 3)
        with connect(self.db) as conn:
            stats = conn.execute("""SELECT COALESCE(SUM(clicked),0) reads, COALESCE(SUM(dwell_seconds),0) dwell,
                                    COALESCE(SUM(saved),0) saved, COALESCE(SUM(impressions),0) seen
                                    FROM user_articles WHERE user_id=?""", (user_id,)).fetchone()
            n_events = conn.execute("SELECT COUNT(*) FROM events WHERE user_id=?", (user_id,)).fetchone()[0]
            muted = [r[0] for r in conn.execute("SELECT publisher FROM muted_sources WHERE user_id=?", (user_id,))]
        avoided = sorted(((k, w) for k, w in aff.get("topic", {}).items() if w < -0.5), key=lambda kv: kv[1])
        from core.your5 import infer_role
        inferred_r, role_conf, role_reason = infer_role(aff)
        return {
            "inferred_role": inferred_r,
            "role_confidence": role_conf,
            "role_reason": role_reason,
            "topics": top("topic", len(TOPICS)),
            "avoided_topics": [{"key": k, "weight": round(w, 3)} for k, w in avoided],
            "keywords": top("keyword", 14, display_term),
            "entities": top("entity", 10),
            "sources": top("source", 8),
            "dayparts": {p: dict(sorted(v.items(), key=lambda kv: -kv[1])[:3]) for p, v in dayparts.items()},
            "muted_sources": muted,
            "stats": {"reads": stats["reads"], "minutes_read": round(stats["dwell"] / 60, 1),
                      "saved": stats["saved"], "seen": stats["seen"], "events": n_events,
                      "confidence": round(1 - math.exp(-self._positive_count(user_id) / 12), 3)},
            "all_topics": TOPICS,
        }

    def reset(self, user_id: int) -> None:
        with _write_lock, connect(self.db) as conn:
            for table in ("affinities", "user_articles", "topic_bandit", "muted_sources", "events"):
                conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
            conn.execute("UPDATE users SET onboarded = 0 WHERE id=?", (user_id,))
