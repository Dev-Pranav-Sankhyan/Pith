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
        ("about.html", "About"),
    ]
    nav_links_html = []
    for href, label in links:
        is_active = (href == active_page)
        active_cls = "nav-link active" if is_active else "nav-link"
        current_attr = ' aria-current="page"' if is_active else ""
        nav_links_html.append(f'<a href="{href}" class="{active_cls}"{current_attr}>{label}</a>')

    return f"""
    <!-- Sticky Crown Header with ELO Rating, User Chip, and Audio Synthesizer -->
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
            <div class="crown-user-chip" id="crown-user-chip" style="display:none;" title="Authenticated Member Session">
                <span class="crown-avatar" id="crown-avatar">?</span>
                <span class="crown-username" id="crown-username"></span>
                <button type="button" class="crown-logout-btn" id="crown-logout-btn" title="Sign out of station">Sign out</button>
            </div>
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
                <a href="about.html">About Pith</a>
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
# 6. BOUNTY.HTML - FALSIFICATION DESK & PEER-REVIEW PROTOCOL (REMOVED)
# ==============================================================================
def render_bounty(all_claims: List[Dict[str, Any]], predictions: List[Prediction], path: str):
    # Bounty page removed per user specification
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ==============================================================================
# 7. ABOUT.HTML - OUR STORY, MANIFESTO & ACCESS TERMINAL
# ==============================================================================
def render_about(path: str):
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About Pith &middot; Anti-Hype Technology Intelligence &amp; Access Gate</title>
    <meta name="description" content="Why Pith exists: The antidote to technology noise, speculative AI hype, and corporate PR. 5 grounded shifts daily with verifiable forecasts.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css">
</head>
<body class="about-page">
    {get_ambient_bg_html()}
    {get_nav_html("about.html")}

    <div class="desk-container">
        <!-- Masthead -->
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> PITH INTELLIGENCE DESK &middot; OUR PHILOSOPHY &amp; ACCESS GATE</div>
                <h1 class="page-title">The Antidote to <em>Tech Noise</em>.</h1>
                <p style="font-size:16px; color:var(--muted); max-width:720px; margin-top:10px; line-height:1.6;">Pith is an independent technological intelligence desk engineered for software engineers, engineering leaders, and founders. We eliminate algorithmic clickbait, speculative PR, and corporate hype cycles by mathematically distilling global tech down to <strong>exactly five grounded architectural and economic shifts</strong> every morning.</p>
            </div>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> NOISE LOWPASS ACTIVE</span>
                <span>&middot;</span>
                <span>5 GROUNDED SHIFTS DAILY</span>
                <span>&middot;</span>
                <span>VERIFIED PRIMARY SOURCES</span>
            </div>
        </section>

        <!-- Access Gate & Portal Section -->
        <section class="access-portal-section">
            <div class="access-portal-grid">
                <!-- Left: Terminal Authentication Card -->
                <div class="access-portal-card lab-card" id="access-auth-card">
                    <div class="portal-card-header">
                        <span class="portal-badge"><i class="radar-dot"></i> STATION ACCESS GATE</span>
                        <h2 class="portal-title">Enter Pith Intelligence Station</h2>
                        <p class="portal-sub">Access to Pith's daily grounded shifts, calibration ledger, and personalized intelligence requires an active member session.</p>
                    </div>

                    <!-- Already Authenticated Banner (Shown when user is logged in) -->
                    <div class="auth-logged-in-box" id="auth-logged-in-box" style="display:none;">
                        <div class="logged-in-icon">✓</div>
                        <div class="logged-in-title">Authenticated Session Active</div>
                        <div class="logged-in-sub">You are currently signed in as <strong id="logged-in-username-label" style="color:var(--gilt);">Member</strong>.</div>
                        <div class="logged-in-actions">
                            <a href="index.html" class="portal-submit-btn enter-station-btn">Enter Daily News Station &rarr;</a>
                            <button type="button" class="portal-demo-btn" id="portal-signout-btn">Sign Out of Station</button>
                        </div>
                    </div>

                    <!-- Auth Forms Container (Shown when logged out) -->
                    <div class="auth-forms-wrap" id="auth-forms-wrap">
                        <div class="auth-tabs-bar">
                            <button type="button" class="auth-tab-btn active" id="tab-btn-login" data-tab="login">Sign In</button>
                            <button type="button" class="auth-tab-btn" id="tab-btn-signup" data-tab="signup">Create Account</button>
                        </div>

                        <!-- Feedback Alert Box -->
                        <div class="auth-alert-box" id="auth-alert-box" style="display:none;"></div>

                        <!-- Sign In Form -->
                        <form class="auth-form" id="about-login-form">
                            <div class="form-field-group">
                                <label for="login-username">Station Username</label>
                                <input type="text" id="login-username" name="username" placeholder="e.g. dev_analyst" required autocomplete="username" autofocus spellcheck="false">
                            </div>
                            <div class="form-field-group">
                                <label for="login-password">Password</label>
                                <input type="password" id="login-password" name="password" placeholder="••••••••••••" required autocomplete="current-password">
                            </div>
                            <button type="submit" class="portal-submit-btn" id="login-submit-btn">
                                <span class="btn-text">Authenticate &amp; Enter Station &rarr;</span>
                            </button>
                            <div class="auth-divider"><span>OR</span></div>
                            <button type="button" class="portal-demo-btn" id="demo-login-btn" title="Sign in with instant guest access">
                                ⚡ Instant 1-Click Guest Pass
                            </button>
                        </form>

                        <!-- Create Account Form (Hidden by default) -->
                        <form class="auth-form" id="about-signup-form" style="display:none;">
                            <div class="form-field-group">
                                <label for="signup-username">Desired Username</label>
                                <input type="text" id="signup-username" name="username" placeholder="3-32 characters (letters, numbers, _ -)" required autocomplete="username" spellcheck="false">
                            </div>
                            <div class="form-field-group">
                                <label for="signup-displayname">Display Name (Optional)</label>
                                <input type="text" id="signup-displayname" name="display_name" placeholder="e.g. Alex Chen" autocomplete="name">
                            </div>
                            <div class="form-field-group">
                                <label for="signup-password">Password</label>
                                <input type="password" id="signup-password" name="password" placeholder="At least 6 characters" required autocomplete="new-password">
                            </div>
                            <button type="submit" class="portal-submit-btn" id="signup-submit-btn">
                                <span class="btn-text">Create Account &amp; Unlock Access &rarr;</span>
                            </button>
                        </form>
                    </div>
                </div>

                <!-- Right: Why Gated & Membership Privileges -->
                <div class="access-info-col">
                    <div class="access-privilege-card lab-card">
                        <div class="privilege-eyebrow">✦ WHY WE GATE ACCESS</div>
                        <h3 class="privilege-title">A News Product That Respects Your Mind</h3>
                        <p class="privilege-p">Modern tech publications monetize outrage, infinite scrolling, and sponsor placements. Pith operates on the inverse thesis: news that protects your focus and proves it was right.</p>
                        
                        <div class="privileges-list">
                            <div class="privilege-item">
                                <div class="priv-icon">◈</div>
                                <div>
                                    <strong>Personalized Calibration ELO</strong>
                                    <p>Participate in "Beat the Brief" forecasting. Your calibration track record is cryptographically logged with mathematical Brier scoring.</p>
                                </div>
                            </div>
                            <div class="privilege-item">
                                <div class="priv-icon">✦</div>
                                <div>
                                    <strong>Zero Algorithmic Clickbait</strong>
                                    <p>We log reading dwell-time exclusively to tailor high-signal shifts—never to sell your attention or serve programmatic ads.</p>
                                </div>
                            </div>
                            <div class="privilege-item">
                                <div class="priv-icon">⚡</div>
                                <div>
                                    <strong>Multi-Lens Technical Directives</strong>
                                    <p>Concrete, grounded actions tailored specifically across Developer, Founder, and Investor viewpoints.</p>
                                </div>
                            </div>
                            <div class="privilege-item">
                                <div class="priv-icon">✓</div>
                                <div>
                                    <strong>Noise Vaporizer Access</strong>
                                    <p>Every morning, inspect our signature "Safely Ignore Today" sheet vaporizing the 8 trending distractions of the day.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- The 4 Core Tenets / Manifesto -->
        <section class="manifesto-section">
            <div class="manifesto-header">
                <div class="eyebrow"><span class="gilt-dot"></span> OUR ARCHITECTURAL MANIFESTO</div>
                <h2 class="section-title">The Four Tenets of Pith</h2>
            </div>

            <div class="pillars-grid">
                <div class="pillar-card lab-card">
                    <div class="pillar-num">01</div>
                    <h3 class="pillar-title">Strict 5-Story Daily Cap</h3>
                    <p class="pillar-desc">If everything is important, nothing is. Every day our pipeline processes thousands of primary announcements, benchmark papers, and code commits. We discard 99.8% of noise to deliver exactly five shifts that actually alter systems or moats.</p>
                </div>

                <div class="pillar-card lab-card">
                    <div class="pillar-num">02</div>
                    <h3 class="pillar-title">Mathematical Falsifiability</h3>
                    <p class="pillar-desc">Opinions are cheap; calibration is earned. Every single story published on Pith includes an explicit, dated prediction with verifiable resolution criteria. Our public Brier score measures exactly how calibrated we are over time.</p>
                </div>

                <div class="pillar-card lab-card">
                    <div class="pillar-num">03</div>
                    <h3 class="pillar-title">The Anti-FOMO Lowpass Filter</h3>
                    <p class="pillar-desc">Half of productivity is knowing what NOT to worry about. Pith provides the "Safely Ignore Today" filter sheet explaining why trending Hacker News or TechCrunch drama won't break your production systems or dilute your competitive moat.</p>
                </div>

                <div class="pillar-card lab-card">
                    <div class="pillar-num">04</div>
                    <h3 class="pillar-title">Multi-Role Translation</h3>
                    <p class="pillar-desc">A shift in KV-cache eviction latency means one thing to a systems engineer, another to a founder budgeting GPU reservations, and another to an investor pricing software defensibility. Pith maps each event across four operational lenses.</p>
                </div>
            </div>
        </section>

        <!-- The Verification Engine Flow -->
        <section class="methodology-section lab-card">
            <div class="methodology-title">How Pith Audits Ground Truth</div>
            <div class="methodology-steps-row">
                <div class="method-step">
                    <span class="method-step-num">Step 1</span>
                    <strong>Primary Source Ingestion</strong>
                    <p>Direct ingest from arXiv papers, Git release tags, regulatory filings, and cloud provider price sheets.</p>
                </div>
                <div class="method-step-arrow">&rarr;</div>
                <div class="method-step">
                    <span class="method-step-num">Step 2</span>
                    <strong>6-Factor Signal Scoring</strong>
                    <p>Scoring breadth of impact, lock-in disruption, irreversibility, source corroboration, and time sensitivity.</p>
                </div>
                <div class="method-step-arrow">&rarr;</div>
                <div class="method-step">
                    <span class="method-step-num">Step 3</span>
                    <strong>Quoted-Span Audit</strong>
                    <p>Every factual claim must match verbatim quoted evidence spans before passing the editorial barrier.</p>
                </div>
                <div class="method-step-arrow">&rarr;</div>
                <div class="method-step">
                    <span class="method-step-num">Step 4</span>
                    <strong>Studio Audio &amp; Video</strong>
                    <p>Synthesis into 90-second studio audio (Nicole voice) and Whisper-aligned vertical video briefs.</p>
                </div>
            </div>
        </section>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

