"""
General news ingestion for the personalised For You feed.

Pulls public RSS / Atom feeds across many sections, normalises them into
`articles`, and attaches deterministic text features (core.textfeatures).
Stdlib only: urllib + xml.etree + sqlite3.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import json
import sqlite3
import threading
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from core.textfeatures import featurize, strip_html

FOR_YOU_DB = "foryou.sqlite3"

# (feed id, publisher, section/topic prior, url, optional home region)
# Regions let a reader ask for more of their part of the world (core/prefs.py REGIONS).
FEED_REGISTRY: List[Dict[str, str]] = [
    {"id": "bbc-world", "publisher": "BBC News", "topic": "World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "region": "uk"},
    {"id": "aljazeera", "publisher": "Al Jazeera", "topic": "World", "url": "https://www.aljazeera.com/xml/rss/all.xml", "region": "middle-east"},
    {"id": "npr-news", "publisher": "NPR", "topic": "World", "url": "https://feeds.npr.org/1001/rss.xml", "region": "americas"},
    {"id": "npr-politics", "publisher": "NPR", "topic": "Politics", "url": "https://feeds.npr.org/1014/rss.xml", "region": "americas"},
    {"id": "bbc-business", "publisher": "BBC News", "topic": "Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "region": "uk"},
    {"id": "cnbc-markets", "publisher": "CNBC", "topic": "Markets", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "region": "americas"},
    {"id": "verge", "publisher": "The Verge", "topic": "Technology", "url": "https://www.theverge.com/rss/index.xml"},
    {"id": "ars", "publisher": "Ars Technica", "topic": "Technology", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"id": "techcrunch", "publisher": "TechCrunch", "topic": "Technology", "url": "https://techcrunch.com/feed/"},
    {"id": "hn", "publisher": "Hacker News", "topic": "Technology", "url": "https://hnrss.org/frontpage"},
    {"id": "mit-tr", "publisher": "MIT Technology Review", "topic": "AI", "url": "https://www.technologyreview.com/feed/"},
    {"id": "bbc-science", "publisher": "BBC News", "topic": "Science", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "region": "uk"},
    {"id": "sciencedaily", "publisher": "ScienceDaily", "topic": "Science", "url": "https://www.sciencedaily.com/rss/top.xml"},
    {"id": "nasa", "publisher": "NASA", "topic": "Space", "url": "https://www.nasa.gov/news-release/feed/"},
    {"id": "bbc-health", "publisher": "BBC News", "topic": "Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml", "region": "uk"},
    {"id": "bbc-sport", "publisher": "BBC Sport", "topic": "Sports", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "region": "uk"},
    {"id": "espn", "publisher": "ESPN", "topic": "Sports", "url": "https://www.espn.com/espn/rss/news", "region": "americas"},
    {"id": "bbc-ent", "publisher": "BBC News", "topic": "Entertainment", "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "region": "uk"},
    {"id": "polygon", "publisher": "Polygon", "topic": "Gaming", "url": "https://www.polygon.com/rss/index.xml"},
    {"id": "guardian-env", "publisher": "The Guardian", "topic": "Climate", "url": "https://www.theguardian.com/environment/rss"},
    {"id": "toi", "publisher": "Times of India", "topic": "World", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "region": "india"},
    {"id": "hindu", "publisher": "The Hindu", "topic": "Politics", "url": "https://www.thehindu.com/news/national/feeder/default.rss", "region": "india"},
    # Regional desks
    {"id": "dw", "publisher": "DW", "topic": "World", "url": "https://rss.dw.com/xml/rss-en-all", "region": "europe"},
    {"id": "france24", "publisher": "France 24", "topic": "World", "url": "https://www.france24.com/en/rss", "region": "europe"},
    {"id": "politico-eu", "publisher": "Politico Europe", "topic": "Politics", "url": "https://www.politico.eu/feed/", "region": "europe"},
    {"id": "skynews", "publisher": "Sky News", "topic": "World", "url": "https://feeds.skynews.com/feeds/rss/home.xml", "region": "uk"},
    {"id": "guardian-uk", "publisher": "The Guardian", "topic": "World", "url": "https://www.theguardian.com/uk-news/rss", "region": "uk"},
    {"id": "guardian-americas", "publisher": "The Guardian", "topic": "World", "url": "https://www.theguardian.com/world/americas/rss", "region": "americas"},
    {"id": "mercopress", "publisher": "MercoPress", "topic": "World", "url": "https://en.mercopress.com/rss", "region": "americas"},
    {"id": "indianexpress", "publisher": "The Indian Express", "topic": "World", "url": "https://indianexpress.com/feed/", "region": "india"},
    {"id": "livemint", "publisher": "Mint", "topic": "Business", "url": "https://www.livemint.com/rss/news", "region": "india"},
    {"id": "japantimes", "publisher": "The Japan Times", "topic": "World", "url": "https://www.japantimes.co.jp/feed/", "region": "asia"},
    {"id": "africanews", "publisher": "Africanews", "topic": "World", "url": "https://www.africanews.com/feed/rss", "region": "africa"},
    {"id": "middleeasteye", "publisher": "Middle East Eye", "topic": "World", "url": "https://www.middleeasteye.net/rss", "region": "middle-east"},
    # Specialist desks
    {"id": "restofworld", "publisher": "Rest of World", "topic": "Technology", "url": "https://restofworld.org/feed/latest/"},
    {"id": "wired", "publisher": "Wired", "topic": "Technology", "url": "https://www.wired.com/feed/rss"},
    {"id": "ieee-spectrum", "publisher": "IEEE Spectrum", "topic": "Technology", "url": "https://spectrum.ieee.org/feeds/feed.rss"},
    {"id": "quanta", "publisher": "Quanta Magazine", "topic": "Science", "url": "https://www.quantamagazine.org/feed/"},
    {"id": "carbonbrief", "publisher": "Carbon Brief", "topic": "Climate", "url": "https://www.carbonbrief.org/feed"},
    {"id": "statnews", "publisher": "STAT", "topic": "Health", "url": "https://www.statnews.com/feed/"},
]
FEED_REGIONS: Dict[str, str] = {f["id"]: f["region"] for f in FEED_REGISTRY if f.get("region")}

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

_write_lock = threading.Lock()


@contextmanager
def connect(db_path: str = FOR_YOU_DB) -> Iterator[sqlite3.Connection]:
    """Short-lived connection: commits on success, rolls back on error, always closes."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(db_path: str = FOR_YOU_DB) -> None:
    with connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            publisher TEXT,
            feed_id TEXT,
            feed_topic TEXT,
            image_url TEXT,
            published_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            tf_json TEXT,
            topics_json TEXT,
            entities_json TEXT,
            is_demo INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            onboarded INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        -- Raw behavioural log: every signal the reader gives us.
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            article_id TEXT,
            kind TEXT NOT NULL,
            value REAL DEFAULT 0,
            meta TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_events_article ON events(article_id, kind);

        -- Learned taste profile: decayed weight per feature (topic / keyword / entity / source / daypart-topic).
        CREATE TABLE IF NOT EXISTS affinities (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            key TEXT NOT NULL,
            weight REAL NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, kind, key)
        );

        -- Per-user per-article state (seen / clicked / saved / hidden).
        CREATE TABLE IF NOT EXISTS user_articles (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            article_id TEXT NOT NULL,
            impressions INTEGER DEFAULT 0,
            clicked INTEGER DEFAULT 0,
            dwell_seconds REAL DEFAULT 0,
            reaction INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (user_id, article_id)
        );

        -- Topic bandit arms for exploration (Beta(successes+1, failures+1)).
        CREATE TABLE IF NOT EXISTS topic_bandit (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic TEXT NOT NULL,
            successes REAL DEFAULT 0,
            failures REAL DEFAULT 0,
            PRIMARY KEY (user_id, topic)
        );

        -- Muted publishers.
        CREATE TABLE IF NOT EXISTS muted_sources (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            publisher TEXT NOT NULL,
            PRIMARY KEY (user_id, publisher)
        );

        -- Reader calls on Pith's forecasts ("Beat the Brief"). One current call per reader per card.
        CREATE TABLE IF NOT EXISTS forecast_votes (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            card_id TEXT NOT NULL,
            vote TEXT NOT NULL CHECK (vote IN ('higher', 'agree', 'lower')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, card_id)
        );
        CREATE INDEX IF NOT EXISTS idx_forecast_votes_card ON forecast_votes(card_id);

        -- Things a reader follows: an entity, a phrase, or one developing story (core/follows.py).
        CREATE TABLE IF NOT EXISTS follows (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind TEXT NOT NULL CHECK (kind IN ('entity', 'keyword', 'story')),
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            seed_json TEXT,
            created_at TEXT NOT NULL,
            last_checked TEXT NOT NULL,
            PRIMARY KEY (user_id, kind, key)
        );

        -- Reader preferences: depth, delivery hour, region (core/prefs.py). Values are JSON.
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, key)
        );

        -- Reader-added RSS/Atom feeds (core/userfeeds.py). Their articles carry feed_id 'u-…'
        -- and are only ranked for readers subscribed to that feed.
        CREATE TABLE IF NOT EXISTS custom_feeds (
            feed_id TEXT PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_fetched TEXT,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS user_feeds (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            feed_id TEXT NOT NULL REFERENCES custom_feeds(feed_id) ON DELETE CASCADE,
            added_at TEXT NOT NULL,
            PRIMARY KEY (user_id, feed_id)
        );

        -- First time a reader was ranked under each experiment variant (core/experiments.py).
        CREATE TABLE IF NOT EXISTS experiment_exposures (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            experiment TEXT NOT NULL,
            variant TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            PRIMARY KEY (user_id, experiment)
        );

        -- Sign-in providers connected to an account (core/oauth.py). No tokens, no email.
        CREATE TABLE IF NOT EXISTS user_identities (
            provider TEXT NOT NULL,
            subject TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            handle TEXT,
            display_name TEXT,
            avatar_url TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT NOT NULL,
            PRIMARY KEY (provider, subject)
        );
        CREATE INDEX IF NOT EXISTS idx_identities_user ON user_identities(user_id);

        -- In-flight OAuth sign-ins: hashed state, PKCE verifier, where to go after. Ten-minute life.
        CREATE TABLE IF NOT EXISTS oauth_states (
            state_hash TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            verifier TEXT,
            next_path TEXT,
            link_user_id INTEGER,
            created_at TEXT NOT NULL
        );

        -- Interests derived from a connected account (core/social_signals.py): the affinity
        -- deltas that were applied, and a plain-language summary shown back to the reader.
        CREATE TABLE IF NOT EXISTS social_signals (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            applied_json TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, provider)
        );
        """)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _parse_date(text: Optional[str]) -> str:
    if not text:
        return now_iso()
    text = text.strip()
    try:
        d = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return now_iso()
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    d = d.astimezone(dt.timezone.utc)
    # Clamp future-dated items so they don't pin the top of the feed.
    return min(d, dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds")


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _find_image(item: ET.Element, summary_html: str) -> Optional[str]:
    for tag in ("media:thumbnail", "media:content"):
        for el in item.findall(tag, _NS):
            url = el.get("url")
            if url and (el.get("medium") in (None, "image") or url.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp"))):
                return url
    enc = item.find("enclosure")
    if enc is not None and (enc.get("type") or "").startswith("image"):
        return enc.get("url")
    import re
    m = re.search(r'<img[^>]+src="([^"]+)"', summary_html or "")
    return m.group(1) if m else None


def parse_feed(xml_bytes: bytes, feed: Dict[str, str]) -> List[Dict[str, Any]]:
    # Entity declarations are how XML bombs and external-entity tricks start; no real feed needs them.
    if b"<!ENTITY" in xml_bytes or b"<!entity" in xml_bytes.lower():
        raise ET.ParseError("XML entity declarations aren't allowed in feeds")
    root = ET.fromstring(xml_bytes)
    items: List[Dict[str, Any]] = []
    rss_items = root.findall(".//item")
    if rss_items:
        for it in rss_items:
            link = _text(it.find("link")) or _text(it.find("guid"))
            raw_summary = _text(it.find("description")) or _text(it.find("content:encoded", _NS))
            items.append({
                "title": strip_html(_text(it.find("title"))),
                "url": link,
                "summary_html": raw_summary,
                "published": _text(it.find("pubDate")) or _text(it.find("dc:date", _NS)),
                "image": _find_image(it, raw_summary),
            })
    else:
        for it in root.findall("atom:entry", _NS):
            # Note: Element truthiness depends on child count, so compare against None explicitly.
            link_el = it.find("atom:link[@rel='alternate']", _NS)
            if link_el is None:
                link_el = it.find("atom:link", _NS)
            raw_summary = _text(it.find("atom:summary", _NS)) or _text(it.find("atom:content", _NS))
            items.append({
                "title": strip_html(_text(it.find("atom:title", _NS))),
                "url": link_el.get("href") if link_el is not None else "",
                "summary_html": raw_summary,
                "published": _text(it.find("atom:published", _NS)) or _text(it.find("atom:updated", _NS)),
                "image": _find_image(it, raw_summary),
            })
    out = []
    for i in items:
        if not i["title"] or not i["url"].lower().startswith(("http://", "https://")):
            continue
        full_text = strip_html(i["summary_html"])
        summary = full_text
        if len(summary) > 420:
            summary = summary[:417].rsplit(" ", 1)[0] + "…"
        out.append({
            "title": i["title"][:300],
            "url": i["url"],
            "summary": summary,
            "full_text": full_text,
            "publisher": feed["publisher"],
            "feed_id": feed["id"],
            "feed_topic": feed["topic"],
            "image_url": i["image"],
            "published_at": _parse_date(i["published"]),
        })
    return out


def fetch_feed(feed: Dict[str, str], timeout: float = 8.0) -> List[Dict[str, Any]]:
    req = urllib.request.Request(feed["url"], headers={
        "User-Agent": "Mozilla/5.0 (compatible; PithReader/1.0; RSS aggregator)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_feed(resp.read(), feed)


def store_articles(raw: List[Dict[str, Any]], db_path: str = FOR_YOU_DB, is_demo: bool = False) -> int:
    inserted = 0
    with _write_lock, connect(db_path) as conn:
        for a in raw:
            aid = hashlib.sha1(a["url"].encode()).hexdigest()[:16]
            full_text = a.get("full_text") or (a["title"] + " " + a.get("summary", ""))
            tf, topics, entities = featurize(a["title"], full_text, a.get("feed_topic"))
            cur = conn.execute("""
                INSERT OR IGNORE INTO articles (id, url, title, summary, publisher, feed_id, feed_topic, image_url,
                    published_at, fetched_at, word_count, tf_json, topics_json, entities_json, is_demo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (aid, a["url"], a["title"], a.get("summary", ""), a.get("publisher"), a.get("feed_id"),
                  a.get("feed_topic"), a.get("image_url"), a["published_at"], now_iso(),
                  len(full_text.split()), json.dumps(dict(tf)),
                  json.dumps(topics), json.dumps(entities), 1 if is_demo else 0))
            inserted += cur.rowcount
    return inserted


def refresh_all(db_path: str = FOR_YOU_DB, feeds: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Fetch every feed concurrently. Returns per-feed status; never raises."""
    init_schema(db_path)
    feeds = feeds or FEED_REGISTRY
    report: Dict[str, Any] = {"ok": 0, "failed": 0, "inserted": 0, "feeds": {}}

    def _one(feed):
        try:
            return feed["id"], fetch_feed(feed), None
        except Exception as e:  # network, parse, HTTP errors
            return feed["id"], [], f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=8) as pool:
        for fid, items, err in pool.map(_one, feeds):
            if err:
                report["failed"] += 1
                report["feeds"][fid] = err
                continue
            n = store_articles(items, db_path)
            report["ok"] += 1
            report["inserted"] += n
            report["feeds"][fid] = f"{len(items)} items, {n} new"

    # Once live news is flowing, retire the offline demo set.
    if report["inserted"] > 0:
        with _write_lock, connect(db_path) as conn:
            conn.execute("DELETE FROM articles WHERE is_demo = 1")
    return report


def article_count(db_path: str = FOR_YOU_DB) -> int:
    init_schema(db_path)
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]


EVENT_RETENTION_DAYS = 180  # raw behaviour log; learned affinities already summarise older history


def prune_old(db_path: str = FOR_YOU_DB, keep_days: int = 21,
              event_days: int = EVENT_RETENTION_DAYS) -> Dict[str, int]:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = (now - dt.timedelta(days=keep_days)).isoformat(timespec="seconds")
    event_cutoff = (now - dt.timedelta(days=event_days)).isoformat(timespec="seconds")
    with _write_lock, connect(db_path) as conn:
        arts = conn.execute("""
            DELETE FROM articles WHERE published_at < ? AND id NOT IN (
                SELECT article_id FROM user_articles WHERE saved = 1)
        """, (cutoff,)).rowcount
        events = conn.execute("DELETE FROM events WHERE created_at < ?", (event_cutoff,)).rowcount
        sessions = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),)).rowcount
    return {"articles": arts, "events": events, "sessions": sessions}
