"""
HTML Static Site Generator for Pith.
Styled according to the 'Working Memory Lab' aesthetic:
silvered ground · blued-steel ink · lacquer red · gilt hairlines.
Includes Daily Brief, Public Prediction Ledger, and Pattern Library.
"""

import json
import html
import os
import datetime
from core.db import Database
from core.ledger import LedgerEngine
from core.patterns_data import PATTERNS
from core.schematics import get_card_schematic
from core.models import Prediction
from core.ledger import LedgerEngine
from pipeline.render_extended import (
    render_horizon,
    render_matrix,
    render_economics,
    render_terminal,
    render_archive,
    render_bounty,
    render_about,
    get_nav_html,
    get_footer_html,
    get_ambient_bg_html,
    get_head_assets
)


def escape(text: str) -> str:
    return html.escape(text or "")


def get_kill_tag_and_period(headline: str, reason: str):
    h = (headline + " " + reason).lower()
    if "benchmark" in h or "synthetic" in h:
        return "BENCHMARK CHERRY-PICKING", "Safe to ignore: 6 months"
    elif "reorganization" in h or "button" in h or "ui" in h or "cosmetic" in h:
        return "HN NOISE & COSMETIC", "Safe to ignore: Indefinitely"
    elif "consumer" in h or "avatar" in h or "chatbot" in h:
        return "PR WITHOUT PRODUCT", "Safe to ignore: 12 months"
    return "BELOW SIGNAL THRESHOLD", "Safe to ignore: Current quarter"


DEEP_CONTEXTS = {
    "card-20261119-cache-cut": {
        "mechanism": "KV-cache eviction offloads inactive session states from GPU High Bandwidth Memory (HBM3e) to host memory without recomputing O(N²) attention matrices. Static prefix hashing triggers instantaneous cache hits.",
        "economics": "Drops input token processing costs from $2.50/M to $0.25/M tokens. Blended gross margin for conversational agent products expands from ~42% to 78% at steady-state cache hit ratios above 80%.",
        "lockin": "Prompt structure becomes platform-dependent. Migrating prompts between providers disrupts prefix hashing boundaries, inducing an estimated 15-25% latency and cost penalty during transition."
    },
    "card-20261119-computer-use": {
        "mechanism": "Vision-language grounding executes continuous OS input event loops: screenshot capture, coordinate prediction, synthetic mouse click, and keyboard keystrokes via platform accessibility APIs.",
        "economics": "Eliminates need for custom enterprise RPA maintenance contracts ($40k-$120k/yr). Action loop latency currently sits at ~2.4 seconds per step, pricing out high-frequency trading but unlocking back-office operations.",
        "lockin": "Shifts lock-in from proprietary API connectors to the cognitive agent runtime. Platforms providing sandboxed, low-latency virtualized environments capture enterprise deployment workflows."
    },
    "card-20261119-oap": {
        "mechanism": "Standardizes bidirectional JSON-RPC schemas over WebSockets and SSE for tool discovery, parameter validation, and client-side sandboxing, decoupling tool definitions from vendor SDKs.",
        "economics": "Reduces marginal cost of adding external data connectors to zero. Shifts enterprise developer spend away from middleware routing gateways to authenticated execution engines.",
        "lockin": "Eats proprietary tool ecosystems. Proprietary walled gardens lose pricing power, forcing model providers to compete on raw reasoning latency and price-per-token."
    },
    "card-20261119-deepseek-mla": {
        "mechanism": "Multi-Head Latent Attention compresses Key-Value tensors into a shared low-rank latent vector (down from 128KB to 16KB per token), dramatically cutting memory bandwidth pressure during generation.",
        "economics": "Enables 3x higher concurrent batch sizes per 8xH100 node. Lowers capital expenditure requirement for open-weights self-hosting by 60% compared to standard MHA models.",
        "lockin": "Challenges CUDA ecosystem hegemony. Decouples frontier inference throughput from raw HBM memory capacity, enabling cheaper deployment across alternate hardware accelerators."
    },
    "card-20261119-llama4": {
        "mechanism": "Meta cluster architecture trains 400B+ parameter models on a unified 100k+ liquid-cooled GPU cluster with automated network fault recovery and FP8 pipeline parallelisms.",
        "economics": "Zero-cost open foundation weights commoditize proprietary baseline models. Shifts enterprise budget toward fine-tuning, domain adaptation, and on-premise privacy.",
        "lockin": "Creates de facto open industry baseline. Enterprises standardize internal tooling on Llama architecture, making proprietary closed APIs a hard sell for standard tasks."
    }
}


def get_deep_context(card_id: str) -> dict:
    return DEEP_CONTEXTS.get(card_id, {
        "mechanism": "Structural architectural shift altering execution pipelines, memory bandwidth, or RPC schemas.",
        "economics": "Directly impacts inference expenditure, SaaS gross margins, and operational compute allocations.",
        "lockin": "Alters switching costs, ecosystem standards, and proprietary vendor leverage."
    })


def get_pattern_for_card(card_id: str):
    for p in PATTERNS:
        if card_id in p.get("related_card_ids", []):
            return p
    return None


def render_all(db_path: str = "brief.sqlite3", output_dir: str = "public"):
    os.makedirs(output_dir, exist_ok=True)
    db = Database(db_path)
    latest_issue = db.get_latest_issue()
    predictions = db.get_all_predictions()
    stats = LedgerEngine.calculate_statistics(predictions)
    all_issues = db.get_all_issues()

    # Clean up deprecated pages per user specification
    for deprecated_file in ("horizon.html", "bounty.html", "matrix.html", "economics.html", "terminal.html"):
        p = os.path.join(output_dir, deprecated_file)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    # Render active core static intelligence pages
    render_index(latest_issue, f"{output_dir}/index.html")
    render_ledger(predictions, stats, f"{output_dir}/ledger.html")
    render_archive(all_issues, f"{output_dir}/archive.html")
    render_patterns(PATTERNS, latest_issue, f"{output_dir}/patterns.html")
    render_about(f"{output_dir}/about.html")
    print("Rendered active static intelligence pages successfully for Pith.")


def render_index(issue, path: str):
    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII"]
    cards_html = []
    
    for idx, card in enumerate(issue.cards):
        roman = roman_numerals[idx] if idx < len(roman_numerals) else f"#{idx+1}"
        dev_view = card.role_views.get("developer")
        pred = card.prediction
        
        role_views_json = escape(json.dumps({
            k: {
                "impact": v.impact,
                "action_type": v.action_type,
                "action_text": v.action_text,
                "stakes": v.stakes
            } for k, v in card.role_views.items()
        }))

        second_order_lis = "".join([f"<li>{escape(so)}</li>" for so in card.second_order])
        evidence_lis = "".join([
            f'<li><a class="evidence-link" href="{escape(el.url)}" target="_blank" rel="noopener">{escape(el.title)}</a> <span class="evidence-publisher">&mdash; {escape(el.publisher)}</span><span class="evidence-quote">&ldquo;{escape(el.quoted_span or "")}&rdquo;</span></li>'
            for el in card.evidence_links
        ])

        analogue_html = ""
        if card.historical_analogue:
            analogue_html = f"""
            <div class="drawer-section">
                <div class="drawer-title">Historical Analogue</div>
                <div class="analogue-card">
                    <div>{escape(card.historical_analogue.analogue)}</div>
                    <div class="analogue-break-text"><strong>Where it breaks:</strong> {escape(card.historical_analogue.where_it_breaks)}</div>
                </div>
            </div>
            """

        roles_comparison_html = """
        <div class="drawer-section">
            <div class="drawer-title">Cross-Role Lens Comparison</div>
            <div class="role-compare-list">
        """
        for r_name, r_view in card.role_views.items():
            roles_comparison_html += f"""
                <div class="role-compare-item">
                    <div class="role-compare-label">{escape(r_name)} <span class="action-pill {escape(r_view.action_type.lower())}">{escape(r_view.action_type)}</span></div>
                    <div class="role-compare-impact">{escape(r_view.impact)}</div>
                    <div class="role-compare-action">&rarr; {escape(r_view.action_text)}</div>
                </div>
            """
        roles_comparison_html += "</div></div>"

        # Pattern link & Deep Context & Schematic
        pattern = get_pattern_for_card(card.id)
        pattern_badge = f'<a href="patterns.html#{pattern["id"]}" class="pattern-pill" title="View historical dynamic & base rates">✦ {escape(pattern["name"])}</a>' if pattern else ""
        deep_ctx = get_deep_context(card.id)
        schematic_html = get_card_schematic(card.id)

        if pred:
            forecast_widget_html = f"""
            <!-- Beat the Brief 1-Tap Calibration Widget with Contrarian Multiplier -->
            <div class="beat-brief-widget" data-card-id="{escape(card.id)}" data-prob="{int(pred.probability * 100)}">
                <!-- Mechanical On-Record Stamp Container (Positioned inside Beat the Brief) -->
                <div class="stamp-container" id="stamp-container-{escape(card.id)}"></div>
                <div class="beat-brief-header">
                    <div>
                        <span class="beat-brief-title">✦ Beat the Brief:</span>
                        <span class="beat-brief-subtitle">Do you think true probability is higher or lower?</span>
                    </div>
                    <span class="contrarian-tag" id="contrarian-tag-{escape(card.id)}" style="display:none;">⚡ 2x Contrarian Multiplier Active</span>
                </div>
                <div class="beat-brief-actions">
                    <button class="vote-btn" data-vote="higher" type="button">▲ Higher</button>
                    <button class="vote-btn" data-vote="agree" type="button">● Agree ({int(pred.probability * 100)}%)</button>
                    <button class="vote-btn" data-vote="lower" type="button">▼ Lower</button>
                </div>
                <div class="crowd-result" style="display:none;">
                    <div class="crowd-bar-track" hidden>
                        <div class="crowd-bar-fill higher" style="width:0%;"></div>
                        <div class="crowd-bar-fill agree" style="width:0%;"></div>
                        <div class="crowd-bar-fill lower" style="width:0%;"></div>
                    </div>
                    <div class="crowd-meta-line">
                        <span class="crowd-summary">Your call is on record.</span>
                        <span class="user-vote-tag">Your pick: <strong class="user-vote-text"></strong></span>
                    </div>
                </div>
            </div>

"""
            forecast_line_html = f"""
                <div class="headline-forecast" title="Pith's falsifiable forecast for this story">
                    <span class="forecast-badge" aria-label="Forecast probability">{int(pred.probability * 100)}%</span>
                    <span class="prediction-text">{escape(pred.statement)}</span>
                    <span class="resolves-badge">Resolves {escape(pred.resolves_at)}</span>
                </div>"""
            criteria_html = f"""
                <div class="drawer-section">
                    <div class="drawer-title">Falsifiable Resolution Criteria</div>
                    <div class="criteria-box">
                        {escape(pred.resolution_criteria)}
                    </div>
                </div>"""
        else:
            forecast_widget_html = ""
            forecast_line_html = '<div class="headline-forecast headline-forecast--none">No forecast was recorded for this story.</div>'
            criteria_html = ""

        cards_html.append(f"""
        <article class="lab-card news-story-card is-collapsed" id="{escape(card.id)}" data-role-views='{role_views_json}'>
            <div class="card-headline-trigger" role="button" tabindex="0" aria-expanded="false" title="Click headline to view details">
                <div class="card-header-line">
                    <span class="card-roman"><span class="card-num">{roman}</span><span class="card-beat">{escape(card.beat)}</span></span>
                    <div class="card-header-meta">
                        {pattern_badge}
                        <span class="card-sources-count">{len(card.evidence_links)} primary source{"" if len(card.evidence_links) == 1 else "s"}</span>
                    </div>
                </div>

                <div class="headline-flex-row">
                    <h2 class="card-headline">{escape(card.headline)}</h2>
                    <span class="headline-expand-badge" aria-hidden="true">
                        <span class="expand-badge-icon">+</span>
                        <span class="expand-badge-text">Details</span>
                    </span>
                </div>
                {forecast_line_html}
            </div>

            <div class="card-details-drawer">
                <div class="story-block">
                    <span class="story-lead">What Happened:</span>
                    <span>{escape(card.what_happened)}</span>
                </div>

            <div class="story-block">
                <span class="story-lead">Why It Matters:</span>
                <span>{escape(card.why_it_matters)}</span>
            </div>

            <!-- Dynamic Role Action Instrument with Split-Flap Typography and Border Glow -->
            <div class="action-panel action-{dev_view.action_type.lower() if dev_view else 'do'} dev-glow">
                <div class="action-panel-top">
                    <span class="action-pill {dev_view.action_type.lower() if dev_view else 'do'}">{dev_view.action_type if dev_view else 'DO'}</span>
                    <span class="action-panel-label">Action this week</span>
                </div>
                <div class="role-impact-preview">{escape(dev_view.impact if dev_view else '')}</div>
                <div class="action-directive">{escape(dev_view.action_text if dev_view else card.action_text)}</div>
            </div>

            <!-- Gauge and Prediction Row -->
            <div class="card-gauge-row">
                <div class="gauge-item">
                    <span>Signal:</span>
                    <span class="badge-tag {card.signal_level.lower()}">{escape(card.signal_level)}</span>
                    <span class="gauge-note">{escape(card.signal_reason)}</span>
                </div>
                <div class="gauge-item">
                    <span>Confidence:</span> <strong>{escape(card.confidence)}</strong>
                </div>
            </div>

{forecast_widget_html}
            <!-- Action Toolbar: Deep Scan, Share to Slack, & Worth My Time Satisfaction Signal -->
            <div class="card-action-bar">
                <button class="deep-scan-btn" type="button">
                    <span class="deep-scan-label">Detailed Intelligence Scan</span>
                    <span class="deep-scan-action-wrap">
                        <span class="deep-scan-text">Expand 5-min deep scan</span>
                        <span class="deep-scan-chevron">▼</span>
                    </span>
                </button>
                <button class="worth-time-btn" type="button" title="Rate this shift as worth your time" data-card-id="{escape(card.id)}">
                    <span class="worth-time-star">✦</span>
                    <span class="worth-time-text">Worth my time</span>
                </button>
                <button class="slack-share-btn" type="button" title="Copy 4-line summary tailored for Slack" data-card-id="{escape(card.id)}">
                    <span class="slack-hash">#</span>
                    <span class="slack-btn-text">Share to Slack</span>
                </button>
            </div>
            <div class="deep-scan-panel">
                <div class="drawer-section">
                    <div class="drawer-title">System Architecture Schematic &amp; Execution Topology</div>
                    {schematic_html}
                </div>

                <div class="drawer-section">
                    <div class="drawer-title">Technical Architecture &amp; Unit Economics Breakdown</div>
                    <div class="deep-context-box">
                        <div class="context-grid">
                            <div class="context-item">
                                <span class="context-item-tag">Architectural Mechanism</span>
                                <p class="context-item-desc">{escape(deep_ctx["mechanism"])}</p>
                            </div>
                            <div class="context-item">
                                <span class="context-item-tag">Unit Economics Shift</span>
                                <p class="context-item-desc">{escape(deep_ctx["economics"])}</p>
                            </div>
                            <div class="context-item">
                                <span class="context-item-tag">Defensibility &amp; Lock-in Vector</span>
                                <p class="context-item-desc">{escape(deep_ctx["lockin"])}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="drawer-section">
                    <div class="drawer-title">Second-Order Consequences</div>
                    <ul class="clean-list">
                        {second_order_lis}
                    </ul>
                </div>

                {analogue_html}

                {criteria_html}

                {roles_comparison_html}

                <div class="drawer-section">
                    <div class="drawer-title">Primary Sources &amp; Quoted Spans</div>
                    <ul class="clean-list">
                        {evidence_lis}
                    </ul>
                </div>
            </div>
            </div>
        </article>
        """)

    # Pool: cards that passed the same threshold and verification as the 5 above. Listing them
    # here publishes their forecasts openly, and signed-in readers get them mixed into Your 5.
    pool_items_html = []
    for pc in getattr(issue, "pool", []) or []:
        link = pc.evidence_links[0] if pc.evidence_links else None
        pred = pc.prediction
        pool_items_html.append(f"""
            <li class="pool-item" id="pool-{escape(pc.id)}">
                <div class="pool-item-meta"><span class="pool-score">{int(pc.signal_score)}</span> signal{f' · <a href="{escape(link.url)}" target="_blank" rel="noopener noreferrer">{escape(link.publisher or "source")}</a>' if link else ""}</div>
                <div class="pool-item-headline">{escape(pc.headline)}</div>
                {f'<div class="pool-item-forecast"><b>{int(round(pred.probability * 100))}%</b> {escape(pred.statement)} <span class="pool-resolves">resolves {escape(pred.resolves_at)}</span></div>' if pred else ""}
            </li>""")
    pool_html = f"""
            <section class="pool-sheet" id="more-shifts" aria-labelledby="more-shifts-title">
                <div class="eyebrow"><span class="gilt-dot"></span> ALSO PASSED THE BAR TODAY</div>
                <h3 class="pool-title" id="more-shifts-title">More verified shifts</h3>
                <p class="pool-sub">These cleared the same signal threshold and quote verification as the five above. Signed-in readers get the ones that fit them mixed into <a href="foryou.html">Your 5</a>.</p>
                <ol class="pool-list">{"".join(pool_items_html)}</ol>
            </section>""" if pool_items_html else ""

    not_included_items_html = []
    for ni in issue.not_included_today:
        tag, period = get_kill_tag_and_period(ni.headline, ni.reason)
        not_included_items_html.append(f"""
        <div class="filtered-item">
            <div class="filtered-header-row">
                <span class="kill-tag">{tag}</span>
                <span class="ignore-period-pill">{period}</span>
            </div>
            <div class="filtered-headline">{escape(ni.headline)}</div>
            <div class="filtered-reason">&mdash; {escape(ni.reason)}</div>
        </div>
        """)

    issue_date_formatted = datetime.datetime.strptime(issue.date, "%Y-%m-%d").strftime("%d %B %Y")

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Tech News &middot; Pith &middot; {escape(issue_date_formatted)}</title>
    <meta name="description" content="Pith filters tech news down to 5 falsifiable events that alter architectures, unit economics, or platform moats.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    {get_head_assets()}
    <link rel="stylesheet" href="style.css">
</head>
<body class="page-brief">
    {get_ambient_bg_html()}

    {get_nav_html("index.html")}

    <div class="desk-container">
        <!-- Masthead -->
        <section class="masthead">
            <div class="eyebrow"><span class="gilt-dot"></span> DAILY TECH INTELLIGENCE &middot; {escape(issue.beat)}</div>
            <h1 class="page-title">Daily <em>Tech News</em></h1>
            <p class="masthead-dek">Today's 5 grounded architectural and market power shifts. Filtered down to events that alter software architectures, unit economics, or competitive moats.</p>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> AUDITED</span>
                <span class="meta-sep">&middot;</span>
                <span>{escape(issue_date_formatted)}</span>
                <span class="meta-sep">&middot;</span>
                <span>ISSUE #01</span>
            </div>
        </section>

        <section class="brief-controls" aria-label="Listen and choose a lens">
        <!-- 90-Second Studio Audio Briefing Player -->
        <div class="audio-brief-section">
            <div class="audio-brief-bar" id="audio-brief-bar">
                <div class="audio-brief-main-row">
                    <div class="audio-brief-play-side">
                        <button class="audio-brief-play-btn" id="audio-brief-play-btn" type="button" aria-label="Play 90-second audio briefing">
                            <span class="audio-play-icon" id="audio-play-icon">▶</span>
                            <span class="audio-pause-icon" id="audio-pause-icon" style="display:none;">❚❚</span>
                        </button>
                        <div class="audio-brief-info">
                            <div class="audio-brief-badge-row">
                                <span class="audio-pulse-indicator" id="audio-pulse-indicator"></span>
                                <span class="audio-brief-title">90s Spoken Briefing</span>
                                <span class="audio-role-pill" id="audio-role-pill">DEVELOPER</span>
                                <div class="audio-eq-waves" id="audio-eq-waves" aria-hidden="true">
                                    <span></span><span></span><span></span><span></span>
                                </div>
                            </div>
                            <div class="audio-brief-sub">ElevenLabs Voice (Nicole) &middot; Studio-mastered &middot; Natural breathing &middot; -45dB room tone &middot; -16 LUFS</div>
                        </div>
                    </div>

                    <div class="audio-brief-track-side">
                        <div class="audio-brief-scrubber" id="audio-brief-scrubber" title="Click to seek">
                            <div class="audio-brief-progress" id="audio-brief-progress"></div>
                        </div>
                        <div class="audio-brief-waveform-time-row">
                            <canvas class="audio-waveform-canvas" id="audio-waveform-canvas" width="220" height="20" aria-hidden="true"></canvas>
                            <div class="audio-brief-time-row">
                                <span id="audio-current-time">0:00</span>
                                <span>/</span>
                                <span id="audio-total-time">1:17</span>
                            </div>
                        </div>
                    </div>
                </div>

                <audio id="audio-player" preload="metadata" src="audio/brief-developer.mp3"></audio>
            </div>
        </div>

        <!-- Segmented Role Selector -->
        <div class="role-bar">
            <div class="role-bar-label">Personal Lens</div>
            <div class="seg-control" role="group" aria-label="Personal lens">
                <button class="seg-btn active" data-role="developer" type="button">Developer</button>
                <button class="seg-btn" data-role="founder" type="button">Founder</button>
                <button class="seg-btn" data-role="investor" type="button">Investor</button>
                <button class="seg-btn" data-role="everyday" type="button">Everyday Person</button>
            </div>
        </div>
        </section>

        <!-- Cards Flow -->
        <main class="cards-flow">
            <div class="headlines-toolbar">
                <div class="headlines-toolbar-status">
                    <span class="live-pulse-dot"></span>
                    <span>Daily Filtered Shifts &middot; Click any headline to inspect full briefing</span>
                </div>
                <button class="expand-all-btn" id="toggle-all-headlines-btn" type="button" aria-expanded="false" title="Expand or collapse all intelligence cards">
                    <span class="expand-all-icon">⊞</span>
                    <span class="expand-all-text">Expand All</span>
                </button>
            </div>

            {"".join(cards_html)}

            <!-- "Zero-FOMO" Completion Card -->
            <div class="completion-card" id="completion-card">
                <div class="completion-crest">
                    <span class="completion-check">✓</span>
                </div>
                <h3 class="completion-title">Briefing complete. Go build.</h3>
                <p class="completion-sub">5 high-signal shifts processed. Zero infinite scroll. Zero algorithmic feeds. Next issue tomorrow at 07:00 IST.</p>
                <div class="completion-meta-row">
                    <span class="completion-pill-status"><span class="pulse-emerald"></span> Signal Calibrated</span>
                    <button class="replay-filter-btn" id="replay-lowpass-btn" type="button">↻ Replay Lowpass</button>
                </div>
            </div>
            {pool_html}
        </main>

        <!-- Signature "Safely Ignore Today" Filter-Proof Sheet with Shredder -->
        <section class="filter-sheet" id="safely-ignore">
            <div class="filter-sheet-header">
                <div>
                    <div class="eyebrow"><span class="gilt-dot"></span> NOISE FILTER AT WORK</div>
                    <h3 class="filter-sheet-title">Safely Ignore Today</h3>
                </div>
                <div class="filter-sheet-actions">
                    <button class="shredder-btn" id="shredder-btn" type="button" title="Vaporize today's filtered distractions">
                        <span class="shredder-icon">⚡</span>
                        <span class="shredder-label">Clear the Noise</span>
                    </button>
                    <span class="filter-sheet-pill">Noise Filtered</span>
                </div>
            </div>
            <p class="filter-subtext">You probably saw these trending on Hacker News, X, or TechCrunch. Here is why you can safely ignore them and protect your focus:</p>
            <div class="filtered-items-container" id="filtered-items-container">
                {"".join(not_included_items_html)}
            </div>
            <div class="shredded-quiet-slate" id="shredded-quiet-slate" style="display:none;">
                <div class="quiet-icon">✦</div>
                <div class="quiet-title">Noise obliterated. Focus preserved.</div>
                <div class="quiet-desc">All 8 low-signal distraction stories vaporized. Zero FOMO. Go back to deep work.</div>
                <button class="restore-noise-btn" id="restore-noise-btn" type="button">Undo shredder</button>
            </div>
        </section>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _pct(h: dict) -> str:
    v = h.get("hit_rate_pct")
    return f"{v}% Hit" if v is not None else "No data"


def render_ledger(predictions, stats, path: str):
    rows_html = []
    for p in predictions:
        status_cls = p.status.lower()
        horizon = LedgerEngine.get_horizon(p)
        postmortem_html = f'<div class="ledger-postmortem"><strong>Post-mortem:</strong> {escape(p.postmortem)}</div>' if p.postmortem else ""
        evidence_html = f'<a class="ledger-evidence" href="{escape(p.evidence_url)}" target="_blank" rel="noopener">Evidence &rarr;</a>' if p.evidence_url else '<span class="cell-empty">&mdash;</span>'

        is_live = LedgerEngine.is_live(p)
        prov_html = "" if is_live else '<span class="badge-tag low prov-tag" title="Hand-written example. Not counted in any score.">Illustrative</span>'
        rows_html.append(f"""
        <tr data-status="{escape(p.status)}" data-category="{escape(p.category)}" data-horizon="{escape(horizon)}" data-provenance="{escape(p.provenance)}"{'' if is_live else ' class="is-illustrative"'}>
            <td class="cell-mono">{escape(p.made_at)}</td>
            <td class="cell-statement">
                <div class="ledger-statement">{prov_html}{escape(p.statement)}</div>
                <div class="ledger-criteria">
                    <em>Resolution standard:</em> {escape(p.resolution_criteria)}
                </div>
                {postmortem_html}
            </td>
            <td><span class="horizon-tag">{escape(horizon)}</span></td>
            <td><span class="category-tag">{escape(p.category)}</span></td>
            <td class="cell-prob">{int(p.probability * 100)}%</td>
            <td><span class="status-pill {status_cls}">{escape(p.status)}</span></td>
            <td class="cell-mono">{escape(p.resolves_at)}</td>
            <td>{evidence_html}</td>
        </tr>
        """)

    calibration_rows = []
    for b in stats["calibration"]:
        actual_str = f"{b['actual_rate']}%" if b['actual_rate'] is not None else "&mdash;"
        gap_str = f"{b['calibration_gap']:+.1f}%" if b['calibration_gap'] is not None else "&mdash;"
        gap_cls = "" if b['calibration_gap'] is None else ("is-good" if b['calibration_gap'] >= 0 else "is-bad")
        calibration_rows.append(f"""
        <tr>
            <td class="cell-strong">{escape(b['bucket'])}</td>
            <td class="cell-mono">{b['count']}</td>
            <td class="cell-mono">{b['avg_forecast']}%</td>
            <td class="cell-prob">{actual_str}</td>
            <td class="cell-mono cell-gap {gap_cls}">{gap_str}</td>
        </tr>
        """)

    brier_val = f"{stats['brier_score']:.4f}" if stats['brier_score'] is not None else "N/A"
    hit_rate_val = f"{stats['hit_rate_pct']:.1f}%" if stats['hit_rate_pct'] is not None else "N/A"

    brier_target = f' data-target="{stats["brier_score"]:.4f}"' if stats["brier_score"] is not None else ""
    hit_target = f' data-target="{stats["hit_rate_pct"]:.1f}"' if stats["hit_rate_pct"] is not None else ""
    bss = stats.get("brier_skill_score")
    brier_sub = "Benchmark &lt; 0.25 (lower is better)" + (f" &middot; skill vs base rate {bss:+.2f}" if bss is not None else "")
    ill = stats.get("illustrative", {})
    if stats["resolved_count"] == 0:
        record_banner = f"""
        <div class="notice">
            <strong>No live forecast has resolved yet.</strong> Scores appear here only once a prediction Pith actually published reaches its resolution date and a named reviewer records the outcome with evidence.
            {f"The {ill.get('count', 0)} faded rows marked <em>Illustrative</em> below are hand-written examples to preview the layout. They are not counted in any number on this page." if ill.get('count') else ""}
        </div>"""
    elif ill.get("count"):
        record_banner = f"""
        <div class="notice notice--quiet">Scores count live forecasts only. {ill['count']} faded <em>Illustrative</em> rows are examples and are excluded.</div>"""
    else:
        record_banner = ""

    live_wrong = [p for p in predictions if LedgerEngine.is_live(p) and p.status == "wrong"]
    live_wrong.sort(key=lambda p: p.resolved_at or "", reverse=True)
    if live_wrong:
        wrong_cards_html = "".join(f"""
            <div class="wrong-card">
                <div class="wrong-card-top">
                    <span class="status-pill wrong">&#10005; Wrong Call</span>
                    <span class="wrong-card-meta">Forecast: {int(w.probability * 100)}% &middot; Resolved {escape(w.resolved_at or "")}{(" by " + escape(w.resolved_by)) if w.resolved_by else ""}</span>
                </div>
                <div class="wrong-statement">&ldquo;{escape(w.statement)}&rdquo;</div>
                {f'<div class="wrong-postmortem-block"><div class="wrong-postmortem-title">Post-mortem:</div><div class="wrong-postmortem-text">{escape(w.postmortem)}</div>' + (f'<div class="wrong-evidence"><a href="{escape(w.evidence_url)}" target="_blank" rel="noopener" class="wrong-evidence-link">Evidence &rarr;</a></div>' if w.evidence_url else "") + '</div>' if w.postmortem else ""}
            </div>""" for w in live_wrong[:3])
    else:
        wrong_cards_html = '<div class="empty-note">No live forecast has been resolved wrong yet. When one is, it appears here with its original probability and a post-mortem.</div>'

    horizon_stats = stats.get("horizon_breakdown", {})
    h30 = horizon_stats.get("30-day", {})
    h90 = horizon_stats.get("90-day", {})
    h365 = horizon_stats.get("365-day", {})

    def _horizon_card(icon: str, label: str, title: str, h: dict) -> str:
        brier = h.get('brier_score') if h.get('brier_score') is not None else '&mdash;'
        return f"""
            <div class="horizon-card">
                <div class="horizon-card-top">
                    <span class="horizon-label"><span aria-hidden="true">{icon}</span> {label}</span>
                    <span class="status-pill {'correct' if h.get('hit_rate_pct') is not None else 'open'}">{_pct(h)}</span>
                </div>
                <div class="horizon-title">{title}</div>
                <div class="horizon-meta">{h.get('resolved', 0)} resolved &middot; {h.get('open', 0)} active &middot; Brier: {brier}</div>
            </div>"""

    horizon_cards_html = f"""
        <div class="horizon-grid">
            {_horizon_card("⚡", "30-Day Horizon", "Immediate Tooling &amp; SDK Shifts", h30)}
            {_horizon_card("◈", "90-Day Horizon", "Quarterly Architecture Milestones", h90)}
            {_horizon_card("✦", "365-Day Horizon", "Annual Platform &amp; Economic Regimes", h365)}
        </div>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forecast Tracker &middot; Pith</title>
    <meta name="description" content="Public, unedited track record of dated falsifiable predictions, Brier accuracy scores, and calibration statistics for Pith.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    {get_head_assets()}
    <link rel="stylesheet" href="style.css">
</head>
<body class="page-ledger">
    {get_ambient_bg_html()}

    {get_nav_html("ledger.html")}

    <div class="desk-container">
        <section class="masthead">
            <div class="eyebrow"><span class="gilt-dot"></span> AUDIT &middot; PUBLIC TRACK RECORD &middot; ACCURACY LEDGER</div>
            <h1 class="page-title">Forecast <em>Tracker</em></h1>
            <p class="masthead-dek">Public, immutable ledger of all dated falsifiable predictions. Probabilities are locked after the publication day and every verdict is an append-only record with a named reviewer and evidence.</p>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> ON-RECORD</span>
                <span class="meta-sep">&middot;</span>
                <span>IMMUTABLE PROBABILITIES</span>
                <span class="meta-sep">&middot;</span>
                <span>ZERO RETROSPECTIVE EDITS</span>
            </div>
        </section>

        {record_banner}

        <!-- Big Num Grid with Counter Animations -->
        <div class="bignum-grid">
            <div class="bignum-card">
                <div class="bignum{'' if brier_target else ' is-empty'}"{brier_target} data-format="brier">{brier_val}</div>
                <div class="bignum-label">Brier Score</div>
                <div class="bignum-sub">{brier_sub}</div>
            </div>
            <div class="bignum-card">
                <div class="bignum{'' if hit_target else ' is-empty'}"{hit_target} data-format="percent">{hit_rate_val}</div>
                <div class="bignum-label">Hit Rate</div>
                <div class="bignum-sub">{stats['correct_count']} of {stats['resolved_count']} resolved</div>
            </div>
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['resolved_count']}" data-format="int">{stats['resolved_count']}</div>
                <div class="bignum-label">Sample Size</div>
                <div class="bignum-sub">{"Preliminary (need &ge; " + str(stats['min_sample_threshold']) + ")" if stats['is_preliminary'] else "Definitive"}</div>
            </div>
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['open_count']}" data-format="int">{stats['open_count']}</div>
                <div class="bignum-label">Active Forecasts</div>
                <div class="bignum-sub">Under evaluation</div>
            </div>
        </div>

        {horizon_cards_html}

        <!-- Calibration Sheet -->
        <section class="table-sheet">
            <div class="sheet-header-line">
                <h3 class="sheet-title">Forecast Calibration</h3>
                <span class="sheet-note">When we predict X%, are we right X% of the time?</span>
            </div>
            <table class="instrument-table">
                <thead>
                    <tr>
                        <th>Bucket</th>
                        <th>Sample Count</th>
                        <th>Avg Forecast</th>
                        <th>Observed Rate</th>
                        <th>Calibration Gap</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(calibration_rows)}
                </tbody>
            </table>
        </section>

        <!-- "Where We Were Wrong" Radical Transparency Showcase -->
        <section class="wrong-showcase-sheet">
            <div class="wrong-showcase-header">
                <div>
                    <span class="wrong-badge">Radical Transparency</span>
                    <h3 class="wrong-showcase-title">Where We Were Wrong</h3>
                </div>
                <p class="wrong-showcase-sub">
                    Legacy analysts quietly delete failed predictions. We celebrate accountability. When our forecast misses reality, we preserve the original probability and publish a candid post-mortem.
                </p>
            </div>

            {wrong_cards_html}
        </section>

        <!-- Filter Controls -->
        <div class="filter-row">
            <div class="filter-select-wrap">
                <label for="status-filter">Status:</label>
                <select id="status-filter" class="filter-select">
                    <option value="all">All Predictions</option>
                    <option value="open">Open (Active)</option>
                    <option value="correct">Resolved: Correct</option>
                    <option value="wrong">Resolved: Wrong</option>
                    <option value="void">Void</option>
                </select>
            </div>
            <div class="filter-select-wrap">
                <label for="horizon-filter">Horizon:</label>
                <select id="horizon-filter" class="filter-select">
                    <option value="all">All Horizons</option>
                    <option value="30-day">30-Day (Immediate)</option>
                    <option value="90-day">90-Day (Quarterly)</option>
                    <option value="365-day">365-Day (Annual)</option>
                </select>
            </div>
            <div class="filter-select-wrap">
                <label for="category-filter">Category:</label>
                <select id="category-filter" class="filter-select">
                    <option value="all">All Categories</option>
                    <option value="technology">Technology</option>
                    <option value="adoption">Adoption</option>
                    <option value="market">Market</option>
                </select>
            </div>
        </div>

        <!-- Full Ledger Sheet -->
        <section class="table-sheet">
            <table class="instrument-table instrument-table--ledger">
                <thead>
                    <tr>
                        <th>Made</th>
                        <th>Prediction &amp; Resolution Standard</th>
                        <th>Horizon</th>
                        <th>Category</th>
                        <th>Prob</th>
                        <th>Status</th>
                        <th>Resolves</th>
                        <th>Evidence</th>
                    </tr>
                </thead>
                <tbody id="ledger-table-body">
                    {"".join(rows_html)}
                </tbody>
            </table>
        </section>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


def render_patterns(patterns, issue, path: str):
    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII"]
    patterns_html = []

    # Map card IDs to headlines
    card_map = {c.id: c.headline for c in (issue.cards if issue else [])}

    for idx, p in enumerate(patterns):
        roman = roman_numerals[idx] if idx < len(roman_numerals) else f"#{idx+1}"

        # Cases HTML
        cases_html = []
        for case in p["cases"]:
            cases_html.append(f"""
            <div class="case-study-card">
                <div class="case-study-title">{escape(case['title'])}</div>
                <div class="case-study-detail">{escape(case['detail'])}</div>
            </div>
            """)

        # Active Cards matching
        matched_cards = []
        for cid in p.get("related_card_ids", []):
            if cid in card_map:
                matched_cards.append(f'<a href="index.html#{escape(cid)}" class="pattern-active-link">{escape(card_map[cid])} &rarr;</a>')

        active_in_brief_html = ""
        if matched_cards:
            active_in_brief_html = f"""
            <div class="pattern-active-brief">
                <span class="pattern-active-label">Active in Today's Issue:</span>
                {" &middot; ".join(matched_cards)}
            </div>
            """

        patterns_html.append(f"""
        <article class="lab-card pattern-card" id="{escape(p['id'])}" data-category="{escape(p['category'])}">
            <div class="card-header-line">
                <span class="card-roman"><span class="card-num">{roman}</span><span class="card-beat">{escape(p['tag'])}</span></span>
                <span class="card-sources-count">{len(p['cases'])} documented cases</span>
            </div>

            <h2 class="card-headline">{escape(p['name'])}</h2>
            
            <p class="pattern-summary">{escape(p['summary'])}</p>

            <div class="story-block">
                <span class="story-lead">The Core Dynamic:</span>
                <span>{escape(p['dynamics'])}</span>
            </div>

            <!-- Base Rate Box -->
            <div class="base-rate-box">
                <div class="base-rate-header">
                    <span class="base-rate-badge">Historical Base Rate</span>
                </div>
                <div class="base-rate-text">{escape(p['base_rate'])}</div>
            </div>

            <!-- Documented Case Studies -->
            <div class="pattern-cases-section">
                <div class="drawer-title">Documented Historical Precedents</div>
                <div class="pattern-cases-grid">
                    {"".join(cases_html)}
                </div>
            </div>

            <!-- Cognitive Bias & Failure Mode Panel -->
            <div class="bias-warning-panel">
                <div class="bias-warning-title">Cognitive Pitfall to Avoid</div>
                <div class="bias-warning-text">{escape(p['cognitive_bias'])}</div>
                <div class="failure-mode-callout">
                    <strong>Known Failure Mode:</strong> {escape(p['failure_mode'])}
                </div>
            </div>

            {active_in_brief_html}
        </article>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech Patterns &middot; Pith</title>
    <meta name="description" content="Curated catalog of recurring tech dynamics, historical base rates, failure modes, and cognitive bias warnings for Pith.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    {get_head_assets()}
    <link rel="stylesheet" href="style.css">
</head>
<body class="page-patterns">
    {get_ambient_bg_html()}

    {get_nav_html("patterns.html")}

    <div class="desk-container">
        <section class="masthead">
            <div class="eyebrow"><span class="gilt-dot"></span> RECURRING DYNAMICS &middot; HISTORICAL PRECEDENTS &middot; MENTAL MODELS</div>
            <h1 class="page-title">Tech <em>Patterns</em></h1>
            <p class="masthead-dek">Tech shifts appear sudden, but infrastructure history repeats in predictable economic and architectural dynamics. We evaluate candidate events against recurring failure modes, historical base rates, and cognitive bias warnings before drafting predictions.</p>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> CATALOGUED</span>
                <span class="meta-sep">&middot;</span>
                <span>MENTAL MODELS</span>
                <span class="meta-sep">&middot;</span>
                <span>{len(patterns)} ARCHITECTURAL DYNAMICS</span>
            </div>
        </section>

        <!-- Pattern Filter Controls -->
        <section class="role-bar role-bar--filters">
            <div class="role-bar-label">Filter Category</div>
            <div class="seg-control" id="pattern-filters" role="group" aria-label="Filter patterns by category">
                <button class="seg-btn active" data-category="all" type="button">All Patterns</button>
                <button class="seg-btn" data-category="Platform Economics" type="button">Platform Economics</button>
                <button class="seg-btn" data-category="Open Source & Standards" type="button">Open Source &amp; Standards</button>
                <button class="seg-btn" data-category="Architecture & Silicon" type="button">Architecture &amp; Silicon</button>
            </div>
        </section>

        <!-- Patterns Flow -->
        <main class="cards-flow" id="patterns-container">
            {"".join(patterns_html)}
        </main>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    render_all()
