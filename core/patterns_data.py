"""
Curated Pattern Library for Daily Tech Intelligence Brief.
Follows Section 7 (Behavioral Psychology and Pattern Matching).
"""

from typing import List, Dict, Any


PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "pattern-commoditisation-cascade",
        "name": "The Commoditisation Cascade",
        "category": "Platform Economics",
        "tag": "PLATFORM ECONOMICS",
        "summary": "Open-weight models match 90% of closed frontier capability at 10% the operating cost, triggering a price collapse that erodes thin wrapper margins and pushes value to proprietary data and execution.",
        "dynamics": "Initial frontier monopoly prices create massive margin incentives for open replication. Once permissive architectures reach 'good enough' utility for 80% of enterprise tasks, proprietary API pricing power breaks. Infrastructure providers are forced to discount inference or bundle it into platform subscriptions.",
        "cases": [
            {
                "title": "Linux vs. Proprietary Unix (1995–2003)",
                "detail": "Sun Microsystems, SGI, and HP commanded 70%+ gross margins on custom Unix servers. Once open-source Linux achieved stability on commodity x86 Intel hardware, proprietary server margins collapsed permanently."
            },
            {
                "title": "Stable Diffusion vs. Closed Image APIs (2022–2024)",
                "detail": "Midjourney and OpenAI initially controlled image generation pricing. The release of open-weight Stable Diffusion and Flux forced hosted API pricing down by >85% within 18 months, shifting defensibility to workflow UI and canvas integration."
            }
        ],
        "base_rate": "In 78% of developer infrastructure categories, permissive open alternatives cap closed API gross margins below 45% within 3 years of first parity release.",
        "cognitive_bias": "Moat Mirage & Recency Bias: Mistaking an incumbent's 6-month research lead for an enduring structural barrier to entry.",
        "failure_mode": "Building a venture-scale startup on a single prompt or thin routing wrapper without proprietary execution loops or enterprise data lock-in.",
        "related_card_ids": ["card-20261119-cache-cut", "card-20261119-mla-kernels"]
    },
    {
        "id": "pattern-standards-war",
        "name": "The Standards War & CNI Moment",
        "category": "Open Source & Standards",
        "tag": "OPEN SOURCE & STANDARDS",
        "summary": "Competing vendors unite under a neutral foundation (e.g., CNCF, Linux Foundation) to standardize an interface, neutralizing a dominant single-vendor tollbooth.",
        "dynamics": "When a platform leader begins leveraging proprietary connector protocols to extract ecosystem tolls, competing cloud providers and developer toolmakers form an open consortium. The resulting open standard commoditizes the connector layer and shifts value to infrastructure reliability and execution sandboxes.",
        "cases": [
            {
                "title": "Container Network Interface (CNI, 2016–2018)",
                "detail": "Docker attempted to capture the container ecosystem by bundling proprietary libnetwork and Docker Swarm. Competitors united around CNCF Kubernetes and the CNI/CSI standards, rendering proprietary container networking obsolete."
            },
            {
                "title": "Language Server Protocol (LSP, 2016)",
                "detail": "Microsoft and Red Hat standardized editor integrations via JSON-RPC. Instead of building M×N bespoke compiler plugins for every IDE, developers adopted a single protocol, commoditizing editor language parsing."
            }
        ],
        "base_rate": "When at least 3 tier-1 rivals back a vendor-neutral protocol under independent governance, proprietary protocols lose developer mindshare within 14 months in 82% of tracked cases.",
        "cognitive_bias": "Incumbent Inevitability: Assuming a first-mover's proprietary connector format is insurmountable simply because it launched first.",
        "failure_mode": "Spending heavy engineering cycles maintaining bilateral custom connectors rather than adopting the upstream neutral specification.",
        "related_card_ids": ["card-20261119-open-agent-protocol"]
    },
    {
        "id": "pattern-price-war-compression",
        "name": "Price-War Margin Compression",
        "category": "Platform Economics",
        "tag": "PLATFORM ECONOMICS",
        "summary": "Hyperscalers with massive balance sheets slash marginal costs on compute primitives to near-zero, squeezing venture-backed challenger clouds and anchoring customer lock-in to their memory clusters.",
        "dynamics": "Cloud hyper-scalers treat low-level compute and caching as loss leaders to capture high-margin enterprise data residency and platform orchestration. Challenger clouds unable to cross-subsidize infrastructure face rapid gross margin compression.",
        "cases": [
            {
                "title": "AWS vs. Google Cloud Price War (2014–2016)",
                "detail": "Sequential price cuts of 30% to 50% across virtual machines and memory instances forced second-tier hosting providers out of business and consolidated 80%+ of cloud spend into AWS, Azure, and GCP."
            },
            {
                "title": "S3 Infrequent Access & Tiered Storage (2015)",
                "detail": "Cloud providers slashed pricing on cold bytes to below raw hardware depreciation rates, disincentivizing customers from running on-premise storage arrays."
            }
        ],
        "base_rate": "Frontier provider price cuts exceeding 40% are matched by at least two major competitors within 180 days in 70% of historical cloud price adjustments.",
        "cognitive_bias": "Static Margin Fallacy: Modeling multi-year company valuation on current token pricing without forecasting aggressive provider deflation.",
        "failure_mode": "Passing provider price drops directly to customers without preserving margin buffers or optimizing prompt prefix architecture.",
        "related_card_ids": ["card-20261119-cache-cut"]
    },
    {
        "id": "pattern-relicensing-trap",
        "name": "The Relicensing & Moat Pivot",
        "category": "Open Source & Standards",
        "tag": "OPEN SOURCE & STANDARDS",
        "summary": "Permissive open-source infrastructure projects face revenue capture from cloud giants, pivot to restrictive source-available licenses (BSL, SSPL), and provoke immediate community forks.",
        "dynamics": "Single-vendor commercial open-source companies struggle to monetize against hyper-scaler managed offerings. Stewards adopt restrictive source-available licenses to force commercial licensing, creating an immediate opportunity for cloud rivals and community consortiums to fork the permissive codebase.",
        "cases": [
            {
                "title": "Elasticsearch to SSPL (2021)",
                "detail": "Elastic switched from Apache 2.0 to SSPL to block AWS. Amazon responded by creating the OpenSearch fork under the Apache license, permanently splitting enterprise mindshare and plugin ecosystems."
            },
            {
                "title": "Terraform to BSL (2023)",
                "detail": "HashiCorp's transition to BSL sparked the OpenTofu fork under the Linux Foundation within 30 days. OpenTofu quickly secured majority corporate backing for open infrastructure deployment."
            }
        ],
        "base_rate": "Within 24 months of relicensing, a community-governed neutral fork captures over 50% of grassroots developer mindshare in 65% of tracked infrastructure cases.",
        "cognitive_bias": "Sunk-Cost Trap: Staying locked into a relicensed vendor's stack due to prior investment, ignoring the rising legal and migration costs.",
        "failure_mode": "Building deep proprietary architectural hooks into single-vendor commercial open-source software without evaluating fork durability.",
        "related_card_ids": []
    },
    {
        "id": "pattern-platform-squeeze",
        "name": "The Platform Squeeze & Sherlocking",
        "category": "Platform Economics",
        "tag": "PLATFORM ECONOMICS",
        "summary": "A platform cultivates an active ecosystem of third-party builders, reaches market dominance, and then systematically restricts API access or ships native clones of the most successful third-party tools.",
        "dynamics": "In early phases, platforms offer generous free APIs and developer grants to build ecosystem gravity. Once user and data lock-in are achieved, the platform absorbs high-demand utility apps into core product tiers or imposes steep API usage tollbooths.",
        "cases": [
            {
                "title": "Apple 'Sherlocking' (2000s–Present)",
                "detail": "Apple systematically incorporated third-party developer utilities (Watson search, f.lux night shift, Tile tracking, Shazam) directly into macOS and iOS system software, erasing third-party business models overnight."
            },
            {
                "title": "Twitter API Paywall (2023)",
                "detail": "Overnight price hikes from free/cheap tiers to $42,000/month wiped out an entire ecosystem of analytics, research, and scheduling software that had spent a decade building Twitter's developer mindshare."
            }
        ],
        "base_rate": "Platforms with >60% category market share clone or restrict top-10 ecosystem utility tools within 3 years of feature maturity (85% historical incidence).",
        "cognitive_bias": "Platform Partnership Illusion: Mistaking a partner marketing badge or early API grant for long-term strategic safety.",
        "failure_mode": "Failing to build proprietary data moats or direct user distribution, leaving your product vulnerable to a single API deprecation notice.",
        "related_card_ids": ["card-20261119-computer-use"]
    },
    {
        "id": "pattern-codesign-bottleneck",
        "name": "The Hardware/Software Co-Design Bottleneck",
        "category": "Architecture & Silicon",
        "tag": "ARCHITECTURE & SILICON",
        "summary": "When hardware interconnects become the primary cost bottleneck, algorithmic kernel breakthroughs (FlashAttention, DualPipe, MLA) temporarily narrow the performance moat of closed hyper-scalers.",
        "dynamics": "Hardware scaling encounters physical thermal and bandwidth walls (HBM capacity, memory bus width, cross-node communication). Software engineers rewrite execution kernels to overlap compute with communication or compress attention states, yielding 2x to 4x efficiency gains on existing commodity hardware.",
        "cases": [
            {
                "title": "Tri Dao FlashAttention (2022–2023)",
                "detail": "Algorithmic IO-awareness cut attention memory from quadratic O(N²) to linear O(N), enabling standard GPU nodes to process long-context sequences without hardware clustering upgrades."
            },
            {
                "title": "DeepSeek Multi-Head Latent Attention (MLA, 2024)",
                "detail": "Projecting key-value matrices into low-rank latent vectors compressed KV-cache memory footprints by over 70%, allowing high-throughput inference on commodity GPU clusters."
            }
        ],
        "base_rate": "Algorithmic and kernel optimizations provide a 2x to 4x throughput improvement on existing silicon before the next hardware fabrication generation reaches scale (90% historical frequency).",
        "cognitive_bias": "Hardware Determinism: Assuming compute dominance is purely a function of raw GPU inventory rather than kernel-level scheduling and attention compression.",
        "failure_mode": "Over-committing to multi-year hardware leases before benchmarking modern low-rank attention and pipeline-overlap runtime libraries.",
        "related_card_ids": ["card-20261119-dualpipe-kernels", "card-20261119-mla-kernels"]
    }
]
