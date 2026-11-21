"""
SQLite storage and repository layer for Daily Tech Intelligence Brief.
Follows Section 9 (Data model).
"""

import sqlite3
import json
import datetime
from contextlib import contextmanager
from typing import Iterator, List, Optional, Dict, Any
from core.models import (
    Source, Card, RoleView, Prediction, Claim,
    HistoricalAnalogue, EvidenceLink, NotIncludedStory, DailyIssue
)


class Database:
    def __init__(self, db_path: str = "brief.sqlite3"):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Short-lived connection: commits on success, rolls back on error, always closes."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            # brief.sqlite3 is committed to git by the daily CI job, so keep every write
            # in the main file (rollback journal), never in a side -wal file git could miss.
            conn.execute("PRAGMA busy_timeout=10000")
            try:
                conn.execute("PRAGMA journal_mode=DELETE")
            except sqlite3.OperationalError:
                pass  # another process holds the file; the switch happens on a later connection
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

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
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
            """)
            self._migrate(conn)

    # Numbered, append-only migrations. Never edit a shipped one; add a new entry.
    MIGRATIONS = [
        # 1: provenance + resolver on predictions; mark hand-written seed data as illustrative.
        """
        ALTER TABLE predictions ADD COLUMN provenance TEXT NOT NULL DEFAULT 'live';
        ALTER TABLE predictions ADD COLUMN resolved_by TEXT;
        UPDATE predictions SET provenance = 'illustrative' WHERE id LIKE 'hist-pred-%';
        """,
        # 2: append-only resolution log. predictions.status is a cache of the latest row here.
        """
        CREATE TABLE IF NOT EXISTS prediction_resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id TEXT NOT NULL REFERENCES predictions(id),
            status TEXT NOT NULL CHECK (status IN ('correct', 'wrong', 'void')),
            evidence_url TEXT,
            postmortem TEXT,
            resolved_by TEXT NOT NULL,
            resolved_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            supersedes_id INTEGER REFERENCES prediction_resolutions(id)
        );
        CREATE INDEX IF NOT EXISTS idx_resolutions_pred ON prediction_resolutions(prediction_id, id);
        CREATE TRIGGER IF NOT EXISTS trg_resolutions_no_update
            BEFORE UPDATE ON prediction_resolutions
            BEGIN SELECT RAISE(ABORT, 'prediction_resolutions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS trg_resolutions_no_delete
            BEFORE DELETE ON prediction_resolutions
            BEGIN SELECT RAISE(ABORT, 'prediction_resolutions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS trg_predictions_immutable_forecast
            BEFORE UPDATE OF statement, probability, resolves_at, resolution_criteria, made_at ON predictions
            WHEN OLD.made_at < date('now')
            BEGIN SELECT RAISE(ABORT, 'forecast fields are immutable after publication day'); END;
        """,
        # 3: per-card factor ratings, so scoring weights can be audited against outcomes.
        """
        ALTER TABLE cards ADD COLUMN factor_scores_json TEXT;
        """,
    ]

    def _migrate(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = row[0] or 0
        for version, sql in enumerate(self.MIGRATIONS, start=1):
            if version <= current:
                continue
            for stmt in _split_sql(sql):
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    # Column already present (DB created by a newer CREATE TABLE) is fine.
                    if "duplicate column" not in str(e):
                        raise
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))

    def get_factor_outcomes(self) -> List[Dict[str, Any]]:
        """Live, resolved (correct/wrong) forecasts joined to the factor ratings of their card."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT p.id, p.status, p.probability, c.factor_scores_json
                FROM predictions p JOIN cards c ON c.id = p.card_id
                WHERE p.provenance = 'live' AND p.status IN ('correct', 'wrong')
                  AND c.factor_scores_json IS NOT NULL AND c.factor_scores_json != '{}'
            """).fetchall()
            return [
                {"id": r["id"], "outcome": 1.0 if r["status"] == "correct" else 0.0,
                 "probability": r["probability"], "factors": json.loads(r["factor_scores_json"])}
                for r in rows
            ]

    def schema_version(self) -> int:
        with self.get_connection() as conn:
            return conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0

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
                    DELETE FROM predictions WHERE status = 'open' AND card_id IN (
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
                historical_analogue_json, evidence_links_json, published_at, factor_scores_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            card.published_at,
            json.dumps(card.factor_scores or {}),
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
        if p is not None:
            self._upsert_prediction_cursor(cursor, p, card.id)

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
                    postmortem=pr["postmortem"],
                    provenance=pr["provenance"],
                    resolved_by=pr["resolved_by"],
                )
            else:
                # Legacy card with no recorded forecast: show none rather than inventing one.
                prediction = None

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
                published_at=cr["published_at"],
                factor_scores=json.loads(cr["factor_scores_json"]) if cr["factor_scores_json"] else {},
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
                    postmortem=r["postmortem"],
                    provenance=r["provenance"],
                    resolved_by=r["resolved_by"],
                ) for r in rows
            ]

    def _upsert_prediction_cursor(self, cursor: sqlite3.Cursor, p: Prediction, card_id: Optional[str]):
        """Insert a new forecast. On conflict, refresh forecast text only while the
        prediction is still open and was made today (a same-day redraft). Resolution
        fields are owned by record_resolution() and are never written here."""
        cursor.execute("""
            INSERT INTO predictions (
                id, card_id, statement, probability, made_at, resolves_at,
                resolution_criteria, category, status, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            ON CONFLICT(id) DO UPDATE SET
                card_id = excluded.card_id,
                statement = excluded.statement,
                probability = excluded.probability,
                resolves_at = excluded.resolves_at,
                resolution_criteria = excluded.resolution_criteria,
                category = excluded.category
            WHERE predictions.status = 'open' AND predictions.made_at >= date('now')
        """, (
            p.id, card_id, p.statement, p.probability, p.made_at, p.resolves_at,
            p.resolution_criteria, p.category, p.provenance,
        ))

    def save_prediction(self, p: Prediction) -> None:
        """Store a standalone prediction (e.g. illustrative examples) plus any resolution it carries."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            self._upsert_prediction_cursor(cur, p, p.card_id)
            if p.status in ("correct", "wrong", "void"):
                existing = cur.execute(
                    "SELECT 1 FROM prediction_resolutions WHERE prediction_id = ?", (p.id,)
                ).fetchone()
                if not existing:
                    self._record_resolution_cursor(
                        cur, p.id, p.status, p.evidence_url, p.postmortem,
                        p.resolved_by or "seed", p.resolved_at,
                    )

    def _record_resolution_cursor(self, cur, prediction_id, status, evidence_url, postmortem,
                                  resolved_by, resolved_at=None) -> int:
        if status not in ("correct", "wrong", "void"):
            raise ValueError(f"Invalid resolution status: {status}")
        if not resolved_by or not resolved_by.strip():
            raise ValueError("resolved_by is required: every resolution needs a named human reviewer")
        if status in ("correct", "wrong") and not evidence_url:
            raise ValueError("evidence_url is required to resolve a prediction correct or wrong")
        row = cur.execute("SELECT status FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown prediction: {prediction_id}")
        prev = cur.execute(
            "SELECT id FROM prediction_resolutions WHERE prediction_id = ? ORDER BY id DESC LIMIT 1",
            (prediction_id,),
        ).fetchone()
        resolved_at = resolved_at or datetime.date.today().isoformat()
        cur.execute("""
            INSERT INTO prediction_resolutions
                (prediction_id, status, evidence_url, postmortem, resolved_by, resolved_at, recorded_at, supersedes_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id, status, evidence_url, postmortem, resolved_by.strip(), resolved_at,
            datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            prev["id"] if prev else None,
        ))
        new_id = cur.lastrowid
        cur.execute("""
            UPDATE predictions
            SET status = ?, resolved_at = ?, evidence_url = ?, postmortem = ?, resolved_by = ?
            WHERE id = ?
        """, (status, resolved_at, evidence_url, postmortem, resolved_by.strip(), prediction_id))
        return new_id

    def record_resolution(self, prediction_id: str, status: str, evidence_url: Optional[str],
                          postmortem: Optional[str], resolved_by: str,
                          resolved_at: Optional[str] = None) -> int:
        """The only way to resolve a prediction. Appends to the immutable log; a later call
        is a correction that supersedes (never erases) the earlier verdict."""
        with self.get_connection() as conn:
            return self._record_resolution_cursor(
                conn.cursor(), prediction_id, status, evidence_url, postmortem, resolved_by, resolved_at
            )

    def get_resolution_history(self, prediction_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM prediction_resolutions WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_prediction_status(
        self,
        prediction_id: str,
        status: str,
        resolved_at: str,
        evidence_url: str,
        postmortem: Optional[str] = None,
        resolved_by: str = "editor",
    ):
        """Deprecated: kept for callers; delegates to record_resolution()."""
        self.record_resolution(prediction_id, status, evidence_url, postmortem, resolved_by, resolved_at)


def asdict_safe(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dict__"):
        return {k: asdict_safe(v) for k, v in obj.__dict__.items()}
    return obj


def _split_sql(script: str) -> List[str]:
    """Split a migration into statements, keeping CREATE TRIGGER ... END blocks whole."""
    out, buf = [], ""
    for piece in script.split(";"):
        buf += piece + ";"
        if sqlite3.complete_statement(buf):
            if buf.strip(" \n;"):
                out.append(buf.strip())
            buf = ""
    return out
