"""
A/B experiments for the For You ranker.

Readers are assigned to a variant deterministically (hash of experiment name + user id),
so assignment needs no storage and never flips. The first time a reader is ranked under an
experiment, an exposure row is written; `pipeline/experiment_report.py` compares variants on
satisfaction ("worth my time" rate) and 7-day return, never on raw clicks.

To retire an experiment, move the winning values into DEFAULT_PARAMS and delete the entry.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from core.newsfeed import FOR_YOU_DB, _write_lock, connect, now_iso

DEFAULT_PARAMS: Dict[str, Any] = {"mmr_lambda": 0.78, "explore_every": 6}

EXPERIMENTS: Dict[str, Dict[str, Any]] = {
    "explore_rate_v1": {
        "description": "Does more exploration (1 slot in 4 instead of 1 in 6, slightly more diversity) "
                       "raise satisfaction without hurting return visits?",
        "variants": {
            "control": {},
            "more_explore": {"explore_every": 4, "mmr_lambda": 0.72},
        },
    },
}

_exposed: set = set()  # (db, user, experiment) already written this process


def assign(user_id: int, experiment: str) -> str:
    variants = sorted(EXPERIMENTS[experiment]["variants"])
    h = int(hashlib.sha256(f"{experiment}:{user_id}".encode()).hexdigest(), 16)
    return variants[h % len(variants)]


def assignments(user_id: int) -> Dict[str, str]:
    return {name: assign(user_id, name) for name in EXPERIMENTS}


def params(user_id: Optional[int], db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """Ranker parameters for this reader, recording the exposure the first time."""
    out = dict(DEFAULT_PARAMS)
    if not user_id:
        return out
    for name, variant in assignments(user_id).items():
        out.update(EXPERIMENTS[name]["variants"][variant])
        key = (db_path, user_id, name)
        if key not in _exposed:
            with _write_lock, connect(db_path) as conn:
                conn.execute("""INSERT OR IGNORE INTO experiment_exposures (user_id, experiment, variant, first_seen)
                                VALUES (?,?,?,?)""", (user_id, name, variant, now_iso()))
            _exposed.add(key)
    return out
