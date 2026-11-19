"""
Pith Interactive Architectural Schematics & Flowcharts.
Generates responsive, dark-mode native, high-tech SVG diagrams with
animated data streams, glowing nodes, and telemetry metrics.
"""

from typing import Dict


def get_card_schematic(card_id: str) -> str:
    """Returns interactive SVG diagram markup tailored to the specific card."""
    if card_id == "card-20261119-cache-cut":
        return """
        <div class="schematic-wrapper" data-schematic="kv-cache">
            <div class="schematic-header">
                <div class="schematic-title-group">
                    <span class="schematic-badge">ARCHITECTURE TOPOLOGY</span>
                    <h4 class="schematic-heading">Static Prefix Routing &amp; GPU HBM Cache Pipeline</h4>
                </div>
                <div class="schematic-telemetry">
                    <span class="telemetry-pill good">HBM Bandwidth: 3.2 TB/s</span>
                    <span class="telemetry-pill">Cache Hit Rate: ~82%</span>
                </div>
            </div>
            <div class="svg-schematic-canvas">
                <svg viewBox="0 0 740 220" fill="none" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
                    <defs>
                        <linearGradient id="grad-gold" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#B58900" stop-opacity="0.8"/>
                            <stop offset="100%" stop-color="#D97706" stop-opacity="0.9"/>
                        </linearGradient>
                        <linearGradient id="grad-green" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#10B981" stop-opacity="0.9"/>
                            <stop offset="100%" stop-color="#059669" stop-opacity="0.9"/>
                        </linearGradient>
                        <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.9"/>
                            <stop offset="100%" stop-color="#1D4ED8" stop-opacity="0.9"/>
                        </linearGradient>
                        <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="3" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                    </defs>

                    <!-- Background Grid Lines -->
                    <line x1="30" y1="110" x2="710" y2="110" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4" />

                    <!-- Animated Pulse Streams -->
                    <path d="M 145 110 L 225 110" class="flow-wire active-gold" />
                    <path d="M 365 110 L 435 60 L 515 60" class="flow-wire active-green" />
                    <path d="M 365 110 L 435 160 L 515 160" class="flow-wire active-dim" />
                    <path d="M 645 60 L 705 60" class="flow-wire active-green" />

                    <!-- Node 1: Incoming Prompt -->
                    <g class="diagram-node" transform="translate(25, 65)">
                        <rect width="120" height="90" rx="8" class="node-box" />
                        <text x="60" y="28" class="node-title">USER PROMPT</text>
                        <rect x="15" y="40" width="90" height="18" rx="4" fill="rgba(181,137,0,0.25)" stroke="#B58900" stroke-width="1" />
                        <text x="60" y="53" class="node-sub-tag">Static Prefix (8k)</text>
                        <rect x="15" y="62" width="90" height="18" rx="4" fill="rgba(255,255,255,0.06)" />
                        <text x="60" y="75" class="node-sub-tag">Query Tail (500t)</text>
                    </g>

                    <!-- Node 2: Prefix Hash Registry -->
                    <g class="diagram-node" transform="translate(225, 65)">
                        <rect width="140" height="90" rx="8" class="node-box accent-box" />
                        <text x="70" y="26" class="node-title">PREFIX REGISTRY</text>
                        <text x="70" y="48" class="node-desc">SHA-256 Attention Mask</text>
                        <text x="70" y="66" class="node-desc">Boundary Hash Match</text>
                        <rect x="25" y="73" width="90" height="12" rx="3" fill="rgba(16,185,129,0.15)" />
                        <text x="70" y="82" class="node-stat">Cache-Key: #9E20F</text>
                    </g>

                    <!-- Node 3A: Cache Hit Path (Green) -->
                    <g class="diagram-node" transform="translate(515, 20)">
                        <rect width="130" height="80" rx="8" class="node-box hit-box" />
                        <circle cx="15" cy="18" r="4" fill="#10B981" filter="url(#neon-glow)" />
                        <text x="72" y="22" class="node-title good">CACHE HIT ($0.25/M)</text>
                        <text x="65" y="42" class="node-desc">GPU HBM3e Resident</text>
                        <text x="65" y="58" class="node-desc">O(1) Memory Pointer</text>
                        <text x="65" y="72" class="node-badge-text">90% BILLING DISCOUNT</text>
                    </g>

                    <!-- Node 3B: Cache Miss Path (Gray/Red) -->
                    <g class="diagram-node" transform="translate(515, 120)">
                        <rect width="130" height="80" rx="8" class="node-box miss-box" />
                        <circle cx="15" cy="18" r="4" fill="#EF4444" />
                        <text x="72" y="22" class="node-title warn">CACHE MISS ($2.50/M)</text>
                        <text x="65" y="42" class="node-desc">Full O(N²) Self-Attention</text>
                        <text x="65" y="58" class="node-desc">Redundant Compute Loop</text>
                        <text x="65" y="72" class="node-badge-text red">10x COST OVERHEAD</text>
                    </g>
                </svg>
            </div>
            <div class="schematic-footer-notes">
                <span>✦ <strong>Architectural Rule:</strong> Keep variable system state (timestamps, user IDs) strictly in prompt tails to guarantee prefix reuse.</span>
            </div>
        </div>
        """

    elif card_id == "card-20261119-computer-use":
        return """
        <div class="schematic-wrapper" data-schematic="computer-use">
            <div class="schematic-header">
                <div class="schematic-title-group">
                    <span class="schematic-badge">CONTROL LOOP TOPOLOGY</span>
                    <h4 class="schematic-heading">Autonomous Desktop OS Control Feedback Loop</h4>
                </div>
                <div class="schematic-telemetry">
                    <span class="telemetry-pill warn">Loop Latency: ~2.4s</span>
                    <span class="telemetry-pill good">Zero Custom Scrapers</span>
                </div>
            </div>
            <div class="svg-schematic-canvas">
                <svg viewBox="0 0 740 210" fill="none" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
                    <!-- Circular Feedback Loop Pathway -->
                    <rect x="40" y="30" width="660" height="150" rx="20" class="loop-track" stroke="rgba(255,255,255,0.08)" stroke-width="2" stroke-dasharray="6 6" />

                    <!-- Step 1: Display Capture -->
                    <g class="diagram-node" transform="translate(60, 60)">
                        <rect width="135" height="90" rx="8" class="node-box" />
                        <text x="67" y="26" class="node-step">STEP 01</text>
                        <text x="67" y="46" class="node-title">FRAMEBUFFER</text>
                        <text x="67" y="64" class="node-desc">1080p Screen Capture</text>
                        <text x="67" y="78" class="node-stat">Lossless PNG Array</text>
                    </g>

                    <!-- Connector Arrow 1 -->
                    <path d="M 195 105 L 235 105" class="flow-wire active-gold" />

                    <!-- Step 2: VLM Grounding -->
                    <g class="diagram-node" transform="translate(235, 60)">
                        <rect width="135" height="90" rx="8" class="node-box accent-box" />
                        <text x="67" y="26" class="node-step">STEP 02</text>
                        <text x="67" y="46" class="node-title">VISION GROUNDING</text>
                        <text x="67" y="64" class="node-desc">Predict Coordinates</text>
                        <text x="67" y="78" class="node-stat">{ x: 842, y: 318 }</text>
                    </g>

                    <!-- Connector Arrow 2 -->
                    <path d="M 370 105 L 410 105" class="flow-wire active-green" />

                    <!-- Step 3: Sandboxed Action Injection -->
                    <g class="diagram-node" transform="translate(410, 60)">
                        <rect width="135" height="90" rx="8" class="node-box" />
                        <text x="67" y="26" class="node-step">STEP 03</text>
                        <text x="67" y="46" class="node-title">SYNTHETIC INPUT</text>
                        <text x="67" y="64" class="node-desc">Virtual Mouse / Keys</text>
                        <text x="67" y="78" class="node-stat">CoreGraphics Sandbox</text>
                    </g>

                    <!-- Connector Arrow 3 -->
                    <path d="M 545 105 L 585 105" class="flow-wire active-blue" />

                    <!-- Step 4: Software State -->
                    <g class="diagram-node" transform="translate(585, 60)">
                        <rect width="125" height="90" rx="8" class="node-box hit-box" />
                        <text x="62" y="26" class="node-step">STEP 04</text>
                        <text x="62" y="46" class="node-title">LEGACY SAAS</text>
                        <text x="62" y="64" class="node-desc">Desktop UI State Mutates</text>
                        <text x="62" y="78" class="node-stat">Cycle Time: 2.4s</text>
                    </g>
                </svg>
            </div>
            <div class="schematic-footer-notes">
                <span>✦ <strong>Strategic Impact:</strong> Automates legacy desktop and internal tools without requiring commercial REST API partnerships.</span>
            </div>
        </div>
        """

    elif card_id == "card-20261119-oap":
        return """
        <div class="schematic-wrapper" data-schematic="oap-protocol">
            <div class="schematic-header">
                <div class="schematic-title-group">
                    <span class="schematic-badge">INTEROPERABILITY TOPOLOGY</span>
                    <h4 class="schematic-heading">Open Agent Protocol (OAP) vs Proprietary SDK Spaghetti</h4>
                </div>
                <div class="schematic-telemetry">
                    <span class="telemetry-pill good">Vendor Neutral: CNCF / LF</span>
                    <span class="telemetry-pill">Transport: JSON-RPC 2.0</span>
                </div>
            </div>
            <div class="svg-schematic-canvas">
                <svg viewBox="0 0 740 200" fill="none" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
                    <!-- Left: Models -->
                    <g class="diagram-node" transform="translate(30, 20)">
                        <rect width="140" height="160" rx="8" class="node-box" />
                        <text x="70" y="24" class="node-title">AI MODELS</text>
                        <rect x="15" y="38" width="110" height="22" rx="4" fill="rgba(255,255,255,0.06)" />
                        <text x="70" y="53" class="node-sub-tag">Claude 3.5 / 3.7</text>
                        <rect x="15" y="68" width="110" height="22" rx="4" fill="rgba(255,255,255,0.06)" />
                        <text x="70" y="83" class="node-sub-tag">GPT-4o / o3</text>
                        <rect x="15" y="98" width="110" height="22" rx="4" fill="rgba(255,255,255,0.06)" />
                        <text x="70" y="113" class="node-sub-tag">Gemini 2.5 Pro</text>
                        <rect x="15" y="128" width="110" height="22" rx="4" fill="rgba(255,255,255,0.06)" />
                        <text x="70" y="143" class="node-sub-tag">DeepSeek / Llama 4</text>
                    </g>

                    <!-- Wires into Hub -->
                    <path d="M 170 50 L 290 100" class="flow-wire active-gold" />
                    <path d="M 170 80 L 290 100" class="flow-wire active-gold" />
                    <path d="M 170 110 L 290 100" class="flow-wire active-gold" />
                    <path d="M 170 140 L 290 100" class="flow-wire active-gold" />

                    <!-- Center Hub: OAP Protocol Specification -->
                    <g class="diagram-node" transform="translate(290, 45)">
                        <rect width="160" height="110" rx="12" class="node-box accent-box" stroke="#B58900" stroke-width="1.5" />
                        <circle cx="80" cy="24" r="5" fill="#B58900" />
                        <text x="80" y="44" class="node-title good">OPEN AGENT PROTOCOL</text>
                        <text x="80" y="64" class="node-desc">Standard Schema (JSON-RPC)</text>
                        <text x="80" y="80" class="node-desc">Bidirectional Tool Discovery</text>
                        <rect x="25" y="88" width="110" height="14" rx="3" fill="rgba(181,137,0,0.18)" />
                        <text x="80" y="98" class="node-stat">Universal MCP Bus</text>
                    </g>

                    <!-- Wires out of Hub -->
                    <path d="M 450 100 L 570 50" class="flow-wire active-green" />
                    <path d="M 450 100 L 570 80" class="flow-wire active-green" />
                    <path d="M 450 100 L 570 110" class="flow-wire active-green" />
                    <path d="M 450 100 L 570 140" class="flow-wire active-green" />

                    <!-- Right: Tools -->
                    <g class="diagram-node" transform="translate(570, 20)">
                        <rect width="140" height="160" rx="8" class="node-box hit-box" />
                        <text x="70" y="24" class="node-title">ENTERPRISE TOOLS</text>
                        <rect x="15" y="38" width="110" height="22" rx="4" fill="rgba(16,185,129,0.12)" />
                        <text x="70" y="53" class="node-sub-tag">PostgreSQL / Vector DB</text>
                        <rect x="15" y="68" width="110" height="22" rx="4" fill="rgba(16,185,129,0.12)" />
                        <text x="70" y="83" class="node-sub-tag">GitHub API &amp; CI/CD</text>
                        <rect x="15" y="98" width="110" height="22" rx="4" fill="rgba(16,185,129,0.12)" />
                        <text x="70" y="113" class="node-sub-tag">Slack / Linear Workflows</text>
                        <rect x="15" y="128" width="110" height="22" rx="4" fill="rgba(16,185,129,0.12)" />
                        <text x="70" y="143" class="node-sub-tag">Terminal Sandboxes</text>
                    </g>
                </svg>
            </div>
            <div class="schematic-footer-notes">
                <span>✦ <strong>Ecosystem Shift:</strong> Eliminates N×M bespoke SDK integrations; open tools gain universal client compatibility.</span>
            </div>
        </div>
        """

    elif card_id == "card-20261119-deepseek-mla":
        return """
        <div class="schematic-wrapper" data-schematic="deepseek-mla">
            <div class="schematic-header">
                <div class="schematic-title-group">
                    <span class="schematic-badge">SILICON &amp; TENSOR COMPRESSION</span>
                    <h4 class="schematic-heading">Multi-Head Latent Attention (MLA) vs Standard MHA</h4>
                </div>
                <div class="schematic-telemetry">
                    <span class="telemetry-pill good">Memory Reduction: -87.5%</span>
                    <span class="telemetry-pill">KV Cache: 16 KB/tok</span>
                </div>
            </div>
            <div class="svg-schematic-canvas">
                <svg viewBox="0 0 740 190" fill="none" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
                    <!-- Standard MHA Bar -->
                    <g transform="translate(40, 30)">
                        <text x="0" y="18" class="node-title">Standard Multi-Head Attention (MHA)</text>
                        <text x="560" y="18" class="node-stat warn">128 KB / Token (HBM Bottleneck)</text>
                        <rect x="0" y="30" width="660" height="32" rx="6" fill="rgba(239,68,68,0.15)" stroke="#EF4444" stroke-width="1" />
                        <rect x="0" y="30" width="660" height="32" rx="6" fill="url(#grad-red-stripes)" />
                        <text x="330" y="51" class="node-bar-label">128 Heads × 128 Dim (Keys &amp; Values Uncompressed)</text>
                    </g>

                    <!-- DeepSeek MLA Bar -->
                    <g transform="translate(40, 105)">
                        <text x="0" y="18" class="node-title good">DeepSeek Multi-Head Latent Attention (MLA)</text>
                        <text x="560" y="18" class="node-stat good">16 KB / Token (-87.5% Memory)</text>
                        <rect x="0" y="30" width="660" height="32" rx="6" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
                        <rect x="0" y="30" width="82.5" height="32" rx="6" fill="#10B981" filter="url(#neon-glow)" />
                        <text x="41" y="51" class="node-bar-label bold">16 KB</text>
                        <text x="350" y="51" class="node-desc">Freed HBM Allocated to 3x Higher Batch Concurrency &amp; Fast Throughput</text>
                    </g>
                </svg>
            </div>
            <div class="schematic-footer-notes">
                <span>✦ <strong>Hardware Implication:</strong> Cracks the memory wall without sacrificing reasoning perplexity; self-hosting on commodity clusters.</span>
            </div>
        </div>
        """

    else:  # card-20261119-llama4 or fallback
        return """
        <div class="schematic-wrapper" data-schematic="cluster-fabric">
            <div class="schematic-header">
                <div class="schematic-title-group">
                    <span class="schematic-badge">INFRASTRUCTURE SCALE</span>
                    <h4 class="schematic-heading">100k+ Liquid-Cooled H100 GPU Cluster Spine Fabric</h4>
                </div>
                <div class="schematic-telemetry">
                    <span class="telemetry-pill good">Zero Downtime MTBF</span>
                    <span class="telemetry-pill">Fabric: RoCE v2 Spine</span>
                </div>
            </div>
            <div class="svg-schematic-canvas">
                <svg viewBox="0 0 740 180" fill="none" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
                    <g transform="translate(40, 20)">
                        <rect width="200" height="130" rx="8" class="node-box" />
                        <text x="100" y="24" class="node-title">COMPUTE PODS</text>
                        <text x="100" y="46" class="node-desc">100,000+ Liquid Cooled</text>
                        <text x="100" y="64" class="node-desc">Custom Thermal Racks</text>
                        <rect x="25" y="80" width="150" height="18" rx="4" fill="rgba(181,137,0,0.15)" />
                        <text x="100" y="93" class="node-stat">FP8 Mixed Precision</text>
                    </g>

                    <path d="M 240 85 L 290 85" class="flow-wire active-gold" />

                    <g transform="translate(290, 20)">
                        <rect width="180" height="130" rx="8" class="node-box accent-box" />
                        <text x="90" y="24" class="node-title good">SPINE NETWORK</text>
                        <text x="90" y="46" class="node-desc">Non-Blocking RoCE v2</text>
                        <text x="90" y="64" class="node-desc">Multi-Tier Leaf Fabric</text>
                        <rect x="20" y="80" width="140" height="18" rx="4" fill="rgba(16,185,129,0.15)" />
                        <text x="90" y="93" class="node-stat">3.2 Tbps Cross-Bisection</text>
                    </g>

                    <path d="M 470 85 L 520 85" class="flow-wire active-green" />

                    <g transform="translate(520, 20)">
                        <rect width="180" height="130" rx="8" class="node-box hit-box" />
                        <text x="90" y="24" class="node-title">FAULT TOLERANCE</text>
                        <text x="90" y="46" class="node-desc">Sub-Second Failover</text>
                        <text x="90" y="64" class="node-desc">Automated Straggler Kill</text>
                        <rect x="20" y="80" width="140" height="18" rx="4" fill="rgba(59,130,246,0.15)" />
                        <text x="90" y="93" class="node-stat">99.8% MFU Efficiency</text>
                    </g>
                </svg>
            </div>
            <div class="schematic-footer-notes">
                <span>✦ <strong>Commoditization Dynamic:</strong> Open model training at frontier capital scale establishes an open-weights baseline impossible for proprietary startups to beat on price.</span>
            </div>
        </div>
        """
