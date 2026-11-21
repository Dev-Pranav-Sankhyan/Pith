"""
Extended Webpage Renderers for Pith Daily Tech Intelligence.
Generates:
1. horizon.html  - The Prediction Horizon Radar (Interactive Future Timeline 2025-2028)
2. matrix.html   - The Platform Squeeze & Moat Matrix (2x2 Market Power Map)
3. economics.html - Inference Economics & Hardware Reality Calculator
4. terminal.html - Full-Screen Interactive Web Terminal Emulator HUD
5. archive.html  - The Issue Vault (Calendar Heatmap & Searchable History)
6. bounty.html   - The Falsification Desk & Peer-Review Claims Protocol
"""

import os
import json
import datetime
import html as _html
from typing import List, Dict, Any, Optional
from core.models import DailyIssue, Card, Prediction


def escape(text: Any) -> str:
    if text is None:
        return ""
    return _html.escape(str(text))


def get_nav_html(active_page: str) -> str:
    links = [
        ("foryou.html", "For You"),
        ("index.html", "Daily News"),
        ("ledger.html", "Forecast Ledger"),
        ("archive.html", "News Archive"),
        ("patterns.html", "Tech Patterns"),
    ]
    nav_links_html = []
    for href, label in links:
        is_active = (href == active_page)
        active_cls = "nav-link active" if is_active else "nav-link"
        current_attr = ' aria-current="page"' if is_active else ""
        nav_links_html.append(f'<a href="{href}" class="{active_cls}"{current_attr}>{label}</a>')

    return f"""
    <!-- Sticky Crown Header with ELO Rating and Sound Synthesizer -->
    <header class="crown">
        <a href="index.html" class="brand-wrapper">
            <div class="brand-mark" aria-hidden="true">
                <i></i><i></i><i></i><i></i>
            </div>
            <div class="brand-name">PITH</div>
        </a>
        <div class="nav-cluster">
            <nav class="nav-pills-bar">
                {"".join(nav_links_html)}
            </nav>
            <div class="elo-badge" id="elo-badge" title="Forecasting Calibration ELO (starts at 1200 · Beat the Brief)">
                <span class="elo-icon">◈</span>
                <span class="elo-score" id="user-elo-score">1200</span>
                <span class="elo-tier" id="user-elo-tier">Observer</span>
            </div>
            <button class="sound-toggle" id="sound-toggle-btn" title="Toggle tactile audio feedback" type="button">
                <span class="sound-wave-icon" aria-hidden="true">
                    <i></i><i></i><i></i>
                </span>
                <span class="sound-label">Audio: On</span>
            </button>
            <button class="theme-toggle" id="theme-toggle-btn" title="Toggle theme" type="button">
                <div class="theme-icon-circle"></div>
            </button>
        </div>
    </header>
    """


def get_ambient_bg_html() -> str:
    return """
    <!-- Particle Ember FX Canvas for Dynamic Animations -->
    <canvas id="fx-canvas" class="fx-canvas" aria-hidden="true"></canvas>

    <!-- Atmospheric Cybernetic Background Elements -->
    <div class="ambient-orb ambient-orb--red" aria-hidden="true"></div>
    <div class="ambient-orb ambient-orb--gilt" aria-hidden="true"></div>
    <div class="ambient-orb ambient-orb--teal" aria-hidden="true"></div>
    <div class="scan-line" aria-hidden="true"></div>
    <div class="grain-overlay" aria-hidden="true"></div>
    """


def get_footer_html() -> str:
    return """
        <footer class="colophon">
            <div><strong>Pith</strong> &middot; Daily High-Signal Technology Intelligence &amp; Architectural Shifts</div>
            <div style="font-size:12px; margin-top:4px;">Primary-sourced &bull; Public calibration ledger &bull; No sponsored content or noise</div>
            <div class="footer-nav">
                <a href="foryou.html">For You</a>
                <a href="index.html">Daily News</a>
                <a href="ledger.html">Forecast Ledger</a>
                <a href="archive.html">News Archive</a>
                <a href="patterns.html">Tech Patterns</a>
            </div>
        </footer>
    """


# ==============================================================================
# 1. HORIZON.HTML - PREDICTION HORIZON RADAR
# ==============================================================================
def render_horizon(predictions: List[Prediction], latest_issue: DailyIssue, path: str):
    # Horizon page removed per user specification
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 2. MATRIX.HTML - THE PLATFORM SQUEEZE & MOAT MATRIX (REMOVED)
# ==============================================================================
def render_matrix(cards: List[Card], path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 3. ECONOMICS.HTML - INFERENCE MATH & HARDWARE REALITY CALCULATOR (REMOVED)
# ==============================================================================
def render_economics(cards: List[Card], path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 4. TERMINAL.HTML - FULL-SCREEN HACKER WEB TERMINAL (REMOVED)
# ==============================================================================
def render_terminal(latest_issue: DailyIssue, path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 5. ARCHIVE.HTML - THE ISSUE VAULT
# ==============================================================================
def render_archive(all_issues: List[DailyIssue], path: str):
    issues_html = []
    total_cards = sum(len(iss.cards) for iss in all_issues)

    for issue in all_issues:
        cards_summary = []
        for card in issue.cards:
            cards_summary.append(f"""
            <div class="archive-card-row">
                <span class="archive-signal-badge {card.signal_level.lower()}">{card.signal_level} ({card.signal_score:.1f})</span>
                <span class="archive-card-headline"><a href="index.html#{escape(card.id)}">{escape(card.headline)}</a></span>
                <span class="archive-prob-tag">{int((card.prediction.probability if card.prediction else 0.70) * 100)}% prob</span>
            </div>
            """)

        issues_html.append(f"""
        <article class="archive-issue-block lab-card" id="issue-{issue.date}">
            <div class="archive-issue-header">
                <div>
                    <span class="archive-date-title">{issue.date}</span>
                    <span class="archive-beat-tag">&middot; {escape(issue.beat)}</span>
                </div>
                <div class="archive-issue-meta">
                    <span>{len(issue.cards)} shifts grounded</span>
                    <span>&bull;</span>
                    <span>{len(issue.not_included_today)} filtered</span>
                </div>
            </div>
            <div class="archive-cards-list">
                {"".join(cards_summary)}
            </div>
        </article>
        """)

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Archive &middot; Pith</title>
    <meta name="description" content="Searchable historical archive of daily technology intelligence briefs, grounded shifts, and dated predictions.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    {get_ambient_bg_html()}
    {get_nav_html("archive.html")}

    <div class="desk-container">
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> HISTORICAL RECORD &middot; SEARCHABLE INTELLIGENCE ARCHIVE</div>
                <h1 class="page-title">News <em>Archive</em></h1>
                <p style="font-size:15px; color:var(--muted); max-width:680px; margin-top:8px; line-height:1.5;">Searchable historical catalog of daily technology shifts, verified claims, and dated falsifiable predictions across past issues.</p>
            </div>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> {len(all_issues)} ISSUES ARCHIVED</span>
                <span>&middot;</span>
                <span>{total_cards} STRUCTURAL SHIFTS</span>
                <span>&middot;</span>
                <span>IMMUTABLE HISTORY</span>
            </div>
        </section>

        <!-- Fast Client-side Search Bar -->
        <section class="archive-search-section">
            <div class="search-input-wrapper">
                <span class="search-icon">⌕</span>
                <input type="text" id="archive-search-input" placeholder="Search archive by keyword, company, standard (e.g. DeepSeek, FP8, PyTorch, lock-in)..." autocomplete="off">
                <button class="search-clear-btn" id="search-clear-btn" type="button" style="display:none;">&times;</button>
            </div>
        </section>

        <!-- Calendar Heatmap Grid -->
        <section class="heatmap-section lab-card">
            <div class="heatmap-header">
                <span>Intelligence Publishing Heatmap &middot; 2026</span>
                <span style="font-size:11px; color:var(--muted);">Darker hue indicates higher signal density</span>
            </div>
            <div class="heatmap-grid" id="heatmap-grid">
                <!-- 52 weeks x 7 days squares -->
                {"".join([f'<div class="heatmap-day active" title="{iss.date}: {len(iss.cards)} shifts"></div>' for iss in all_issues])}
                {"".join(['<div class="heatmap-day"></div>' for _ in range(40)])}
            </div>
        </section>

        <!-- Past Issues Flow -->
        <main class="archive-flow" id="archive-flow">
            {"".join(issues_html)}
        </main>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ==============================================================================
# 6. BOUNTY.HTML - FALSIFICATION DESK & PEER-REVIEW PROTOCOL
# ==============================================================================
def render_bounty(all_claims: List[Dict[str, Any]], predictions: List[Prediction], path: str):
    # Bounty page removed per user specification
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
