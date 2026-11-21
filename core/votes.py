"""Reader votes on Pith forecasts ("Beat the Brief"), stored in foryou.sqlite3."""

from typing import Dict

from core.newsfeed import FOR_YOU_DB, connect, now_iso

VOTES = ("higher", "agree", "lower")


def cast_vote(user_id: int, card_id: str, vote: str, db_path: str = FOR_YOU_DB) -> None:
    if vote not in VOTES:
        raise ValueError(f"vote must be one of {VOTES}")
    if not card_id or len(card_id) > 200:
        raise ValueError("invalid card_id")
    ts = now_iso()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO forecast_votes (user_id, card_id, vote, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, card_id) DO UPDATE SET vote = excluded.vote, updated_at = excluded.updated_at
            """,
            (user_id, card_id, vote, ts, ts),
        )


def counts(card_id: str, db_path: str = FOR_YOU_DB) -> Dict[str, int]:
    out = {v: 0 for v in VOTES}
    with connect(db_path) as conn:
        for row in conn.execute(
            "SELECT vote, COUNT(*) AS n FROM forecast_votes WHERE card_id = ? GROUP BY vote", (card_id,)
        ):
            out[row["vote"]] = row["n"]
    return out
