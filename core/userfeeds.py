"""
Reader-added RSS/Atom feeds.

A reader can add up to MAX_FEEDS_PER_USER feeds. Their articles are stored like any other
(feed_id 'u-<hash>') but are only ranked for readers subscribed to that feed, never in
Trending or anyone else's feed.

Fetching a URL a user typed is a server-side request forgery risk, so every fetch:
  * allows only http/https on default or common ports,
  * resolves the host and refuses private, loopback, link-local, multicast and reserved
    addresses, then connects to exactly the address it checked (so a DNS answer that changes
    between the check and the connect can't point the fetch at an internal host), on every
    redirect too, and never through an environment proxy,
  * caps the response size and time, and refuses XML with entity declarations.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

from core.newsfeed import FOR_YOU_DB, _write_lock, connect, now_iso, parse_feed, store_articles

PRIVATE_FEED_PREFIX = "u-"
MAX_FEEDS_PER_USER = 10
MAX_FEED_BYTES = 3 * 1024 * 1024
FETCH_TIMEOUT = 8.0
ALLOWED_PORTS = {None, 80, 443, 8080, 8443}
USER_AGENT = "Mozilla/5.0 (compatible; PithReader/1.0; RSS aggregator)"


class FeedError(ValueError):
    pass


def _public_addresses(host: str, port: Optional[int]):
    """Every address the host resolves to, or FeedError if any of them isn't on the public internet."""
    if not host:
        raise FeedError("That URL has no host")
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise FeedError("Couldn't find that site")
    out = []
    for family, _type, _proto, _name, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise FeedError("That address isn't on the public internet")
        out.append((family, sockaddr))
    return out


def _check_host(host: str, port: Optional[int]) -> None:
    _public_addresses(host, port)


def _connect_public(host: str, port: int, timeout) -> socket.socket:
    """Resolve, check and connect in one step, to the address that was checked."""
    last: Optional[OSError] = None
    for family, sockaddr in _public_addresses(host, port):
        sock = socket.socket(family, socket.SOCK_STREAM)
        if timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            sock.close()
            last = e
    raise last or FeedError("Couldn't connect to that site")


class _PublicHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = _connect_public(self.host, self.port, self.timeout)


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        sock = _connect_public(self.host, self.port, self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTPConnection, req)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=self._context)


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if len(url) > 500:
        raise FeedError("URL is too long")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FeedError("Feed URLs must start with http:// or https://")
    if parts.username or parts.password:
        raise FeedError("Feed URLs can't contain a username or password")
    if parts.port not in ALLOWED_PORTS:
        raise FeedError("That port isn't allowed")
    _check_host(parts.hostname or "", parts.port)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", parts.query, ""))


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 4

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(urllib.parse.urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SafeRedirect,
                                      _PublicHTTPHandler, _PublicHTTPSHandler)


def safe_fetch(url: str) -> bytes:
    url = validate_url(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
    })
    try:
        with _OPENER.open(req, timeout=FETCH_TIMEOUT) as resp:
            body = resp.read(MAX_FEED_BYTES + 1)
    except FeedError:
        raise
    except Exception as e:
        raise FeedError(f"Couldn't fetch that feed ({type(e).__name__})")
    if len(body) > MAX_FEED_BYTES:
        raise FeedError("That feed is too large")
    if re.search(rb"<!ENTITY", body, re.IGNORECASE):
        raise FeedError("That feed uses XML entity declarations, which aren't allowed")
    return body


def feed_title(xml_bytes: bytes, fallback: str) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        raise FeedError("That URL isn't an RSS or Atom feed")
    el = root.find("./channel/title")
    if el is None:
        el = root.find("{http://www.w3.org/2005/Atom}title")
    title = " ".join((el.text or "").split()) if el is not None else ""
    return (title or fallback)[:80]


def feed_id_for(url: str) -> str:
    return PRIVATE_FEED_PREFIX + hashlib.sha1(url.encode()).hexdigest()[:12]


def _feed_dict(fid: str, url: str, title: str) -> Dict[str, str]:
    return {"id": fid, "publisher": title, "topic": None, "url": url}


def add_feed(user_id: int, url: str, db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    url = validate_url(url)
    fid = feed_id_for(url)
    with connect(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM user_feeds WHERE user_id=?", (user_id,)).fetchone()[0]
        mine = conn.execute("SELECT 1 FROM user_feeds WHERE user_id=? AND feed_id=?", (user_id, fid)).fetchone()
        known = conn.execute("SELECT title FROM custom_feeds WHERE feed_id=?", (fid,)).fetchone()
    if mine:
        raise FeedError("You already follow that feed")
    if n >= MAX_FEEDS_PER_USER:
        raise FeedError(f"You can add up to {MAX_FEEDS_PER_USER} feeds")

    body = safe_fetch(url)
    title = known["title"] if known else feed_title(body, urllib.parse.urlsplit(url).hostname or "Custom feed")
    try:
        items = parse_feed(body, _feed_dict(fid, url, title))
    except ET.ParseError:
        raise FeedError("That URL isn't an RSS or Atom feed")
    if not items:
        raise FeedError("That feed has no stories we can read")
    ts = now_iso()
    with _write_lock, connect(db_path) as conn:
        conn.execute("""INSERT INTO custom_feeds (feed_id, url, title, created_at, last_fetched) VALUES (?,?,?,?,?)
                        ON CONFLICT(feed_id) DO UPDATE SET last_fetched=excluded.last_fetched, last_error=NULL""",
                     (fid, url, title, ts, ts))
        conn.execute("INSERT OR IGNORE INTO user_feeds (user_id, feed_id, added_at) VALUES (?,?,?)", (user_id, fid, ts))
    inserted = store_articles(items, db_path)
    return {"feed_id": fid, "title": title, "url": url, "items": len(items), "new": inserted}


def remove_feed(user_id: int, feed_id: str, db_path: str = FOR_YOU_DB) -> bool:
    with _write_lock, connect(db_path) as conn:
        removed = conn.execute("DELETE FROM user_feeds WHERE user_id=? AND feed_id=?", (user_id, feed_id)).rowcount
        # Nobody left reading it: stop fetching (its articles age out with prune_old).
        conn.execute("""DELETE FROM custom_feeds WHERE feed_id=? AND NOT EXISTS
                        (SELECT 1 FROM user_feeds WHERE feed_id=?)""", (feed_id, feed_id))
    return removed > 0


def list_feeds(user_id: int, db_path: str = FOR_YOU_DB) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute("""SELECT c.feed_id, c.url, c.title, c.last_fetched, c.last_error, u.added_at
                               FROM user_feeds u JOIN custom_feeds c ON c.feed_id = u.feed_id
                               WHERE u.user_id=? ORDER BY u.added_at DESC""", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def subscribed_feed_ids(user_id: Optional[int], db_path: str = FOR_YOU_DB) -> Set[str]:
    if not user_id:
        return set()
    with connect(db_path) as conn:
        return {r[0] for r in conn.execute("SELECT feed_id FROM user_feeds WHERE user_id=?", (user_id,))}


def refresh_custom(db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """Fetch every reader-added feed that still has a subscriber. Never raises."""
    report = {"ok": 0, "failed": 0, "inserted": 0}
    with connect(db_path) as conn:
        feeds = conn.execute("""SELECT feed_id, url, title FROM custom_feeds c WHERE EXISTS
                                (SELECT 1 FROM user_feeds u WHERE u.feed_id = c.feed_id)""").fetchall()
    for f in feeds:
        err = None
        try:
            items = parse_feed(safe_fetch(f["url"]), _feed_dict(f["feed_id"], f["url"], f["title"]))
            report["inserted"] += store_articles(items, db_path)
            report["ok"] += 1
        except Exception as e:  # FeedError, ParseError, anything else: record and move on
            err = str(e)[:200]
            report["failed"] += 1
        with _write_lock, connect(db_path) as conn:
            conn.execute("UPDATE custom_feeds SET last_fetched=?, last_error=? WHERE feed_id=?",
                         (now_iso(), err, f["feed_id"]))
    return report
