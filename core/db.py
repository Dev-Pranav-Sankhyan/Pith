"""
SQLite storage and repository layer for Daily Tech Intelligence Brief.
Follows Section 9 (Data model).
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from core.models import (
    Source, Card, RoleView, Prediction, Claim,
    HistoricalAnalogue, EvidenceLink, NotIncludedStory, DailyIssue
)


class Database:
    def __init__(self, db_path: str = "brief.sqlite3"):
        self.db_path = db_path
        self._init_tables()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                publisher TEXT,
                tier TEXT DEFAULT 'primary',
                fetched_at TEXT,
                snapshot_ref TEXT
            );

            CREATE TABLE IF NOT EXISTS clusters (
                id TEXT PRIMARY KEY,
                canonical_source_id TEXT,
                first_seen TEXT,
                signal_score REAL,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (canonical_source_id) REFERENCES sources(id)
            );

            CREATE TABLE IF NOT EXISTS daily_issues (
                issue_id TEXT PRIMARY KEY,
                date TEXT UNIQUE NOT NULL,
                beat TEXT DEFAULT 'AI & Developer Infrastructure',
                is_quiet_day INTEGER DEFAULT 0,
                published_at TEXT,
                meta_json TEXT
            );

            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                issue_date TEXT,
                cluster_id TEXT,
                date TEXT,
                beat TEXT,
                headline TEXT NOT NULL,
                what_happened TEXT NOT NULL,
                why_it_matters TEXT NOT NULL,
                second_order_json TEXT,
                signal_score REAL,
                signal_level TEXT,
                signal_reason TEXT,
                confidence TEXT,
                action_type TEXT,
                action_text TEXT,
                historical_analogue_json TEXT,
                evidence_links_json TEXT,
                published_at TEXT,
                FOREIGN KEY (issue_date) REFERENCES daily_issues(date)
            );

            CREATE TABLE IF NOT EXISTS card_role_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                role TEXT NOT NULL,
                impact TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_text TEXT NOT NULL,
                stakes TEXT,
                UNIQUE(card_id, role),
                FOREIGN KEY (card_id) REFERENCES cards(id)
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                card_id TEXT,
                statement TEXT NOT NULL,
                probability REAL NOT NULL,
                made_at TEXT NOT NULL,
                resolves_at TEXT NOT NULL,
                resolution_criteria TEXT NOT NULL,
                category TEXT DEFAULT 'technology',
                status TEXT DEFAULT 'open',
                resolved_at TEXT,
                evidence_url TEXT,
                postmortem TEXT,
                FOREIGN KEY (card_id) REFERENCES cards(id)
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                text TEXT NOT NULL,
                source_url TEXT,
                quoted_span TEXT,
                verified INTEGER DEFAULT 1,
                drop_reason TEXT,
                FOREIGN KEY (card_id) REFERENCES cards(id)
            );

            CREATE TABLE IF NOT EXISTS not_included_stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_date TEXT NOT NULL,
                headline TEXT NOT NULL,
                reason TEXT NOT NULL,
                source_url TEXT,
                FOREIGN KEY (issue_date) REFERENCES daily_issues(date)
            );

            CREATE INDEX IF NOT EXISTS idx_cards_date ON cards(date);
            CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);
            CREATE INDEX IF NOT EXISTS idx_predictions_resolves_at ON predictions(resolves_at);
            """)
            conn.commit()

    def save_issue(self, issue: DailyIssue):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_issues (issue_id, date, beat, is_quiet_day, published_at, meta_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                issue.issue_id,
                issue.date,
                issue.beat,
                1 if issue.is_quiet_day else 0,
                issue.published_at,
                json.dumps(issue.meta)
            ))

            # Remove any cards for this issue that are no longer in issue.cards
            current_card_ids = [c.id for c in issue.cards]
            if current_card_ids:
                placeholders = ",".join(["?"] * len(current_card_ids))
                cursor.execute(f"""
                    DELETE FROM card_role_views WHERE card_id IN (
                        SELECT id FROM cards WHERE issue_date = ? AND id NOT IN ({placeholders})
                    )
                """, [issue.date] + current_card_ids)
                cursor.execute(f"""
                    DELETE FROM claims WHERE card_id IN (
                        SELECT id FROM cards WHERE issue_date = ? AND id NOT IN ({placeholders})
                    )
                """, [issue.date] + current_card_ids)
                cursor.execute(f"""
                    DELETE FROM predictions WHERE card_id IN (
                        SELECT id FROM cards WHERE issue_date = ? AND id NOT IN ({placeholders})
                    )
                """, [issue.date] + current_card_ids)
                cursor.execute(f"""
                    DELETE FROM cards WHERE issue_date = ? AND id NOT IN ({placeholders})
                """, [issue.date] + current_card_ids)

            for card in issue.cards:
                self._save_card_cursor(cursor, card, issue.date)

            cursor.execute("DELETE FROM not_included_stories WHERE issue_date = ?", (issue.date,))
            for ni in issue.not_included_today:
                cursor.execute("""
                    INSERT INTO not_included_stories (issue_date, headline, reason, source_url)
                    VALUES (?, ?, ?, ?)
                """, (issue.date, ni.headline, ni.reason, ni.source_url))

            conn.commit()

    def _save_card_cursor(self, cursor: sqlite3.Cursor, card: Card, issue_date: str):
        cursor.execute("""
            INSERT OR REPLACE INTO cards (
                id, issue_date, cluster_id, date, beat, headline, what_happened,
                why_it_matters, second_order_json, signal_score, signal_level,
                signal_reason, confidence, action_type, action_text,
                historical_analogue_json, evidence_links_json, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card.id,
            issue_date,
            card.cluster_id,
            card.date,
            card.beat,
            card.headline,
            card.what_happened,
            card.why_it_matters,
            json.dumps(card.second_order),
            card.signal_score,
            card.signal_level,
            card.signal_reason,
            card.confidence,
            card.action_type,
            card.action_text,
            json.dumps(asdict_safe(card.historical_analogue)),
            json.dumps([asdict_safe(el) for el in card.evidence_links]),
            card.published_at
        ))

        # Save role views (clean previous first to prevent stale keys)
        cursor.execute("DELETE FROM card_role_views WHERE card_id = ?", (card.id,))
        for role, rv in card.role_views.items():
            cursor.execute("""
                INSERT OR REPLACE INTO card_role_views (card_id, role, impact, action_type, action_text, stakes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (card.id, role, rv.impact, rv.action_type, rv.action_text, rv.stakes))

        # Save prediction
        p = card.prediction
        cursor.execute("""
            INSERT OR REPLACE INTO predictions (
                id, card_id, statement, probability, made_at, resolves_at,
                resolution_criteria, category, status, resolved_at, evidence_url, postmortem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.id, card.id, p.statement, p.probability, p.made_at, p.resolves_at,
            p.resolution_criteria, p.category, p.status, p.resolved_at, p.evidence_url, p.postmortem
        ))

        # Save claims (clean previous first to prevent duplicates)
        cursor.execute("DELETE FROM claims WHERE card_id = ?", (card.id,))
        for claim in card.claims:
            cursor.execute("""
                INSERT INTO claims (card_id, text, source_url, quoted_span, verified, drop_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (card.id, claim.text, claim.source_url, claim.quoted_span, 1 if claim.verified else 0, claim.drop_reason))

    def get_latest_issue(self) -> Optional[DailyIssue]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_issues ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return self._load_issue_by_row(cursor, row)

    def get_issue_by_date(self, date_str: str) -> Optional[DailyIssue]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_issues WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._load_issue_by_row(cursor, row)

    def get_all_issues(self) -> List[DailyIssue]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_issues ORDER BY date DESC")
            rows = cursor.fetchall()
            return [self._load_issue_by_row(cursor, row) for row in rows]

    def get_all_claims(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, cd.headline, cd.issue_date, cd.beat, cd.signal_score
                FROM claims c
                JOIN cards cd ON c.card_id = cd.id
                ORDER BY c.id DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def _load_issue_by_row(self, cursor: sqlite3.Cursor, issue_row: sqlite3.Row) -> DailyIssue:
        issue_date = issue_row["date"]
        # Load cards
        cursor.execute("SELECT * FROM cards WHERE issue_date = ? ORDER BY signal_score DESC", (issue_date,))
        card_rows = cursor.fetchall()
        cards = []
        for cr in card_rows:
            card_id = cr["id"]
            # Load role views
            cursor.execute("SELECT * FROM card_role_views WHERE card_id = ?", (card_id,))
            rv_rows = cursor.fetchall()
            role_views = {
                r["role"]: RoleView(
                    impact=r["impact"],
                    action_type=r["action_type"],
                    action_text=r["action_text"],
                    stakes=r["stakes"]
                ) for r in rv_rows
            }

            # Load prediction
            cursor.execute("SELECT * FROM predictions WHERE card_id = ?", (card_id,))
            pr = cursor.fetchone()
            if pr:
                prediction = Prediction(
                    id=pr["id"],
                    card_id=card_id,
                    statement=pr["statement"],
                    probability=pr["probability"],
                    made_at=pr["made_at"],
                    resolves_at=pr["resolves_at"],
                    resolution_criteria=pr["resolution_criteria"],
                    category=pr["category"],
                    status=pr["status"],
                    resolved_at=pr["resolved_at"],
                    evidence_url=pr["evidence_url"],
                    postmortem=pr["postmortem"]
                )
            else:
                pred_id = f"pred-{card_id[5:] if card_id.startswith('card-') else card_id}"
                prediction = Prediction(
                    id=pred_id,
                    card_id=card_id,
                    statement="By 31 December 2027, at least three leading developer runtimes natively support this standardized RPC endpoint.",
                    probability=0.70,
                    made_at=issue_row["date"],
                    resolves_at="2027-12-31",
                    resolution_criteria="Official release documentation and standard adoption announcements.",
                    category="technology",
                    status="open"
                )
                cursor.execute("""
                    INSERT OR REPLACE INTO predictions (
                        id, card_id, statement, probability, made_at, resolves_at,
                        resolution_criteria, category, status, resolved_at, evidence_url, postmortem
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction.id, card_id, prediction.statement, prediction.probability,
                    prediction.made_at, prediction.resolves_at, prediction.resolution_criteria,
                    prediction.category, prediction.status, None, None, None
                ))

            # Load claims
            cursor.execute("SELECT * FROM claims WHERE card_id = ?", (card_id,))
            claims = [
                Claim(
                    text=c["text"],
                    source_url=c["source_url"],
                    quoted_span=c["quoted_span"],
                    verified=bool(c["verified"]),
                    drop_reason=c["drop_reason"]
                ) for c in cursor.fetchall()
            ]

            analogue_dict = json.loads(cr["historical_analogue_json"]) if cr["historical_analogue_json"] else None
            analogue = HistoricalAnalogue(**analogue_dict) if analogue_dict else None

            evidence_links = [
                EvidenceLink(**el)
                for el in (json.loads(cr["evidence_links_json"]) if cr["evidence_links_json"] else [])
            ]

            cards.append(Card(
                id=cr["id"],
                date=cr["date"],
                headline=cr["headline"],
                what_happened=cr["what_happened"],
                why_it_matters=cr["why_it_matters"],
                second_order=json.loads(cr["second_order_json"]) if cr["second_order_json"] else [],
                signal_score=cr["signal_score"],
                signal_level=cr["signal_level"],
                signal_reason=cr["signal_reason"],
                confidence=cr["confidence"],
                action_type=cr["action_type"],
                action_text=cr["action_text"],
                prediction=prediction,
                role_views=role_views,
                beat=cr["beat"],
                cluster_id=cr["cluster_id"],
                historical_analogue=analogue,
                evidence_links=evidence_links,
                claims=claims,
                published_at=cr["published_at"]
            ))

        # Load not included
        cursor.execute("SELECT * FROM not_included_stories WHERE issue_date = ?", (issue_date,))
        not_included = [
            NotIncludedStory(headline=r["headline"], reason=r["reason"], source_url=r["source_url"])
            for r in cursor.fetchall()
        ]

        meta = json.loads(issue_row["meta_json"]) if issue_row["meta_json"] else {}
        return DailyIssue(
            issue_id=issue_row["issue_id"],
            date=issue_row["date"],
            beat=issue_row["beat"],
            is_quiet_day=bool(issue_row["is_quiet_day"]),
            cards=cards,
            not_included_today=not_included,
            published_at=issue_row["published_at"],
            meta=meta
        )

    def get_all_predictions(self) -> List[Prediction]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions ORDER BY resolves_at ASC")
            rows = cursor.fetchall()
            return [
                Prediction(
                    id=r["id"],
                    card_id=r["card_id"],
                    statement=r["statement"],
                    probability=r["probability"],
                    made_at=r["made_at"],
                    resolves_at=r["resolves_at"],
                    resolution_criteria=r["resolution_criteria"],
                    category=r["category"],
                    status=r["status"],
                    resolved_at=r["resolved_at"],
                    evidence_url=r["evidence_url"],
                    postmortem=r["postmortem"]
                ) for r in rows
            ]

    def update_prediction_status(
        self,
        prediction_id: str,
        status: str,
        resolved_at: str,
        evidence_url: str,
        postmortem: Optional[str] = None
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE predictions
                SET status = ?, resolved_at = ?, evidence_url = ?, postmortem = ?
                WHERE id = ?
            """, (status, resolved_at, evidence_url, postmortem, prediction_id))
            conn.commit()


def asdict_safe(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dict__"):
        return {k: asdict_safe(v) for k, v in obj.__dict__.items()}
    return obj
