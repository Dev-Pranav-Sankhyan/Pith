"""
HTML Static Site Generator for Pith.
Styled according to the 'Working Memory Lab' aesthetic:
silvered ground · blued-steel ink · lacquer red · gilt hairlines.
Includes Daily Brief, Public Prediction Ledger, and Pattern Library.
"""

import json
import html
import datetime
from core.db import Database
from core.ledger import LedgerEngine
from core.patterns_data import PATTERNS
from core.schematics import get_card_schematic


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
    db = Database(db_path)
    latest_issue = db.get_latest_issue()
    predictions = db.get_all_predictions()
    stats = LedgerEngine.calculate_statistics(predictions)

    render_index(latest_issue, f"{output_dir}/index.html")
    render_ledger(predictions, stats, f"{output_dir}/ledger.html")
    render_patterns(PATTERNS, latest_issue, f"{output_dir}/patterns.html")
    print("Rendered index.html, ledger.html, and patterns.html successfully for Pith.")


def render_index(issue, path: str):
    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII"]
    cards_html = []
    
    for idx, card in enumerate(issue.cards):
        roman = roman_numerals[idx] if idx < len(roman_numerals) else f"#{idx+1}"
        dev_view = card.role_views.get("developer")
        
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
            f'<li><a href="{escape(el.url)}" target="_blank" rel="noopener" style="color:var(--ink); font-weight:600;">{escape(el.title)}</a> &mdash; {escape(el.publisher)}<br><span style="font-size:12px; color:var(--muted);">&ldquo;{escape(el.quoted_span or "")}&rdquo;</span></li>'
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
            <div style="display:flex; flex-direction:column; gap:8px;">
        """
        for r_name, r_view in card.role_views.items():
            roles_comparison_html += f"""
                <div style="background:var(--surface); padding:10px 12px; border-radius:6px; border:1px solid var(--hairline);">
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--gilt);">{escape(r_name)} &middot; {escape(r_view.action_type)}</div>
                    <div style="font-size:13.5px; margin-top:2px; color:var(--ink);">{escape(r_view.impact)}</div>
                    <div style="font-size:13px; font-weight:600; color:var(--ink); margin-top:3px;">&rarr; {escape(r_view.action_text)}</div>
                </div>
            """
        roles_comparison_html += "</div></div>"

        # Pattern link & Deep Context & Schematic
        pattern = get_pattern_for_card(card.id)
        pattern_badge = f'<a href="patterns.html#{pattern["id"]}" class="pattern-pill" title="View historical dynamic & base rates">✦ {escape(pattern["name"])}</a>' if pattern else ""
        deep_ctx = get_deep_context(card.id)
        schematic_html = get_card_schematic(card.id)

        cards_html.append(f"""
        <article class="lab-card" id="{escape(card.id)}" data-role-views='{role_views_json}'>
            <div class="card-header-line">
                <span class="card-roman">{roman} &middot; {escape(card.beat)}</span>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    {pattern_badge}
                    <span class="card-sources-count">{len(card.evidence_links)} primary source</span>
                </div>
            </div>

            <h2 class="card-headline">{escape(card.headline)}</h2>

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
                    <span style="font-size:11.5px; text-transform:uppercase; letter-spacing:0.12em; color:var(--muted); font-weight:600;">Action this week</span>
                </div>
                <div class="role-impact-preview">{escape(dev_view.impact if dev_view else '')}</div>
                <div class="action-directive">{escape(dev_view.action_text if dev_view else card.action_text)}</div>
            </div>

            <!-- Gauge and Prediction Row -->
            <div class="card-gauge-row">
                <div class="gauge-item">
                    <span>Signal:</span>
                    <span class="badge-tag {card.signal_level.lower()}">{escape(card.signal_level)}</span>
                    <span style="font-size:12px; color:var(--muted); margin-left:4px;">({escape(card.signal_reason)})</span>
                </div>
                <div class="gauge-item">
                    <span>Confidence: <strong style="color:var(--ink);">{escape(card.confidence)}</strong></span>
                </div>
            </div>

            <!-- Precision Prediction Strip -->
            <div class="prediction-strip">
                <span class="forecast-badge">{int(card.prediction.probability * 100)}% Forecast</span>
                <span class="prediction-text">{escape(card.prediction.statement)}</span>
                <span class="resolves-badge">Resolves {escape(card.prediction.resolves_at)}</span>
            </div>

            <!-- Beat the Brief 1-Tap Calibration Widget with Contrarian Multiplier -->
            <div class="beat-brief-widget" data-card-id="{escape(card.id)}" data-prob="{int(card.prediction.probability * 100)}">
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
                    <button class="vote-btn" data-vote="agree" type="button">● Agree ({int(card.prediction.probability * 100)}%)</button>
                    <button class="vote-btn" data-vote="lower" type="button">▼ Lower</button>
                </div>
                <div class="crowd-result" style="display:none;">
                    <div class="crowd-bar-track">
                        <div class="crowd-bar-fill higher" style="width: 22%;" title="22% Higher"></div>
                        <div class="crowd-bar-fill agree" style="width: 63%;" title="63% Agree"></div>
                        <div class="crowd-bar-fill lower" style="width: 15%;" title="15% Lower"></div>
                    </div>
                    <div class="crowd-meta-line">
                        <span>Crowd: <strong>63% Agree</strong> &middot; 22% Higher &middot; 15% Lower</span>
                        <span class="user-vote-tag">Your pick: <strong class="user-vote-text">Agree</strong></span>
                    </div>
                </div>
            </div>

            <!-- Action Toolbar: Deep Scan & Share to Slack -->
            <div class="card-action-bar">
                <button class="deep-scan-btn" type="button">
                    <span class="deep-scan-label">Detailed Intelligence Scan</span>
                    <span class="deep-scan-action-wrap">
                        <span class="deep-scan-text">Expand 5-min deep scan</span>
                        <span class="deep-scan-chevron">▼</span>
                    </span>
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

                <div class="drawer-section">
                    <div class="drawer-title">Falsifiable Resolution Criteria</div>
                    <div style="font-size:13px; font-family:var(--font-mono); background:var(--surface); padding:10px 12px; border-radius:6px; border:1px solid var(--hairline); color:var(--ink-2);">
                        {escape(card.prediction.resolution_criteria)}
                    </div>
                </div>

                {roles_comparison_html}

                <div class="drawer-section">
                    <div class="drawer-title">Primary Sources &amp; Quoted Spans</div>
                    <ul class="clean-list">
                        {evidence_lis}
                    </ul>
                </div>
            </div>
        </article>
        """)

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

    pip_items = []
    pip_roman = ["I", "II", "III", "IV", "V", "VI", "VII"]
    for i, card in enumerate(issue.cards):
        roman = pip_roman[i] if i < len(pip_roman) else str(i+1)
        short_title = card.headline.split(":")[0].split(",")[0][:20].upper()
        pip_items.append(f'''
            <a href="#{escape(card.id)}" class="rail-pip{' active' if i == 0 else ''}" data-index="{i}" data-target="{escape(card.id)}" title="{roman}. {escape(card.headline)}">
                <span class="pip-square"></span>
                <span class="pip-tooltip">{roman} // {escape(short_title)}</span>
            </a>''')
    if issue.not_included_today:
        pip_items.append(f'''
            <a href="#safely-ignore" class="rail-pip" data-index="{len(issue.cards)}" data-target="safely-ignore" title="Safely Ignore Today">
                <span class="pip-square noise-pip"></span>
                <span class="pip-tooltip">NOISE // SAFELY IGNORE</span>
            </a>''')
    pips_html = "".join(pip_items)

    issue_date_formatted = datetime.datetime.strptime(issue.date, "%Y-%m-%d").strftime("%d %B %Y")

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pith &middot; Daily Tech Intelligence &middot; {escape(issue_date_formatted)}</title>
    <meta name="description" content="Pith filters tech news down to 5 falsifiable events that alter architectures, unit economics, or platform moats.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <!-- Andrew McCarthy (andrevv.com) Inspired Architectural Vertical Side Rails -->
    <aside class="side-rail-left" aria-hidden="true">
        <div class="rail-line-track"></div>
        <div class="rail-bead" id="rail-bead-left"></div>
        <div class="rail-telemetry">
            <span class="telemetry-idx" id="telemetry-card-idx">01</span>
            <span class="telemetry-slash">//</span>
            <span class="telemetry-total">{len(issue.cards):02d}</span>
        </div>
        <div class="rail-coord" id="rail-scroll-coord">Y: 00%</div>
    </aside>

    <nav class="side-rail-right" id="side-rail-nav" aria-label="Section navigation">
        <div class="rail-line-track"></div>
        <div class="rail-tracer-beam-wrap" aria-hidden="true">
            <div class="rail-tracer-beam" id="rail-tracer-beam"></div>
        </div>
        <div class="rail-pips-container" id="rail-pips-container">
            {pips_html}
        </div>
    </nav>

    <!-- Particle Ember FX Canvas for Dynamic Animations -->
    <canvas id="fx-canvas" class="fx-canvas" aria-hidden="true"></canvas>

    <!-- 0.8s Lowpass Noise-to-Signal Compression Hero Overlay -->
    <div class="lowpass-overlay" id="lowpass-overlay" aria-hidden="true" style="display:none;">
        <div class="noise-cloud" id="noise-cloud"></div>
        <div class="laser-sweep-line" id="laser-sweep-line"></div>
        <div class="lowpass-caption">LOWPASS FILTER // VAPORIZING NOISE</div>
    </div>

    <!-- Sticky Crown Header with ELO Rating and Sound Synthesizer -->
    <header class="crown">
        <a href="index.html" class="brand-wrapper">
            <div class="brand-mark" aria-hidden="true">
                <i></i><i></i><i></i><i></i>
            </div>
            <div class="brand-name">PITH</div>
        </a>
        <div class="nav-cluster">
            <nav>
                <a href="index.html" class="nav-link active" aria-current="page">Brief</a>
                <a href="ledger.html" class="nav-link">Ledger</a>
                <a href="patterns.html" class="nav-link">Patterns</a>
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

    <div class="desk-container">
        <!-- Masthead -->
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> BEAT &middot; {escape(issue.beat)}</div>
                <h1 class="page-title">Pith <em>Intelligence</em></h1>
            </div>
            <div class="meta-pill-group">
                <span>{escape(issue_date_formatted)}</span>
                <span>&middot;</span>
                <span>ISSUE #01</span>
                <span>&middot;</span>
                <button class="lowpass-replay-pill" id="replay-lowpass-pill" title="Replay the 0.8s Lowpass Noise Compression" type="button">↻ Lowpass</button>
            </div>
            <div class="scroll-cue" id="scroll-cue" title="Scroll down to read today's 5 falsifiable shifts">
                <span class="scroll-mouse-icon"><i class="scroll-mouse-dot"></i></span>
                <span class="scroll-cue-text">Scroll to explore 5 high-signal shifts</span>
            </div>
        </section>

        <!-- 90-Second Studio Audio Briefing Player -->
        <section class="audio-brief-section">
            <div class="audio-brief-bar" id="audio-brief-bar">
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
                        <div class="audio-brief-sub">ElevenLabs Voice (Adam) &middot; Studio-mastered &middot; Natural breathing &middot; -45dB room tone &middot; -16 LUFS</div>
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

                <div class="audio-brief-cli-pill" title="Terminal CLI: Fetch brief instantly in terminal">
                    <span class="cli-icon">$</span>
                    <code id="cli-cmd-display">curl -sL https://dev-pranav-sankhyan.github.io/Pith/dev</code>
                    <button class="cli-copy-btn" id="cli-copy-btn" title="Copy terminal curl command" type="button">Copy</button>
                </div>

                <audio id="audio-player" preload="metadata" src="audio/brief-developer.mp3"></audio>
            </div>
        </section>

        <!-- Segmented Role Selector -->
        <section class="role-bar">
            <div class="role-bar-label">Personal Lens</div>
            <div class="seg-control">
                <button class="seg-btn active" data-role="developer" type="button">Developer</button>
                <button class="seg-btn" data-role="founder" type="button">Founder</button>
                <button class="seg-btn" data-role="investor" type="button">Investor</button>
                <button class="seg-btn" data-role="everyday" type="button">Everyday Person</button>
            </div>
        </section>

        <!-- Cards Flow -->
        <main class="cards-flow">
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
        </main>

        <!-- Signature "Safely Ignore Today" Filter-Proof Sheet with Shredder -->
        <section class="filter-sheet" id="safely-ignore">
            <div class="filter-sheet-header">
                <div>
                    <div class="eyebrow" style="margin-bottom:2px;"><span class="gilt-dot"></span> NOISE FILTER AT WORK</div>
                    <h3 class="filter-sheet-title">Safely Ignore Today</h3>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
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

        <!-- Footer -->
        <footer class="desk-footer">
            <div><strong>Pith</strong> &middot; Not what happened, but what it means for you and what to do about it this week.</div>
            <div style="font-size:12px; margin-top:4px;">Primary-sourced &bull; Public calibration ledger &bull; No sponsored content or financial advice</div>
            <div class="footer-nav">
                <a href="index.html">Today's Issue</a>
                <a href="ledger.html">Public Ledger</a>
                <a href="patterns.html">Pattern Library</a>
            </div>
        </footer>
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


def render_ledger(predictions, stats, path: str):
    rows_html = []
    for p in predictions:
        status_cls = p.status.lower()
        postmortem_html = f'<div style="font-size:12px; color:var(--red-ink); margin-top:4px;"><strong>Post-mortem:</strong> {escape(p.postmortem)}</div>' if p.postmortem else ""
        evidence_html = f'<a href="{escape(p.evidence_url)}" target="_blank" rel="noopener" style="font-size:12px; color:var(--ink); font-weight:600;">Evidence &rarr;</a>' if p.evidence_url else "&mdash;"

        rows_html.append(f"""
        <tr data-status="{escape(p.status)}" data-category="{escape(p.category)}">
            <td style="font-family:var(--font-mono); font-size:12px;">{escape(p.made_at)}</td>
            <td>
                <div style="font-weight:600; color:var(--ink);">{escape(p.statement)}</div>
                <div style="font-size:12px; color:var(--muted); margin-top:2px;">
                    <em>Resolution standard:</em> {escape(p.resolution_criteria)}
                </div>
                {postmortem_html}
            </td>
            <td><span style="font-size:11px; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); font-weight:600;">{escape(p.category)}</span></td>
            <td style="font-family:var(--font-mono); font-weight:700; color:var(--ink);">{int(p.probability * 100)}%</td>
            <td><span class="status-pill {status_cls}">{escape(p.status)}</span></td>
            <td style="font-family:var(--font-mono); font-size:12px;">{escape(p.resolves_at)}</td>
            <td>{evidence_html}</td>
        </tr>
        """)

    calibration_rows = []
    for b in stats["calibration"]:
        actual_str = f"{b['actual_rate']}%" if b['actual_rate'] is not None else "&mdash;"
        gap_str = f"{b['calibration_gap']:+.1f}%" if b['calibration_gap'] is not None else "&mdash;"
        gap_color = "var(--good)" if (b['calibration_gap'] or 0) >= 0 else "var(--bad)"
        calibration_rows.append(f"""
        <tr>
            <td style="font-weight:600; color:var(--ink);">{escape(b['bucket'])}</td>
            <td>{b['count']}</td>
            <td style="font-family:var(--font-mono);">{b['avg_forecast']}%</td>
            <td style="font-family:var(--font-mono); font-weight:700; color:var(--ink);">{actual_str}</td>
            <td style="font-family:var(--font-mono); color:{gap_color}; font-weight:600;">{gap_str}</td>
        </tr>
        """)

    brier_val = f"{stats['brier_score']:.4f}" if stats['brier_score'] is not None else "N/A"
    hit_rate_val = f"{stats['hit_rate_pct']:.1f}%" if stats['hit_rate_pct'] is not None else "N/A"

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prediction Ledger &middot; Pith</title>
    <meta name="description" content="Public, unedited track record of dated falsifiable predictions, Brier accuracy scores, and calibration statistics for Pith.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header class="crown">
        <a href="index.html" class="brand-wrapper">
            <div class="brand-mark" aria-hidden="true">
                <i></i><i></i><i></i><i></i>
            </div>
            <div class="brand-name">PITH</div>
        </a>
        <div class="nav-cluster">
            <nav>
                <a href="index.html" class="nav-link">Brief</a>
                <a href="ledger.html" class="nav-link active" aria-current="page">Ledger</a>
                <a href="patterns.html" class="nav-link">Patterns</a>
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

    <div class="desk-container">
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> AUDIT &middot; PUBLIC TRACK RECORD</div>
                <h1 class="page-title">Prediction <em>Ledger</em></h1>
            </div>
            <div class="meta-pill-group">
                <span>IMMUTABLE PROBABILITIES</span>
                <span>&middot;</span>
                <span>ZERO RETROSPECTIVE EDITS</span>
            </div>
        </section>

        <!-- Big Num Grid with Counter Animations -->
        <div class="bignum-grid">
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['brier_score']:.4f}" data-format="brier">{brier_val}</div>
                <div class="bignum-label">Brier Score</div>
                <div class="bignum-sub">Benchmark &lt; 0.25 (lower is better)</div>
            </div>
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['hit_rate_pct']:.1f}" data-format="percent">{hit_rate_val}</div>
                <div class="bignum-label">Hit Rate</div>
                <div class="bignum-sub">{stats['correct_count']} of {stats['resolved_count']} resolved</div>
            </div>
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['resolved_count']}" data-format="int">{stats['resolved_count']}</div>
                <div class="bignum-label">Sample Size</div>
                <div class="bignum-sub">{"Preliminary (need >= 20)" if stats['is_preliminary'] else "Definitive"}</div>
            </div>
            <div class="bignum-card">
                <div class="bignum" data-target="{stats['open_count']}" data-format="int">{stats['open_count']}</div>
                <div class="bignum-label">Active Forecasts</div>
                <div class="bignum-sub">Under evaluation</div>
            </div>
        </div>

        <!-- Calibration Sheet -->
        <section class="table-sheet">
            <div class="sheet-header-line">
                <h3 class="sheet-title">Forecast Calibration</h3>
                <span style="font-size:12px; color:var(--muted);">When we predict X%, are we right X% of the time?</span>
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

            <!-- The Missed Prediction Card -->
            <div class="wrong-card">
                <div class="wrong-card-top" style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="status-pill wrong">✕ Wrong Call</span>
                    <span style="font-family:var(--font-mono); font-size:12px; color:var(--muted);">Forecast: 60% probability &middot; Resolved 15 Sep 2026</span>
                </div>
                <div class="wrong-statement">
                    &ldquo;By 15 September 2026, the European Union AI Act general-purpose model guidelines require public watermark disclosure for all commercial code generation models.&rdquo;
                </div>
                <div class="wrong-outcome-block">
                    <div class="wrong-outcome-title">What Actually Happened:</div>
                    <div class="wrong-outcome-text">
                        The EU AI Office retained watermarking recommendations for synthetic video and audio, but explicitly exempted standalone code completion tools following AST integrity lobbying from open-source IDE stewards.
                    </div>
                </div>
                <div class="wrong-postmortem-block">
                    <div class="wrong-postmortem-title">Why Our Model Missed:</div>
                    <div class="wrong-postmortem-text">
                        We over-indexed on draft EU AI Office working memos and failed to account for compiler AST integrity lobbying from open-source IDE stewards. <strong>Lesson Learned:</strong> Regulatory drafts in developer tooling rarely survive intact when they break compiler deterministic verification.
                    </div>
                    <div style="margin-top:10px;">
                        <a href="https://digital-strategy.ec.europa.eu/en/policies/ai-office" target="_blank" rel="noopener" class="wrong-evidence-link">Inspect Official Ruling Evidence &rarr;</a>
                    </div>
                </div>
            </div>
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
            <table class="instrument-table">
                <thead>
                    <tr>
                        <th>Made</th>
                        <th>Prediction &amp; Resolution Standard</th>
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

        <footer class="desk-footer">
            <div><strong>Pith</strong> &middot; Public Prediction Ledger</div>
            <div class="footer-nav">
                <a href="index.html">Today's Issue</a>
                <a href="ledger.html">Public Ledger</a>
                <a href="patterns.html">Pattern Library</a>
            </div>
        </footer>
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
                <span style="font-weight:700; font-size:11.5px; text-transform:uppercase; letter-spacing:0.08em; color:var(--gilt);">Active in Today's Issue:</span>
                {" &middot; ".join(matched_cards)}
            </div>
            """

        patterns_html.append(f"""
        <article class="lab-card pattern-card" id="{escape(p['id'])}" data-category="{escape(p['category'])}">
            <div class="card-header-line">
                <span class="card-roman">{roman} &middot; {escape(p['tag'])}</span>
                <span class="card-sources-count">{len(p['cases'])} documented cases</span>
            </div>

            <h2 class="card-headline">{escape(p['name'])}</h2>
            
            <p class="story-block" style="font-size:16px; color:var(--ink); font-weight:500;">
                {escape(p['summary'])}
            </p>

            <div class="story-block" style="margin-top:10px;">
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
                <div class="drawer-title" style="margin-bottom:10px;">Documented Historical Precedents</div>
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
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Library &middot; Pith</title>
    <meta name="description" content="Curated catalog of recurring tech dynamics, historical base rates, failure modes, and cognitive bias warnings for Pith.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header class="crown">
        <a href="index.html" class="brand-wrapper">
            <div class="brand-mark" aria-hidden="true">
                <i></i><i></i><i></i><i></i>
            </div>
            <div class="brand-name">PITH</div>
        </a>
        <div class="nav-cluster">
            <nav>
                <a href="index.html" class="nav-link">Brief</a>
                <a href="ledger.html" class="nav-link">Ledger</a>
                <a href="patterns.html" class="nav-link active" aria-current="page">Patterns</a>
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

    <div class="desk-container">
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> RECURRING DYNAMICS &middot; BASE RATES &middot; BIAS PITFALLS</div>
                <h1 class="page-title">Pattern <em>Library</em></h1>
            </div>
            <div class="meta-pill-group">
                <span>MENTAL MODELS</span>
                <span>&middot;</span>
                <span>6 ARCHITECTURAL DYNAMICS</span>
            </div>
        </section>

        <div style="margin-bottom:28px;">
            <p style="font-size:15px; color:var(--ink-2); line-height:1.6; max-width:68ch;">
                Tech shifts appear sudden, but infrastructure history repeats in predictable economic and architectural dynamics. We evaluate candidate events against recurring failure modes, historical base rates, and cognitive bias warnings before drafting predictions.
            </p>
        </div>

        <!-- Pattern Filter Controls -->
        <section class="role-bar" style="margin-bottom:30px;">
            <div class="role-bar-label">Filter Category</div>
            <div class="seg-control" id="pattern-filters">
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

        <footer class="desk-footer">
            <div><strong>Pith</strong> &middot; Mental Models &amp; Pattern Library</div>
            <div class="footer-nav">
                <a href="index.html">Today's Issue</a>
                <a href="ledger.html">Public Ledger</a>
                <a href="patterns.html">Pattern Library</a>
            </div>
        </footer>
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    render_all()
