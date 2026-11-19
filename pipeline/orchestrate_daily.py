"""
Pith Master Daily Intelligence Orchestrator.
Runs the complete autonomous daily publishing loop:
1. Multi-source intelligence collection (Hacker News, arXiv, OSS runtimes, lab blogs)
2. 6-Factor signal scoring & penalty audit (killing PR/hype)
3. 4-Role intelligence drafting (Developer, Founder, Investor, Everyday Person)
4. Falsifiable prediction generation with Brier resolve dates
5. Verification & quote grounding pass
6. Compilation into SQLite issue (Top 5 Cards + Safely Ignore Today)
7. Static asset generation (index.html, ledger.html, patterns.html, feed.json, rss.xml)
8. Studio audio synthesis & mastering (ElevenLabs + FFmpeg broadcast loudnorm)
"""

import os
import sys
import argparse
import datetime
import json
from typing import List, Dict, Any

from core.db import Database
from core.models import DailyIssue, Card, NotIncludedStory
from core.sources import SourceCollector
from pipeline.ingest_llm import run_pipeline, fetch_url_content
from pipeline.build_issue import build_static_artifacts
from pipeline.render_html import render_all
from pipeline.audio_brief import generate_audio_briefs


def run_daily_pipeline(
    dry_run: bool = False,
    skip_audio: bool = False,
    provider: str = "auto",
    model: str = None,
    db_path: str = "brief.sqlite3",
    output_dir: str = "public"
) -> Dict[str, Any]:
    today_str = datetime.date.today().isoformat()
    today_formatted = datetime.date.today().strftime("%d %B %Y")

    print("\n" + "="*70)
    print(f"✦ PITH DAILY AUTONOMOUS INTELLIGENCE RUNNER · {today_formatted.upper()}")
    print("="*70)
    print(f"Mode:          {'DRY RUN (Simulation)' if dry_run else 'LIVE PRODUCTION'}")
    print(f"LLM Provider:  {provider.upper()}")
    print(f"Audio Enabled: {not skip_audio}")
    print(f"Database:      {db_path}")
    print(f"Output Dir:    {output_dir}")
    print("-"*70)

    # 1. Source Collection
    print("\n[Phase 1/5] Collecting candidates from multi-channel streams...")
    candidates = SourceCollector.fetch_daily_candidates()
    print(f"  Collected {len(candidates)} candidate stories.")

    accepted_cards: List[Card] = []
    ignored_stories: List[NotIncludedStory] = []

    # 2. Scoring & Drafting Pipeline
    print("\n[Phase 2/5] Running signal scoring, drafting & quote verification...")
    for idx, candidate in enumerate(candidates, start=1):
        title = candidate.get("title", f"Candidate {idx}")
        url = candidate.get("url", "https://news.ycombinator.com")
        publisher = candidate.get("publisher", "Technical Feed")
        raw_text = candidate.get("raw_text")

        if not raw_text and url and not dry_run:
            try:
                print(f"  Fetching full text for candidate {idx}: {title[:50]}...")
                raw_text, _ = fetch_url_content(url)
            except Exception as e:
                print(f"  Warning: failed to fetch URL {url}: {e}")
                raw_text = f"Title: {title}\nSource: {publisher}\nURL: {url}\nArchitectural report regarding core system modifications."

        if not raw_text:
            raw_text = f"Title: {title}\nSource: {publisher}\nURL: {url}\nStructural technology shift affecting inference unit economics and system design."

        metadata = {
            "title": title,
            "publisher": publisher,
            "url": url
        }

        try:
            result = run_pipeline(
                raw_text=raw_text,
                metadata=metadata,
                provider_name=provider,
                model=model,
                dry_run=dry_run,
                add_to_issue=False,
                rebuild=False,
                db_path=db_path
            )

            if result.get("status") == "success":
                card_obj = result.get("card_obj") or Card.from_dict(result["card"])
                accepted_cards.append(card_obj)
            elif result.get("status") == "filtered":
                ignored_stories.append(NotIncludedStory(
                    headline=title,
                    reason=result.get("kill_reason", "Below signal threshold (<60.0)."),
                    source_url=url
                ))
        except Exception as e:
            print(f"  ✕ Error processing candidate '{title[:40]}': {e}")

    print(f"\n  Pipeline Results: {len(accepted_cards)} passed signal threshold, {len(ignored_stories)} routed to Safely Ignore.")

    # 3. Issue Construction
    print("\n[Phase 3/5] Selecting Top 5 Structural Cards for Today's Issue...")
    # Sort accepted cards by signal score descending
    accepted_cards.sort(key=lambda c: getattr(c, "signal_score", 70.0), reverse=True)
    top_5_cards = accepted_cards[:5]

    # If we got fewer than 5 (e.g. offline dry-run or low volume), retain existing issue cards
    db = Database(db_path)
    existing_issue = db.get_latest_issue()
    if len(top_5_cards) < 5 and existing_issue and existing_issue.cards:
        print(f"  Supplementing with {5 - len(top_5_cards)} benchmark cards from existing issue...")
        needed = 5 - len(top_5_cards)
        existing_ids = {c.id for c in top_5_cards}
        for ec in existing_issue.cards:
            if ec.id not in existing_ids:
                top_5_cards.append(ec)
                if len(top_5_cards) >= 5:
                    break

    # Safely Ignore: top 3-5 stories
    final_ignored = ignored_stories[:5]
    if len(final_ignored) < 3 and existing_issue and existing_issue.not_included_today:
        needed_ni = 3 - len(final_ignored)
        existing_headlines = {ni.headline for ni in final_ignored}
        for eni in existing_issue.not_included_today:
            if eni.headline not in existing_headlines:
                final_ignored.append(eni)
                if len(final_ignored) >= 3:
                    break

    daily_issue = DailyIssue(
        issue_id=f"issue-{today_str}",
        date=today_str,
        beat="AI & Developer Infrastructure",
        cards=top_5_cards,
        not_included_today=final_ignored
    )

    db.save_issue(daily_issue)
    print(f"  ✓ Issue saved to {db_path} with {len(daily_issue.cards)} cards and {len(daily_issue.not_included_today)} filtered stories.")

    # 4. Static Asset Rendering & Feeds
    print("\n[Phase 4/5] Building static web pages and distribution feeds...")
    build_static_artifacts(db_path=db_path, output_dir=output_dir)
    render_all(db_path=db_path, output_dir=output_dir)
    print("  ✓ index.html, ledger.html, patterns.html, feed.json, and rss.xml compiled.")

    # 5. Studio Audio Briefing
    audio_results = {}
    if not skip_audio:
        print("\n[Phase 5/5] Synthesizing Studio Voice Briefings via ElevenLabs & FFmpeg...")
        audio_dir = os.path.join(output_dir, "audio")
        try:
            generate_audio_briefs(db_path=db_path, output_dir=audio_dir)
            audio_results = {
                "developer": os.path.exists(os.path.join(audio_dir, "brief-developer.mp3")),
                "founder": os.path.exists(os.path.join(audio_dir, "brief-founder.mp3")),
                "investor": os.path.exists(os.path.join(audio_dir, "brief-investor.mp3")),
                "everyday": os.path.exists(os.path.join(audio_dir, "brief-everyday.mp3"))
            }
            print("  ✓ Studio audio briefing pipeline complete.")
        except Exception as e:
            print(f"  ✕ Warning: Audio briefing generation encountered error: {e}")
    else:
        print("\n[Phase 5/5] Audio briefing skipped (--skip-audio).")

    print("\n" + "="*70)
    print(f"✦ PITH DAILY ISSUE FOR {today_formatted.upper()} IS PUBLISHED")
    print("="*70)
    for i, card in enumerate(daily_issue.cards, start=1):
        print(f"  {i}. [{card.signal_level}] {card.headline[:60]}... ({int(card.prediction.probability * 100)}% prob)")
    print(f"  Safely Ignore: {len(daily_issue.not_included_today)} items filtered out")
    print("="*70 + "\n")

    return {
        "status": "success",
        "date": today_str,
        "cards_count": len(daily_issue.cards),
        "ignored_count": len(daily_issue.not_included_today),
        "audio": audio_results
    }


def main():
    parser = argparse.ArgumentParser(description="Pith Autonomous Daily Intelligence Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode without external LLM API calls")
    parser.add_argument("--skip-audio", action="store_true", help="Skip ElevenLabs audio synthesis pass")
    parser.add_argument("--provider", default="auto", choices=["auto", "gemini", "openai", "anthropic", "ollama"], help="LLM Provider")
    parser.add_argument("--model", default=None, help="Specific LLM model identifier")
    parser.add_argument("--db", default="brief.sqlite3", help="Path to SQLite database")
    parser.add_argument("--output", default="public", help="Output directory for generated static assets")

    args = parser.parse_args()

    # Determine if dry_run should be enabled automatically if no LLM keys present
    has_llm_key = any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"))
    dry_run = args.dry_run or (not has_llm_key and args.provider == "auto")

    run_daily_pipeline(
        dry_run=dry_run,
        skip_audio=args.skip_audio,
        provider=args.provider,
        model=args.model,
        db_path=args.db,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
