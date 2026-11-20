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
        ("index.html", "Daily News"),
        ("matrix.html", "Market Map"),
        ("economics.html", "Cost Calculator"),
        ("terminal.html", "CLI Terminal"),
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
                <a href="index.html">Daily News</a>
                <a href="matrix.html">Market Map</a>
                <a href="economics.html">Cost Calculator</a>
                <a href="terminal.html">CLI Terminal</a>
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
# 2. MATRIX.HTML - THE PLATFORM SQUEEZE & MOAT MATRIX
# ==============================================================================
def render_matrix(cards: List[Card], path: str):
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Power Map &middot; Pith</title>
    <meta name="description" content="Interactive 2x2 Market Power Map: Chokepoints vs Compounding Moats vs Commoditized Layers vs Squeezed Middleware in tech infrastructure.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    {get_ambient_bg_html()}
    {get_nav_html("matrix.html")}

    <div class="desk-container">
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> MARKET POWER &middot; COMPETITIVE DEFENSIBILITY &middot; PLATFORM RISK</div>
                <h1 class="page-title">Market <em>Power Map</em></h1>
                <p style="font-size:15px; color:var(--muted); max-width:680px; margin-top:8px; line-height:1.5;">A 2×2 map of technology layers. Identifies true chokepoint monopolies, compounding proprietary moats, commoditized compute, and middleware vulnerable to platform sherlocking.</p>
            </div>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> ECONOMIC POWER INDEX</span>
                <span>&middot;</span>
                <span>SHERLOCKING RADAR</span>
                <span>&middot;</span>
                <span>SWITCHING FRICTION</span>
            </div>
        </section>

        <!-- 2x2 Interactive Ecosystem Matrix Canvas -->
        <section class="matrix-canvas-wrapper">
            <div class="matrix-axis-label vertical">▲ ECONOMIC RENT &amp; MARGIN DEFENSIBILITY (HIGH)</div>
            
            <div class="matrix-grid">
                <!-- Q1: The Chokepoints -->
                <div class="matrix-quadrant chokepoint" id="quad-chokepoint">
                    <div class="quad-header">
                        <span class="quad-badge chokepoint">QUADRANT II &middot; CHOKEPOINTS</span>
                        <span class="quad-sub">Monopoly Pricing Power &bull; High Switching Cost</span>
                    </div>
                    <div class="quad-nodes">
                        <div class="matrix-node" data-risk="15%" data-layer="Hardware Packaging">
                            <strong>CoWoS &amp; Optical Interconnects</strong>
                            <span>Nvidia, TSMC packaging allocation bottleneck</span>
                        </div>
                        <div class="matrix-node" data-risk="20%" data-layer="Frontier Weights">
                            <strong>Proprietary Reasoning Models</strong>
                            <span>Massive capital barrier ($1B+ training clusters)</span>
                        </div>
                        <div class="matrix-node" data-risk="25%" data-layer="OS Integration">
                            <strong>Native OS Permission Sandboxes</strong>
                            <span>Apple Intelligence, Android OS-level agent APIs</span>
                        </div>
                    </div>
                </div>

                <!-- Q2: Compounding Moats -->
                <div class="matrix-quadrant moat" id="quad-moat">
                    <div class="quad-header">
                        <span class="quad-badge moat">QUADRANT IV &middot; COMPOUNDING MOATS</span>
                        <span class="quad-sub">Network Effects &bull; Standard Protocol Ownership</span>
                    </div>
                    <div class="quad-nodes">
                        <div class="matrix-node" data-risk="30%" data-layer="Protocol Standards">
                            <strong>Open Agent Protocol (Model Context Protocol)</strong>
                            <span>Ecosystem standard with multi-client network effects</span>
                        </div>
                        <div class="matrix-node" data-risk="35%" data-layer="OSS Runtime Kernels">
                            <strong>vLLM &amp; PyTorch 2.6 AOTInductor Kernels</strong>
                            <span>Open-source community optimization engine</span>
                        </div>
                        <div class="matrix-node" data-risk="25%" data-layer="Data Workflows">
                            <strong>Production Evaluation Datasets</strong>
                            <span>Proprietary task ground-truth and telemetry</span>
                        </div>
                    </div>
                </div>

                <!-- Q3: The Squeezed (Sherlocked) -->
                <div class="matrix-quadrant squeezed" id="quad-squeezed">
                    <div class="quad-header">
                        <span class="quad-badge squeezed">QUADRANT I &middot; THE SQUEEZED</span>
                        <span class="quad-sub">Extreme Sherlocking Risk &bull; Zero Pricing Power</span>
                    </div>
                    <div class="quad-nodes">
                        <div class="matrix-node danger" data-risk="92%" data-layer="UI Wrappers">
                            <strong>Thin LLM Wrapper Tools</strong>
                            <span>Vulnerable to single platform feature updates</span>
                        </div>
                        <div class="matrix-node danger" data-risk="85%" data-layer="Single-Vendor Agents">
                            <strong>Closed Desktop UI Clickers</strong>
                            <span>Bypassed by native OS Computer Use APIs</span>
                        </div>
                        <div class="matrix-node danger" data-risk="78%" data-layer="Prompt Middleware">
                            <strong>Basic Prompt Chaining Libraries</strong>
                            <span>Subsumed into standardized runtime RPC endpoints</span>
                        </div>
                    </div>
                </div>

                <!-- Q4: The Commodities -->
                <div class="matrix-quadrant commodity" id="quad-commodity">
                    <div class="quad-header">
                        <span class="quad-badge commodity">QUADRANT III &middot; COMMODITIES</span>
                        <span class="quad-sub">Deflationary Race to Zero &bull; Margin Compression</span>
                    </div>
                    <div class="quad-nodes">
                        <div class="matrix-node warn" data-risk="65%" data-layer="Compute Hosting">
                            <strong>Generic GPU Cloud Resellers</strong>
                            <span>Aggressive price competition and spot commoditization</span>
                        </div>
                        <div class="matrix-node warn" data-risk="70%" data-layer="Token Generation">
                            <strong>Unspecialized Open-Weights Hosting</strong>
                            <span>Per-token pricing racing toward zero electricity cost</span>
                        </div>
                        <div class="matrix-node warn" data-risk="60%" data-layer="Vector Indexing">
                            <strong>Generic Vector DB Plugins</strong>
                            <span>Natively integrated into PostgreSQL (pgvector) and SQLite</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="matrix-axis-label horizontal">SWITCHING COST / FRICTION (LOW &rarr; EXTREME LOCK-IN) ▶</div>
        </section>

        <!-- Sherlocking Risk Threat Radar Table -->
        <section class="sherlock-radar-section">
            <div class="sherlock-header">
                <span class="sherlock-badge">PLATFORM SHERLOCKING RISK INDEX</span>
                <h3>Who is actively capturing margin from developer startups?</h3>
            </div>
            <div class="sherlock-table-card">
                <table class="sherlock-table">
                    <thead>
                        <tr>
                            <th>Platform Aggressor</th>
                            <th>Target Startup Layer</th>
                            <th>Vulnerability Mechanism</th>
                            <th>Sherlock Risk</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Anthropic / OpenAI</strong></td>
                            <td>RPA &amp; Screen Scraper SaaS</td>
                            <td>Native Computer Use API standardizes desktop GUI input</td>
                            <td><span class="status-pill critical">92% Critical</span></td>
                        </tr>
                        <tr>
                            <td><strong>Google / Chrome</strong></td>
                            <td>Browser Automation Extensions</td>
                            <td>Chromium native virtualized OS agent permissions</td>
                            <td><span class="status-pill critical">88% Critical</span></td>
                        </tr>
                        <tr>
                            <td><strong>Open Source (vLLM/SGLang)</strong></td>
                            <td>Proprietary Inference Middleware</td>
                            <td>Prefix caching and FP8 GEMM kernels standardized in OSS</td>
                            <td><span class="status-pill high">78% High</span></td>
                        </tr>
                        <tr>
                            <td><strong>PostgreSQL / SQLite</strong></td>
                            <td>Pure Vector Database Startups</td>
                            <td>pgvector + sqlite-vec subsumes 90% of production RAG</td>
                            <td><span class="status-pill high">74% High</span></td>
                        </tr>
                    </tbody>
                </table>
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


# ==============================================================================
# 3. ECONOMICS.HTML - INFERENCE MATH & HARDWARE REALITY CALCULATOR
# ==============================================================================
def render_economics(cards: List[Card], path: str):
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Cost Calculator &middot; Pith</title>
    <meta name="description" content="Interactive token cost, KV cache memory footprint, and bare-metal vs cloud API breakeven calculator for AI engineering teams.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    {get_ambient_bg_html()}
    {get_nav_html("economics.html")}

    <div class="desk-container">
        <section class="masthead">
            <div>
                <div class="eyebrow"><span class="gilt-dot"></span> UNIT ECONOMICS &middot; CLOUD API VS BARE-METAL GPU CLUSTER</div>
                <h1 class="page-title">AI <em>Cost Calculator</em></h1>
                <p style="font-size:15px; color:var(--muted); max-width:680px; margin-top:8px; line-height:1.5;">Model serving unit economics calculator. Adjust your user volume and token consumption to calculate exactly when self-hosting on dedicated GPUs becomes cheaper than managed cloud APIs.</p>
            </div>
            <div class="meta-pill-group">
                <span class="live-telemetry-chip"><i class="radar-dot"></i> HARDWARE REALITY CHECK</span>
                <span>&middot;</span>
                <span>API VS DEDICATED GPUS</span>
                <span>&middot;</span>
                <span>KV CACHE SIZING</span>
            </div>
        </section>

        <!-- Interactive Calculator Workspace -->
        <div class="calc-workspace-grid">
            <!-- Left Column: Interactive Controls & Sliders -->
            <div class="calc-controls-card lab-card">
                <div class="calc-section-title">1. Operational Traffic Inputs</div>
                
                <div class="calc-slider-group">
                    <div class="slider-header">
                        <label for="dau-slider">Daily Active Users (DAU)</label>
                        <span class="slider-val" id="dau-val">25,000</span>
                    </div>
                    <input type="range" id="dau-slider" min="1000" max="500000" step="1000" value="25000">
                </div>

                <div class="calc-slider-group">
                    <div class="slider-header">
                        <label for="req-slider">Requests per User / Day</label>
                        <span class="slider-val" id="req-val">12 reqs</span>
                    </div>
                    <input type="range" id="req-slider" min="1" max="100" step="1" value="12">
                </div>

                <div class="calc-slider-group">
                    <div class="slider-header">
                        <label for="input-tok-slider">Avg Input Tokens (Context)</label>
                        <span class="slider-val" id="input-tok-val">2,400 tok</span>
                    </div>
                    <input type="range" id="input-tok-slider" min="200" max="32000" step="200" value="2400">
                </div>

                <div class="calc-slider-group">
                    <div class="slider-header">
                        <label for="output-tok-slider">Avg Output Tokens (Generation)</label>
                        <span class="slider-val" id="output-tok-val">450 tok</span>
                    </div>
                    <input type="range" id="output-tok-slider" min="50" max="4000" step="50" value="450">
                </div>

                <div class="calc-section-title" style="margin-top:20px;">2. Model Architecture &amp; Precision</div>
                <div class="calc-btn-group" id="model-tier-buttons">
                    <button class="calc-choice-btn active" data-tier="medium" type="button">70B Parameter (Llama 3.3 / Qwen 2.5)</button>
                    <button class="calc-choice-btn" data-tier="frontier" type="button">Frontier MoE (DeepSeek-V3 / Sonnet)</button>
                    <button class="calc-choice-btn" data-tier="small" type="button">8B Edge / Fast (Llama 3.1 8B)</button>
                </div>

                <div class="calc-section-title" style="margin-top:20px;">3. Architecture Presets (From Today's Shifts)</div>
                <div class="calc-presets-pills">
                    <button class="preset-pill" id="preset-deepseek" type="button">✦ DeepSeek-V3 DualPipe FP8</button>
                    <button class="preset-pill" id="preset-cloudflare" type="button">✦ Cloudflare Edge Streaming FP8</button>
                    <button class="preset-pill" id="preset-vllm" type="button">✦ vLLM Prefix Caching Cluster</button>
                </div>
            </div>

            <!-- Right Column: Live Economic Output Gauges -->
            <div class="calc-telemetry-col">
                <div class="telemetry-box cloud-cost">
                    <div class="telemetry-badge">PROPRIETARY CLOUD API BILLING</div>
                    <div class="telemetry-big-num" id="cloud-monthly-cost">$28,350<small>/mo</small></div>
                    <div class="telemetry-sub" id="cloud-cost-sub">Based on standard $3.00/M input + $15.00/M output</div>
                </div>

                <div class="telemetry-box baremetal-cost">
                    <div class="telemetry-badge">SELF-HOSTED GPU CLUSTER (vLLM + FP8)</div>
                    <div class="telemetry-big-num" id="baremetal-monthly-cost">$9,600<small>/mo</small></div>
                    <div class="telemetry-sub" id="baremetal-cost-sub">4x H100 SXM5 node rented on spot/reserve bare metal</div>
                </div>

                <div class="telemetry-box delta-box">
                    <div class="telemetry-badge">PROJECTED NET ARBITRAGE</div>
                    <div class="delta-headline" id="delta-savings">Save +$18,750 / mo (66.1%)</div>
                    <div class="delta-inflection" id="delta-inflection">
                        <strong>Migration Inflection Point:</strong> Self-hosting becomes cheaper above <strong>8,400 DAU</strong>.
                    </div>
                </div>

                <div class="calc-hardware-specs lab-card">
                    <div class="specs-title">Hardware Memory &amp; Throughput Footprint</div>
                    <div class="spec-row">
                        <span>KV Cache Memory Required:</span>
                        <strong id="spec-kv-memory">38.4 GB</strong>
                    </div>
                    <div class="spec-row">
                        <span>Total Monthly Tokens Processed:</span>
                        <strong id="spec-total-tokens">25.65 Billion</strong>
                    </div>
                    <div class="spec-row">
                        <span>Required Node GPU Count:</span>
                        <strong id="spec-gpu-count">4x H100 (80GB)</strong>
                    </div>
                    <div class="spec-row">
                        <span>Prefix Caching Savings:</span>
                        <strong style="color:#10B981;" id="spec-cache-savings">~35% latency cut</strong>
                    </div>
                </div>
            </div>
        </div>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ==============================================================================
# 4. TERMINAL.HTML - FULL-SCREEN HACKER WEB TERMINAL
# ==============================================================================
def render_terminal(latest_issue: DailyIssue, path: str):
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CLI Terminal &middot; Pith</title>
    <meta name="description" content="Interactive browser ANSI terminal workstation for Pith. Type commands, listen to briefings, inspect forecasts in a developer sandbox.">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css">
</head>
<body class="terminal-body-page">
    {get_ambient_bg_html()}
    {get_nav_html("terminal.html")}

    <div class="desk-container terminal-container">
        <!-- Terminal Outer Window Frame -->
        <div class="term-window">
            <div class="term-titlebar">
                <div class="term-traffic-lights">
                    <span class="term-light close"></span>
                    <span class="term-light min"></span>
                    <span class="term-light max"></span>
                </div>
                <div class="term-title">pith-agent@station: ~ (VT100 &bull; 9600 BAUD &bull; ANSI COLOR)</div>
                <div class="term-theme-toggle">
                    <button class="term-font-btn active" data-phosphor="amber" type="button">Amber</button>
                    <button class="term-font-btn" data-phosphor="emerald" type="button">Emerald</button>
                    <button class="term-font-btn" data-phosphor="cyan" type="button">Cyan</button>
                </div>
            </div>

            <!-- Terminal Screen -->
            <div class="term-screen" id="term-screen">
                <div class="term-welcome">
<pre class="ascii-banner">
██████╗ ██╗████████╗██╗  ██╗
██╔══██╗██║╚══██╔══╝██║  ██║   P I T H   T E R M I N A L
██████╔╝██║   ██║   ███████║   HIGH-SIGNAL TECH INTELLIGENCE
██╔═══╝ ██║   ██║   ██╔══██║   OBSIDIAN ANSI WORKSTATION
██║     ██║   ██║   ██║  ██║
╚═╝     ╚═╝   ╚═╝   ╚═╝  ╚═╝
</pre>
                    <div class="term-meta-line">SYSTEM STATUS: <span style="color:#10B981;">ALL RUNTIMES OPTIMAL</span> &bull; DATE: {latest_issue.date} &bull; BEAT: {latest_issue.beat}</div>
                    <div class="term-help-hint">Type <span class="term-key">help</span> to list commands, or try <span class="term-key">today</span>, <span class="term-key">listen</span>, <span class="term-key">stats</span>, <span class="term-key">matrix</span>, <span class="term-key">calc</span>, <span class="term-key">clear</span>.</div>
                </div>

                <div class="term-output-history" id="term-output-history"></div>

                <!-- Input Prompt Line -->
                <div class="term-input-line">
                    <span class="term-prompt">pith@intel:~$</span>
                    <input type="text" id="term-input" class="term-cli-input" autofocus autocomplete="off" spellcheck="false">
                </div>
            </div>
        </div>

        <!-- Quick Terminal Command Pills -->
        <div class="term-quick-bar">
            <span>Quick Commands:</span>
            <button class="term-chip-btn" data-cmd="today" type="button">today</button>
            <button class="term-chip-btn" data-cmd="listen developer" type="button">listen developer</button>
            <button class="term-chip-btn" data-cmd="stats" type="button">stats</button>
            <button class="term-chip-btn" data-cmd="matrix" type="button">matrix</button>
            <button class="term-chip-btn" data-cmd="calc 50000 15" type="button">calc 50000 15</button>
            <button class="term-chip-btn" data-cmd="curl" type="button">curl</button>
            <button class="term-chip-btn" data-cmd="clear" type="button">clear</button>
        </div>

        {get_footer_html()}
    </div>
    <script src="app.js"></script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


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
