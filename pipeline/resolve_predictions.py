"""
Human-in-the-loop prediction resolution.

Nothing in Pith marks a forecast correct or wrong automatically. This tool lists
what is due and records a named reviewer's verdict in the append-only
`prediction_resolutions` log. A later verdict on the same prediction is a
correction that supersedes the earlier one; the earlier row is kept forever.

Usage:
    python3 -m pipeline.resolve_predictions due [--as-of YYYY-MM-DD]
    python3 -m pipeline.resolve_predictions show <prediction_id>
    python3 -m pipeline.resolve_predictions draft <prediction_id> --evidence <url> [--provider anthropic]
    python3 -m pipeline.resolve_predictions resolve <prediction_id> \\
        --status correct|wrong|void --evidence <url> --by "<reviewer>" [--note "<post-mortem>"]

After resolving, re-render the site:  python3 -m pipeline.render_html
"""

import argparse
import json
import sys
from typing import Dict, List, Optional

from core.db import Database
from core.ledger import LedgerEngine


def due(db: Database, as_of: Optional[str] = None) -> List:
    live = [p for p in db.get_all_predictions() if LedgerEngine.is_live(p)]
    return LedgerEngine.get_due_predictions(live, as_of_date=as_of)


DRAFT_SYSTEM = (
    "You check whether a dated, falsifiable forecast came true. You are given the forecast, "
    "its resolution criterion and the text of one evidence page. Judge only from that page. "
    "Reply with JSON only: {\"verdict\": \"correct\"|\"wrong\"|\"insufficient\", "
    "\"quote\": \"<exact sentence copied from the page that decides it, or empty>\", "
    "\"reasoning\": \"<two sentences>\"}. Use \"insufficient\" unless the page clearly settles the criterion."
)


def draft_verdict(prediction, page_text: str, llm) -> Dict:
    """Ask an LLM for a suggested verdict. The quote must appear verbatim in the page,
    the same rule core/verification.py applies to card claims; otherwise the draft is
    downgraded to 'insufficient'. Nothing is recorded: a human still runs `resolve`."""
    from core.llm import clean_json_response
    prompt = (
        f"FORECAST ({int(prediction.probability * 100)}%, made {prediction.made_at}, due {prediction.resolves_at}):\n"
        f"{prediction.statement}\n\nRESOLUTION CRITERION:\n{prediction.resolution_criteria}\n\n"
        f"EVIDENCE PAGE TEXT:\n{page_text[:60000]}"
    )
    raw = llm.complete(DRAFT_SYSTEM, prompt, json_mode=True)
    try:
        out = json.loads(clean_json_response(raw))
    except (ValueError, TypeError):
        return {"verdict": "insufficient", "quote": "", "reasoning": "Model reply was not valid JSON.", "quote_verified": False}
    verdict = out.get("verdict") if out.get("verdict") in ("correct", "wrong", "insufficient") else "insufficient"
    quote = (out.get("quote") or "").strip()
    norm = lambda t: " ".join(t.split()).lower()
    verified = bool(quote) and norm(quote) in norm(page_text)
    if verdict != "insufficient" and not verified:
        verdict = "insufficient"
        out["reasoning"] = f"Downgraded: quoted sentence not found on the page. Model said: {out.get('reasoning', '')}"
    return {"verdict": verdict, "quote": quote, "reasoning": out.get("reasoning", ""), "quote_verified": verified}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="brief.sqlite3")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("due", help="List live predictions whose resolution date has passed")
    d.add_argument("--as-of")

    s = sub.add_parser("show", help="Show a prediction and its full resolution history")
    s.add_argument("prediction_id")

    dr = sub.add_parser("draft", help="LLM-suggested verdict from one evidence page (records nothing)")
    dr.add_argument("prediction_id")
    dr.add_argument("--evidence", required=True, help="URL of the page to judge from")
    dr.add_argument("--provider", default="auto")

    r = sub.add_parser("resolve", help="Record a reviewer's verdict")
    r.add_argument("prediction_id")
    r.add_argument("--status", required=True, choices=["correct", "wrong", "void"])
    r.add_argument("--evidence", help="URL proving the outcome (required for correct/wrong)")
    r.add_argument("--by", required=True, help="Name of the human reviewer")
    r.add_argument("--note", help="Post-mortem / what actually happened")
    r.add_argument("--resolved-at", help="Date the outcome became knowable (default: today)")

    args = ap.parse_args(argv)
    db = Database(args.db)

    if args.cmd == "due":
        items = due(db, args.as_of)
        if not items:
            print("No live predictions are due.")
            return 0
        for p in items:
            print(f"{p.id}\n  {int(p.probability * 100)}%  {p.statement}\n"
                  f"  criterion: {p.resolution_criteria}\n  due: {p.resolves_at}  (made {p.made_at})\n")
        print(f"{len(items)} due. Resolve each with: python3 -m pipeline.resolve_predictions resolve <id> ...")
        return 0

    if args.cmd == "show":
        preds = {p.id: p for p in db.get_all_predictions()}
        p = preds.get(args.prediction_id)
        if not p:
            print(f"Unknown prediction: {args.prediction_id}", file=sys.stderr)
            return 1
        print(f"{p.id} [{p.provenance}] {p.status}\n  {int(p.probability * 100)}%  {p.statement}\n"
              f"  criterion: {p.resolution_criteria}\n  made {p.made_at}, resolves {p.resolves_at}")
        for h in db.get_resolution_history(p.id):
            sup = f" (supersedes #{h['supersedes_id']})" if h["supersedes_id"] else ""
            print(f"  #{h['id']} {h['status']} by {h['resolved_by']} on {h['resolved_at']}{sup}\n"
                  f"      evidence: {h['evidence_url']}\n      note: {h['postmortem']}")
        return 0

    if args.cmd == "draft":
        from core.llm import get_llm_provider, SimulatedProvider
        from pipeline.ingest_llm import fetch_url_content
        p = {x.id: x for x in db.get_all_predictions()}.get(args.prediction_id)
        if not p:
            print(f"Unknown prediction: {args.prediction_id}", file=sys.stderr)
            return 1
        llm = get_llm_provider(provider_name=args.provider)
        if isinstance(llm, SimulatedProvider):
            print("No LLM provider configured (set ANTHROPIC_API_KEY or PITH_LLM_PROVIDER). Nothing drafted.", file=sys.stderr)
            return 1
        text, title = fetch_url_content(args.evidence)
        d = draft_verdict(p, text, llm)
        print(f"Suggested verdict: {d['verdict'].upper()}  (quote verified on page: {d['quote_verified']})")
        print(f"Page: {title}\nQuote: {d['quote'] or '-'}\nReasoning: {d['reasoning']}\n")
        if d["verdict"] in ("correct", "wrong"):
            print("If you agree, record it yourself:\n"
                  f"  python3 -m pipeline.resolve_predictions resolve {p.id} --status {d['verdict']} "
                  f"--evidence '{args.evidence}' --by \"<your name>\" --note \"...\"")
        return 0

    if args.cmd == "resolve":
        try:
            rid = db.record_resolution(
                args.prediction_id, args.status, args.evidence, args.note, args.by, args.resolved_at
            )
        except (ValueError, KeyError) as e:
            print(f"Refused: {e}", file=sys.stderr)
            return 1
        print(f"Recorded resolution #{rid}. Re-render with: python3 -m pipeline.render_html")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
