"""
Pith Automated LLM Ingestion Pipeline.
Takes any raw article, announcement, or URL -> Scores signal -> Drafts Card ->
Verifies quoted spans -> Adds to SQLite Issue -> Rebuilds static assets.
Supports Google Gemini, OpenAI, Claude, Local Ollama, and Dry-Run simulation.
"""

import sys
import os
import argparse
import json
import re
import datetime
import urllib.request
from html.parser import HTMLParser
from typing import Dict, Any, Tuple

from core.models import (
    Card, RoleView, Prediction, Claim, HistoricalAnalogue,
    EvidenceLink, NotIncludedStory, DailyIssue
)
from core.scoring import ScoringEngine, extract_grounded_features
from core.verification import VerificationEngine
from core.prompts import (
    SYSTEM_DRAFT_PROMPT, generate_draft_prompt,
    SCORING_SYSTEM_PROMPT, generate_scoring_prompt,
    generate_kill_reason_prompt
)
from core.llm import get_llm_provider, clean_json_response
from core.db import Database
from pipeline.build_issue import build_static_artifacts
from pipeline.render_html import render_all


class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "noscript"):
            self.in_script = True
        elif tag == "style":
            self.in_style = True
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "noscript"):
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip() + " "
        elif not self.in_script and not self.in_style:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


def fetch_url_content(url: str) -> Tuple[str, str]:
    """Fetches text and title from a webpage URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PithBot/1.0"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw_html = resp.read().decode(charset, errors="ignore")
    
    extractor = SimpleHTMLTextExtractor()
    extractor.feed(raw_html)
    text = extractor.get_text()
    title = extractor.title.strip() or url
    return text, title


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:32] if slug else "item"


def run_pipeline(
    raw_text: str,
    metadata: Dict[str, str],
    provider_name: str = "auto",
    model: str = None,
    dry_run: bool = False,
    add_to_issue: bool = False,
    rebuild: bool = False,
    db_path: str = "brief.sqlite3"
) -> Dict[str, Any]:
    print("\n" + "="*60)
    print("✦ PITH AUTOMATED INTELLIGENCE PIPELINE")
    print("="*60)
    print(f"Title:     {metadata.get('title')}")
    print(f"Publisher: {metadata.get('publisher')}")
    print(f"URL:       {metadata.get('url')}")
    print(f"Provider:  {provider_name.upper()} (Dry-run: {dry_run})")
    print("-"*60)

    llm = get_llm_provider(provider_name=provider_name, model=model, dry_run=dry_run)

    # -------------------------------------------------------------
    # Step 1: Signal Scoring
    # -------------------------------------------------------------
    print("\n[Step 1/4] Evaluating 6-Factor Signal Scoring...")
    scoring_prompt = generate_scoring_prompt(raw_text, metadata)
    scoring_raw = llm.complete(SCORING_SYSTEM_PROMPT, scoring_prompt, json_mode=True)
    scoring_json = json.loads(clean_json_response(scoring_raw))

    llm_features = scoring_json.get("features", {})
    llm_penalties = scoring_json.get("penalties", {})

    # Ground model scores with empirical data (primary domains, pricing/API terms, outlet counts)
    grounded_features, grounded_penalties = extract_grounded_features(
        raw_text,
        url=metadata.get("url", ""),
        publisher=metadata.get("publisher", ""),
        outlet_count=metadata.get("outlet_count", 1),
        llm_features=llm_features
    )
    combined_penalties = {**grounded_penalties, **llm_penalties}

    engine = ScoringEngine()
    score, level, reason, breakdown = engine.compute_score(grounded_features, combined_penalties)

    print(f"  Score:    {score:.1f} / 100 ({level} Signal)")
    print(f"  Reason:   {reason}")
    for b in breakdown:
        print(f"    • {b}")

    # Check if below threshold (< 60)
    if score < 60.0:
        print("\n[RESULT] ✕ Below Signal Threshold (<60.0). Routing to 'Safely Ignore Today'...")
        kill_prompt = generate_kill_reason_prompt(raw_text, metadata)
        kill_raw = llm.complete("You write concise tech noise filters.", kill_prompt, json_mode=True)
        kill_json = json.loads(clean_json_response(kill_raw))

        ni_story = NotIncludedStory(
            headline=metadata.get("title", "Low Signal Tech Announcement"),
            reason=kill_json.get("reason", "Below signal threshold and lacks structural architecture impact."),
            source_url=metadata.get("url")
        )

        if add_to_issue:
            db = Database(db_path)
            issue = db.get_latest_issue()
            today_str = datetime.date.today().isoformat()
            if not issue or issue.date != today_str:
                issue = DailyIssue(
                    issue_id=f"issue-{today_str}",
                    date=today_str,
                    beat="AI & Developer Infrastructure",
                    cards=[],
                    not_included_today=[ni_story]
                )
            else:
                issue.not_included_today.append(ni_story)
            db.save_issue(issue)
            print(f"  ✓ Added to 'Safely Ignore Today' for Issue {issue.date}")

            if rebuild:
                build_static_artifacts(db_path)
                render_all(db_path)
                print("  ✓ Static artifacts & HTML rebuilt.")

        return {
            "status": "filtered",
            "score": score,
            "level": level,
            "kill_reason": ni_story.reason
        }

    # -------------------------------------------------------------
    # Step 2: Card Drafting Pass
    # -------------------------------------------------------------
    print("\n[Step 2/4] Drafting Intelligence Card with Structured JSON...")
    draft_prompt = generate_draft_prompt(raw_text, metadata)
    card_raw = llm.complete(SYSTEM_DRAFT_PROMPT, draft_prompt, json_mode=True)
    card_dict = json.loads(clean_json_response(card_raw))

    today_str = datetime.date.today().isoformat()
    import hashlib
    slug_source = card_dict.get("headline") or metadata.get("title", "shift")
    title_hash = hashlib.md5((metadata.get("title", "") + metadata.get("url", "")).encode("utf-8")).hexdigest()[:6]
    card_slug = slugify(slug_source)[:24] + f"-{title_hash}"
    card_id = f"card-{today_str.replace('-', '')}-{card_slug}"

    # Build Card dataclass
    prediction_data = card_dict.get("prediction", {})
    pred = Prediction(
        id=f"pred-{today_str.replace('-', '')}-{card_slug}",
        card_id=card_id,
        statement=prediction_data.get("statement", "By end of year, architecture standardizes."),
        probability=float(prediction_data.get("probability", 0.70)),
        made_at=today_str,
        resolves_at=prediction_data.get("resolves_at", "2027-12-31"),
        resolution_criteria=prediction_data.get("resolution_criteria", "Official release documentation."),
        category=prediction_data.get("category", "technology"),
        status="open"
    )

    role_views = {}
    for role_name in ("developer", "founder", "investor", "everyday"):
        rv = card_dict.get("role_views", {}).get(role_name, {})
        role_views[role_name] = RoleView(
            impact=rv.get("impact", "Material structural impact for this role."),
            action_type=rv.get("action_type", "DO"),
            action_text=rv.get("action_text", "Audit affected system components this week."),
            stakes=rv.get("stakes", "High")
        )

    analogue_dict = card_dict.get("historical_analogue")
    analogue = HistoricalAnalogue(
        analogue=analogue_dict.get("analogue", "Precedent shift."),
        where_it_breaks=analogue_dict.get("where_it_breaks", "Context differs.")
    ) if analogue_dict else None

    evidence = [
        EvidenceLink(
            title=metadata.get("title", "Primary Announcement"),
            url=metadata.get("url", ""),
            publisher=metadata.get("publisher", "Official Documentation"),
            tier="primary",
            quoted_span=card_dict.get("claims", [{}])[0].get("quoted_span", "") if card_dict.get("claims") else ""
        )
    ]

    claims = [
        Claim(
            text=c.get("text", ""),
            source_url=metadata.get("url", ""),
            quoted_span=c.get("quoted_span", ""),
            verified=True
        ) for c in card_dict.get("claims", [])
    ]

    card = Card(
        id=card_id,
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline=card_dict.get("headline", metadata.get("title")),
        what_happened=card_dict.get("what_happened", ""),
        why_it_matters=card_dict.get("why_it_matters", ""),
        second_order=card_dict.get("second_order", []),
        signal_score=score,
        signal_level=level,
        signal_reason=reason,
        confidence=card_dict.get("confidence", "High"),
        action_type=card_dict.get("action_type", "DO"),
        action_text=card_dict.get("action_text", role_views["developer"].action_text),
        prediction=pred,
        role_views=role_views,
        historical_analogue=analogue,
        evidence_links=evidence,
        claims=claims,
        published_at=f"{today_str}T07:00:00Z",
        factor_scores={k: round(float(v), 1) for k, v in grounded_features.items()}
    )

    # -------------------------------------------------------------
    # Step 3: Quoted-Span Verification Check
    # -------------------------------------------------------------
    print("\n[Step 3/4] Running Falsifiable Verification & Quote-Span Check...")
    verifier = VerificationEngine()
    card, claim_results, issues = verifier.verify_card(card, {metadata.get("url", ""): raw_text})

    print(f"  Claims verified: {len(card.claims)} / {len(claim_results)}")
    for cr in claim_results:
        status_mark = "✓" if cr["verified"] else "✕"
        print(f"    {status_mark} '{cr['claim'][:50]}...' -> span: '{cr['quoted_span'][:40]}...'")
        if not cr["verified"]:
            print(f"      Reason: {cr['drop_reason']}")

    if issues:
        print("  Verification warnings:")
        for iss in issues:
            print(f"    ! {iss}")

    # Validate card schema
    validation_errs = card.validate()
    if validation_errs:
        print("  ✕ Card schema validation failed:")
        for err in validation_errs:
            print(f"    - {err}")
        return {"status": "validation_failed", "errors": validation_errs}

    print("\n[Step 4/4] Verified Card Summary:")
    print(f"  Headline:     {card.headline}")
    print(f"  What Happened:{card.what_happened}")
    print(f"  Why Matters:  {card.why_it_matters}")
    print(f"  Prediction:   {card.prediction.probability * 100:.0f}% -> {card.prediction.statement}")
    print(f"  Dev Action:   [{card.role_views['developer'].action_type}] {card.role_views['developer'].action_text}")

    # -------------------------------------------------------------
    # Persistence & Rebuild
    # -------------------------------------------------------------
    if add_to_issue:
        db = Database(db_path)
        issue = db.get_latest_issue()
        if not issue or issue.date != today_str:
            issue = DailyIssue(
                issue_id=f"issue-{today_str}",
                date=today_str,
                beat="AI & Developer Infrastructure",
                cards=[card],
                not_included_today=[]
            )
        else:
            # Replace existing card with same ID or append (max 5)
            existing_ids = [c.id for c in issue.cards]
            if card.id in existing_ids:
                idx = existing_ids.index(card.id)
                issue.cards[idx] = card
            elif len(issue.cards) < 5:
                issue.cards.append(card)
            else:
                print("  ! Issue already has 5 cards. Replacing lowest score card.")
                issue.cards.sort(key=lambda c: c.signal_score)
                issue.cards[0] = card

        db.save_issue(issue)
        print(f"\n✓ Card successfully committed to SQLite issue {issue.date} ({len(issue.cards)} cards active).")

        if rebuild:
            build_static_artifacts(db_path)
            render_all(db_path)
            print("✓ Static RSS, JSON feeds, and HTML pages regenerated successfully.")

    return {
        "status": "success",
        "card": card.to_dict(),
        "card_obj": card,
        "score": score,
        "level": level
    }


def main():
    parser = argparse.ArgumentParser(description="Pith Automated LLM Ingestion Pipeline")
    parser.add_argument("--url", type=str, help="Web URL to fetch and process")
    parser.add_argument("--file", type=str, help="Local text or markdown file")
    parser.add_argument("--text", type=str, help="Raw text string to ingest")
    parser.add_argument("--title", type=str, default="", help="Article or release title")
    parser.add_argument("--publisher", type=str, default="", help="Publisher or source organization")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "gemini", "openai", "anthropic", "ollama", "simulated"])
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--dry-run", action="store_true", help="Run simulated LLM for testing without API keys")
    parser.add_argument("--add-to-issue", action="store_true", help="Commit verified card to today's SQLite issue")
    parser.add_argument("--rebuild", action="store_true", help="Re-render HTML and feeds after adding")
    parser.add_argument("--db", type=str, default="brief.sqlite3", help="Database path")

    args = parser.parse_args()

    raw_text = ""
    title = args.title
    publisher = args.publisher
    source_url = args.url or ""

    if args.url:
        print(f"Fetching {args.url}...")
        try:
            fetched_text, fetched_title = fetch_url_content(args.url)
            raw_text = fetched_text
            if not title:
                title = fetched_title
            if not publisher:
                publisher = urllib.parse.urlparse(args.url).netloc
        except Exception as e:
            print(f"Error fetching URL: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw_text = f.read()
        if not title:
            title = os.path.basename(args.file)
        if not publisher:
            publisher = "Local File"
    elif args.text:
        raw_text = args.text
        if not title:
            title = "Manual Ingestion"
        if not publisher:
            publisher = "Terminal Input"
    else:
        # If no input provided, default to dry-run demo
        print("No --url, --file, or --text provided. Running demo dry-run ingestion...")
        args.dry_run = True
        title = "Open Agent Protocol Initiative Launch"
        publisher = "Linux Foundation Press"
        source_url = "https://www.linuxfoundation.org/press/open-agent-protocol"
        raw_text = """The Linux Foundation and CNCF announced the creation of the Open Agent Protocol (OAP), a vendor-neutral standard for connecting AI models to external tools, databases, and enterprise software.
        Under the charter, working group members will establish open governance for Model Context Protocol and cross-platform agent execution specs.
        Database vendors and client IDEs will be able to implement standardized JSON-RPC endpoints, removing the need for proprietary bilateral integration agreements.
        """

    metadata = {
        "title": title,
        "publisher": publisher,
        "url": source_url
    }

    result = run_pipeline(
        raw_text=raw_text,
        metadata=metadata,
        provider_name=args.provider,
        model=args.model,
        dry_run=args.dry_run,
        add_to_issue=args.add_to_issue,
        rebuild=args.rebuild,
        db_path=args.db
    )

    if result.get("status") == "success":
        print("\n✦ Pipeline completed successfully.")
    elif result.get("status") == "filtered":
        print("\n✦ Story filtered out as low-signal.")
    else:
        print(f"\n✕ Pipeline exited with status: {result.get('status')}")


if __name__ == "__main__":
    main()
