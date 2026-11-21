"""
Audit the 6-factor scoring weights against how live forecasts actually resolved.

    python3 -m pipeline.tune_scoring            # report only
    python3 -m pipeline.tune_scoring --apply    # also write scoring_weights.json

Nothing changes until at least MIN_TUNING_SAMPLE live forecasts have resolved.
"""

import argparse
import json
import os
import sys

from core.db import Database
from core.scoring import DEFAULT_WEIGHTS, MIN_TUNING_SAMPLE, ScoringEngine, outcome_correlations

WEIGHTS_FILE = "scoring_weights.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="brief.sqlite3")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    rows = Database(args.db).get_factor_outcomes()
    print(f"{len(rows)} resolved live forecasts with factor ratings (need {MIN_TUNING_SAMPLE}).")
    corr = outcome_correlations(rows)
    if not corr:
        print("Not enough data yet. Weights unchanged.")
        return 0
    engine = ScoringEngine(weights=dict(DEFAULT_WEIGHTS))
    engine.tune_weights(corr)
    for f in DEFAULT_WEIGHTS:
        print(f"  {f:32s} r={corr.get(f, 0):+.3f}  {DEFAULT_WEIGHTS[f]:.3f} -> {engine.weights[f]:.3f}")
    if args.apply:
        with open(WEIGHTS_FILE, "w") as fh:
            json.dump({"weights": engine.weights, "sample": len(rows), "correlations": corr}, fh, indent=2)
        print(f"Wrote {WEIGHTS_FILE}. ScoringEngine picks it up on the next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
