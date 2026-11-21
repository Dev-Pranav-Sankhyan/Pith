"""
Seed script that populates the Daily Tech Intelligence Brief with:
1. Today's 3 high-signal cards (AI & Developer Infrastructure beat).
2. The signature 'Not Included Today' filtered stories.
3. A seeded historical ledger of resolved and active predictions for Brier scoring & calibration.
"""

from core.models import (
    Card, RoleView, Prediction, Claim, HistoricalAnalogue,
    EvidenceLink, NotIncludedStory, DailyIssue
)
from core.db import Database
import datetime


def generate_seed_issue() -> DailyIssue:
    today_str = datetime.date.today().isoformat()

    card1 = Card(
        id="card-20261119-cache-cut",
        cluster_id="cluster-cache-pricing",
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline="Tier-1 API Providers Cut Context Caching Rates by 90%, Slashing Agent Run Costs",
        what_happened="Major AI providers cut the cost of reusing repeated text and instructions by up to 90%. Long conversations and multi-step agent workflows now run at a fraction of their previous bill.",
        why_it_matters="Apps that process long documents or run multi-step tasks become dramatically cheaper to operate today. However, structuring your prompts to claim these discounts deepens lock-in to that specific provider.",
        second_order=[
            "Agent frameworks prioritize static prompt architecture to maximize cache hit rates over dynamic assembly",
            "Switching costs rise as teams optimize backend memory layouts for specific provider KV-cache eviction policies",
            "Boutique single-model wrapper SaaS providers face intense margin compression unless they add workflow orchestration"
        ],
        signal_score=86.5,
        signal_level="High",
        signal_reason="Broad ecosystem impact (alters switching costs and platform dependencies)",
        confidence="High",
        action_type="DO",
        action_text="Refactor agent system prompts into static prefixes to trigger automatic cache hits and benchmark billing changes.",
        prediction=Prediction(
            id="pred-20261119-01",
            card_id="card-20261119-cache-cut",
            statement="By 30 June 2027, at least three leading open-source inference runtimes (vLLM, SGLang, TensorRT-LLM) natively support cross-session shared KV-cache eviction APIs matching commercial cloud standards.",
            probability=0.75,
            made_at=today_str,
            resolves_at="2027-06-30",
            resolution_criteria="Published release notes in official GitHub repositories documenting standardized shared KV-cache session eviction endpoint.",
            category="technology",
            status="open"
        ),
        historical_analogue=HistoricalAnalogue(
            analogue="Resembles AWS S3 Infrequent Access pricing tier introduced to anchor high-volume data lakes in 2015.",
            where_it_breaks="KV-cache requires GPU SRAM/HBM residency with microseconds eviction pressure, unlike cold object storage tiering."
        ),
        evidence_links=[
            EvidenceLink(
                title="API Pricing & Caching Architecture Update",
                url="https://platform.openai.com/docs/guides/prompt-caching",
                publisher="OpenAI Platform Documentation",
                tier="primary",
                quoted_span="cached input tokens receive an automatic 50% to 90% discount when hitting identical prompt prefixes"
            )
        ],
        claims=[
            Claim(
                text="Prompt caching read costs dropped by up to 90% for identical prefixes.",
                source_url="https://platform.openai.com/docs/guides/prompt-caching",
                quoted_span="cached input tokens receive an automatic 50% to 90% discount when hitting identical prompt prefixes",
                verified=True
            )
        ],
        role_views={
            "developer": RoleView(
                impact="Your prompt engineering shifts from dynamic template injection to strict static prefix isolation to maximize the 90% cache discount window.",
                action_type="DO",
                action_text="Audit prompt formatting utilities this week; split user state and variable data to the tail of the prompt sequence.",
                stakes="High"
            ),
            "founder": RoleView(
                impact="Gross margins on conversational and reasoning agent features improve by 30-45%, giving runway buffer or pricing leverage against competitors.",
                action_type="DO",
                action_text="Recalculate monthly per-active-user COGS and evaluate expanding agent search depth without raising customer subscription tiers.",
                stakes="High"
            ),
            "investor": RoleView(
                impact="Unit economics for token-heavy verticals (code generation, legal document parsing) stabilize; defensive moats shift from raw token volume to orchestration stickiness.",
                action_type="WATCH",
                action_text="Review portfolio company gross margins to verify teams have captured cache discounts rather than subsidizing inefficient prompt construction.",
                stakes="Medium"
            ),
            "everyday": RoleView(
                impact="The everyday AI tools you use just got 90% cheaper for companies to run. They can now remember much longer conversations and documents without crashing or cutting you off.",
                action_type="WATCH",
                action_text="Notice if your writing apps start handling 50-page PDFs without asking you to buy an expensive add-on.",
                stakes="Low"
            )
        },
        published_at=f"{today_str}T07:00:00Z"
    )

    card2 = Card(
        id="card-20261119-open-agent-protocol",
        cluster_id="cluster-oap-standard",
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline="Linux Foundation & CNCF Form Open Agent Protocol (OAP) to Unify Tool & MCP Interfaces",
        what_happened="The Linux Foundation and CNCF created an open, vendor-neutral standard for connecting AI models to external tools, databases, and enterprise software.",
        why_it_matters="Developers will no longer need to write bespoke connectors for every new AI vendor. Proprietary walled gardens lose their tollbooth, while open tools gain instant universal compatibility.",
        second_order=[
            "Database and SaaS vendors provide a single standard OAP endpoint rather than bespoke plugins for Claude, OpenAI, and Copilot",
            "Tool security and sandbox validation shift to standardized proxy layers at the network boundary",
            "Agent IDEs and terminal environments become plug-and-play interchangeable"
        ],
        signal_score=82.0,
        signal_level="High",
        signal_reason="Broad ecosystem impact (breaks from existing industry trajectory and eliminates proprietary lock-in)",
        confidence="High",
        action_type="DO",
        action_text="Adopt standardized JSON-RPC agent tool definitions rather than vendor-specific function schemas.",
        prediction=Prediction(
            id="pred-20261119-02",
            card_id="card-20261119-open-agent-protocol",
            statement="Within 30 days, at least two competing agent frameworks (e.g. LangChain, AutoGen) ship pull requests supporting the Open Agent Protocol standard.",
            probability=0.75,
            made_at=today_str,
            resolves_at="2026-12-20",
            resolution_criteria="Official pull request or release in langchain-ai or microsoft/autogen implementing conforming protocol client.",
            category="adoption",
            status="open"
        ),
        historical_analogue=HistoricalAnalogue(
            analogue="Mirrors the Container Network Interface (CNI) and Container Storage Interface (CSI) standardization in Kubernetes (2016-2018).",
            where_it_breaks="Agent tool execution carries dynamic state, schema drift, and authentication challenges far more complex than block volume mounting."
        ),
        evidence_links=[
            EvidenceLink(
                title="Linux Foundation Announces Open Agent Protocol Initiative",
                url="https://www.linuxfoundation.org/press/open-agent-protocol",
                publisher="Linux Foundation Press Release",
                tier="primary",
                quoted_span="working group will establish open governance for Model Context Protocol and cross-platform agent execution specs"
            )
        ],
        claims=[
            Claim(
                text="The Linux Foundation established a working group for open governance of agent context and execution protocols.",
                source_url="https://www.linuxfoundation.org/press/open-agent-protocol",
                quoted_span="working group will establish open governance for Model Context Protocol and cross-platform agent execution specs",
                verified=True
            )
        ],
        role_views={
            "developer": RoleView(
                impact="Eliminates the maintenance headache of writing and syncing multiple function calling schemas for separate LLM client SDKs.",
                action_type="DO",
                action_text="Standardize internal service interfaces on OAP tool definitions to ensure model neutrality.",
                stakes="Medium"
            ),
            "founder": RoleView(
                impact="Removes distribution barriers: your product can be exposed as an agent skill to any compliant client without bilateral partnership agreements.",
                action_type="WATCH",
                action_text="Track whether major client platforms (Claude Desktop, VS Code, OpenAI Operator) commit to upstream protocol conformance.",
                stakes="High"
            ),
            "investor": RoleView(
                impact="Commoditizes thin tool-routing middleware; value moves to privileged enterprise data access and verifiable agent execution sandboxes.",
                action_type="WATCH",
                action_text="Assess whether tooling portfolio companies rely on proprietary protocol lock-in that will be erased by CNCF standardization.",
                stakes="Medium"
            ),
            "everyday": RoleView(
                impact="Tech companies agreed to build a single universal plug—like USB-C, but for AI—so assistants can easily work with your calendar, email, and files without requiring 10 separate logins.",
                action_type="IGNORE",
                action_text="You don't have to configure anything; future app updates will automatically connect your tools smoothly.",
                stakes="Low"
            )
        },
        published_at=f"{today_str}T07:00:00Z"
    )

    card3 = Card(
        id="card-20261119-dualpipe-kernels",
        cluster_id="cluster-dualpipe-oss",
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline="DeepSeek Open-Sources DualPipe Kernels for Extreme Overlap Computation in Clustered Training",
        what_happened="DeepSeek released free open-source software kernels that overlap computing and data transfer during model training, eliminating cross-node network idle time.",
        why_it_matters="Smaller AI labs and cloud providers can now train frontier models at throughput speeds previously only achievable on multi-million dollar tech-giant networks.",
        second_order=[
            "Mid-market GPU cluster operators achieve 20-30% higher MFU (Model Flops Utilization) without InfiniBand upgrades",
            "PyTorch and Megatron-LM teams face immediate pressure to incorporate bidirectional pipeline scheduling natively",
            "Alternative silicon vendors (AMD ROCm, Intel Gaudi) gain accelerated parity on distributed pipeline training benchmarks"
        ],
        signal_score=78.5,
        signal_level="High",
        signal_reason="Broad ecosystem impact (breaks from existing industry trajectory via open-source release)",
        confidence="Medium",
        action_type="WATCH",
        action_text="Monitor PyTorch integration PRs and test throughput benchmarks on your distributed training stack.",
        prediction=Prediction(
            id="pred-20261119-03",
            card_id="card-20261119-dualpipe-kernels",
            statement="By 30 September 2027, the PyTorch core repository merges bidirectional pipeline parallelism scheduling inspired by DualPipe.",
            probability=0.65,
            made_at=today_str,
            resolves_at="2027-09-30",
            resolution_criteria="Merged commit in pytorch/pytorch implementing bidirectional pipeline parallel overlap schedule with benchmark documentation.",
            category="technology",
            status="open"
        ),
        historical_analogue=HistoricalAnalogue(
            analogue="Resembles Meta open-sourcing PyTorch FSDP (Fully Sharded Data Parallel) in 2021, democratizing ZeRO memory efficiency.",
            where_it_breaks="DualPipe focuses heavily on pipeline scheduling overlap under strict memory bounds rather than simple tensor sharding."
        ),
        evidence_links=[
            EvidenceLink(
                title="DeepSeek-V3 Technical Report & DualPipe Repository",
                url="https://github.com/deepseek-ai/DualPipe",
                publisher="DeepSeek GitHub",
                tier="primary",
                quoted_span="DualPipe achieves full computation and communication overlap across pipeline stages under Apache 2.0"
            )
        ],
        claims=[
            Claim(
                text="DualPipe open-sourced under Apache 2.0 enables full computation and communication overlap.",
                source_url="https://github.com/deepseek-ai/DualPipe",
                quoted_span="DualPipe achieves full computation and communication overlap across pipeline stages under Apache 2.0",
                verified=True
            )
        ],
        role_views={
            "developer": RoleView(
                impact="Distributed model fine-tuning and pre-training clusters can increase MFU throughput without hardware topology changes.",
                action_type="WATCH",
                action_text="Follow PyTorch distributed pull requests and review kernel benchmarks for your specific cluster interconnect.",
                stakes="Medium"
            ),
            "founder": RoleView(
                impact="Lowers the capital expenditure hurdle for training domain-specific proprietary models, narrowing the gap with frontier labs.",
                action_type="IGNORE",
                action_text="No immediate engineering intervention needed unless actively managing a multi-node GPU training cluster.",
                stakes="Low"
            ),
            "investor": RoleView(
                impact="High-cost proprietary interconnect networking moats face incremental erosion as clever software algorithms mitigate hardware bottlenecks.",
                action_type="WATCH",
                action_text="Track compute cost per token trajectory for open-source AI labs versus hyperscale frontier providers.",
                stakes="Low"
            ),
            "everyday": RoleView(
                impact="Researchers released free open software that lets smaller teams train AI models much faster, breaking Big Tech's monopoly on building smart computer brains.",
                action_type="IGNORE",
                action_text="No action needed. Expect more free, high-powered tools competing with big commercial chatbots.",
                stakes="Low"
            )
        },
        published_at=f"{today_str}T07:00:00Z"
    )

    card4 = Card(
        id="card-20261119-computer-use",
        cluster_id="cluster-os-computer-use",
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline="Anthropic Introduces Native OS Computer Use API, Standardizing Desktop Agent Automation",
        what_happened="Anthropic launched an API that allows AI models to directly view desktop screens, move mouse cursors, click buttons, and type text inside any computer application.",
        why_it_matters="Automating routine computer work no longer requires custom API integrations or fragile web scrapers. Software can now be operated by an AI agent just like a human team member.",
        second_order=[
            "Enterprise security teams mandate isolated sandbox hypervisors for agent environments to prevent unauthorized credential access",
            "Traditional robotic process automation (RPA) vendors face existential commoditization from native model-driven action spaces",
            "Synthetic UI training data generation explodes as agents self-record interaction trajectories"
        ],
        signal_score=84.0,
        signal_level="High",
        signal_reason="Broad ecosystem impact (alters switching costs and automation platform dependencies)",
        confidence="High",
        action_type="DO",
        action_text="Benchmark a prototype UI regression suite using vision-driven coordinate actions against existing Selenium/Playwright tests.",
        prediction=Prediction(
            id="pred-20261119-04",
            card_id="card-20261119-computer-use",
            statement="By 31 August 2027, at least two major browser vendors (Chromium, Firefox, WebKit) merge native virtualized OS agent permission sandboxes.",
            probability=0.65,
            made_at=today_str,
            resolves_at="2027-08-31",
            resolution_criteria="Official browser release notes document isolated agent sandbox profile with restricted credential access and synthetic input isolation.",
            category="adoption",
            status="open"
        ),
        historical_analogue=HistoricalAnalogue(
            analogue="Resembles the introduction of the WebDriver W3C standard in 2011, replacing ad-hoc browser automation hacks.",
            where_it_breaks="Computer Use relies on pixel-space visual reasoning rather than deterministic DOM element selectors."
        ),
        evidence_links=[
            EvidenceLink(
                title="Developing Computer Use with Claude 3.5 Sonnet",
                url="https://www.anthropic.com/news/3-5-models-and-computer-use",
                publisher="Anthropic Engineering",
                tier="primary",
                quoted_span="developers can direct Claude to use computers the way people do—by looking at a screen, moving a cursor, clicking buttons, and typing text"
            )
        ],
        claims=[
            Claim(
                text="API enables agents to look at screens, move cursors, click buttons, and type text across desktop applications.",
                source_url="https://www.anthropic.com/news/3-5-models-and-computer-use",
                quoted_span="developers can direct Claude to use computers the way people do—by looking at a screen, moving a cursor, clicking buttons, and typing text",
                verified=True
            )
        ],
        role_views={
            "developer": RoleView(
                impact="Enables end-to-end automation across legacy desktop software, CLI tools, and web apps that lack programmatic REST APIs.",
                action_type="DO",
                action_text="Build a test sandbox VM and evaluate coordinate latency on your internal testing workflow.",
                stakes="High"
            ),
            "founder": RoleView(
                impact="Lowers build costs for autonomous vertical agents (accounting, claims processing, legal onboarding) by bypassing API integration backlogs.",
                action_type="DO",
                action_text="Audit which customer onboarding tasks can be converted from manual operator labor to supervised OS agents.",
                stakes="High"
            ),
            "investor": RoleView(
                impact="Puts intense margin pressure on legacy RPA giants (UiPath, Automation Anywhere) whose seat-based licensing models depend on brittle workflow recorders.",
                action_type="WATCH",
                action_text="Assess exposure to workflow automation incumbents without foundational multi-modal agent roadmaps.",
                stakes="Medium"
            ),
            "everyday": RoleView(
                impact="Instead of you clicking and typing across 5 websites to complete boring tasks, an AI can now see your screen and move the mouse to fill out forms and book appointments for you.",
                action_type="TRY",
                action_text="Watch a 2-minute demo of computer-use automation to see if your repetitive office chores could be handed off.",
                stakes="Medium"
            )
        },
        published_at=f"{today_str}T07:00:00Z"
    )

    card5 = Card(
        id="card-20261119-mla-kernels",
        cluster_id="cluster-mla-compression",
        date=today_str,
        beat="AI & Developer Infrastructure",
        headline="vLLM & SGLang Merge Native Multi-Head Latent Attention (MLA), Cutting KV-Cache RAM by 70%",
        what_happened="Open-source AI engines vLLM and SGLang added a memory compression algorithm that cuts the RAM needed to serve long documents by 70%.",
        why_it_matters="Engineering teams can now host large AI models on half as many GPU servers, dramatically lowering monthly cloud hosting bills.",
        second_order=[
            "Enterprise self-hosting total cost of ownership (TCO) drops dramatically for long-document RAG pipelines",
            "Open-source model architectures standardize on low-rank latent compression over standard Multi-Query Attention (MQA)",
            "Memory bandwidth bottlenecks shift from KV-cache capacity to compute kernel execution overhead"
        ],
        signal_score=81.5,
        signal_level="High",
        signal_reason="Broad ecosystem impact (alters switching costs and deployment infrastructure requirements)",
        confidence="High",
        action_type="DO",
        action_text="Upgrade serving nodes to vLLM v0.7+ and benchmark GPU memory utilization under peak token generation load.",
        prediction=Prediction(
            id="pred-20261119-05",
            card_id="card-20261119-mla-kernels",
            statement="By 30 June 2027, at least three of the top five open-weight foundational model architectures adopt MLA as their default attention architecture.",
            probability=0.75,
            made_at=today_str,
            resolves_at="2027-06-30",
            resolution_criteria="Published model architecture papers on arXiv from major labs (e.g. Meta, Mistral, Qwen) explicitly specify Multi-Head Latent Attention in model specifications.",
            category="technology",
            status="open"
        ),
        historical_analogue=HistoricalAnalogue(
            analogue="Resembles the industry-wide shift from Multi-Head Attention (MHA) to Grouped-Query Attention (GQA) in 2023.",
            where_it_breaks="MLA compresses both keys and values into a shared low-rank latent vector rather than grouping head projections."
        ),
        evidence_links=[
            EvidenceLink(
                title="vLLM Multi-Head Latent Attention Implementation",
                url="https://github.com/vllm-project/vllm/pull/11245",
                publisher="vLLM GitHub",
                tier="primary",
                quoted_span="native MLA decoding kernels compress KV-cache memory footprints by over 70% with near-zero perplexity degradation"
            )
        ],
        claims=[
            Claim(
                text="Native MLA decoding kernels compress KV-cache memory footprints by over 70%.",
                source_url="https://github.com/vllm-project/vllm/pull/11245",
                quoted_span="native MLA decoding kernels compress KV-cache memory footprints by over 70% with near-zero perplexity degradation",
                verified=True
            )
        ],
        role_views={
            "developer": RoleView(
                impact="Enables hosting long-context models without out-of-memory crashes on resource-constrained development nodes.",
                action_type="DO",
                action_text="Test SGLang/vLLM MLA branch with your long-context RAG prompts to evaluate throughput gains.",
                stakes="Medium"
            ),
            "founder": RoleView(
                impact="Reduces inference hosting hardware requirements by up to 50%, directly cutting private cloud infrastructure bills.",
                action_type="WATCH",
                action_text="Review cloud GPU cluster capacity planning and defer hardware expansion until MLA benchmarks are verified.",
                stakes="High"
            ),
            "investor": RoleView(
                impact="Lowers infrastructure barriers for self-hosted sovereign AI, reducing enterprise reliance on closed hyper-scaler APIs.",
                action_type="WATCH",
                action_text="Assess whether private cloud AI infrastructure margins widen as serving software efficiency doubles.",
                stakes="Medium"
            ),
            "everyday": RoleView(
                impact="Engineers found a trick to shrink the memory needed to run AI by 70%, so apps won't slow down or show 'system overloaded' during busy hours.",
                action_type="WATCH",
                action_text="Enjoy faster, more reliable web tools without having to care about the computer memory under the hood.",
                stakes="Low"
            )
        },
        published_at=f"{today_str}T07:00:00Z"
    )

    not_included = [
        NotIncludedStory(
            headline="New Consumer Chatbot App Launch with Character Avatars",
            reason="Insufficient technical differentiation and negligible impact on developer infrastructure.",
            source_url="https://news.ycombinator.com"
        ),
        NotIncludedStory(
            headline="Minor GitHub Copilot UI Button Reorganization",
            reason="Cosmetic developer interface change with zero platform or architectural implications.",
            source_url="https://github.blog"
        ),
        NotIncludedStory(
            headline="Unverified Synthetic Benchmark Claim for Experimental Model",
            reason="Lacks primary methodology disclosure and independent peer reproducibility.",
            source_url="https://arxiv.org"
        )
    ]

    issue = DailyIssue(
        issue_id=f"issue-{today_str}",
        date=today_str,
        beat="AI & Developer Infrastructure",
        is_quiet_day=False,
        cards=[card1, card2, card3, card4, card5],
        not_included_today=not_included,
        published_at=f"{today_str}T07:00:00Z",
        meta={
            "candidate_clusters_evaluated": 178,
            "claims_verified_count": 5,
            "claims_dropped_count": 0,
            "editor_review_minutes": 16.0
        }
    )
    return issue


def seed_historical_predictions(db: Database):
    """
    Seeds a realistic historical track record of resolved predictions so that the
    Prediction Ledger, Brier Score, and Calibration chart have verifiable data to showcase.
    """
    historical = [
        # --- 30-Day Horizon Historical Predictions ---
        Prediction(
            id="hist-pred-01",
            statement="Within 30 days of release, provider pricing page confirms prompt caching with >75% discount.",
            probability=0.80,
            made_at="2026-03-01",
            resolves_at="2026-03-31",
            resolution_criteria="Official provider pricing page documents >75% reduction on cached input prompt tokens.",
            category="technology",
            status="correct",
            resolved_at="2026-03-25",
            evidence_url="https://platform.openai.com/docs/pricing",
            postmortem="Correct. Multiple frontier providers introduced prompt caching with up to 90% discount on cache hits."
        ),
        Prediction(
            id="hist-pred-06",
            statement="Within 30 days, major provider deprecates legacy v1 completions API in favor of chat/messages endpoint.",
            probability=0.90,
            made_at="2026-04-01",
            resolves_at="2026-05-01",
            resolution_criteria="Completions API endpoint decommissioned with 410 Gone status.",
            category="technology",
            status="correct",
            resolved_at="2026-04-28",
            evidence_url="https://platform.openai.com/docs/deprecations",
            postmortem="Correct. Legacy completions endpoint retired on schedule."
        ),
        Prediction(
            id="hist-pred-07",
            statement="Within 30 days of CUDA 12.8 release candidate, release notes officially deprecate Pascal GPU architecture.",
            probability=0.85,
            made_at="2026-05-01",
            resolves_at="2026-05-31",
            resolution_criteria="NVIDIA CUDA toolkit release documentation explicitly marks sm_60 and sm_61 as deprecated.",
            category="technology",
            status="correct",
            resolved_at="2026-05-22",
            evidence_url="https://developer.nvidia.com/cuda-toolkit/release-notes",
            postmortem="Correct. CUDA 12.8 formally marked Pascal compute architectures as deprecated."
        ),
        Prediction(
            id="hist-pred-08",
            statement="Within 30 days of public beta, Cloudflare Vectorize demonstrates p99 query latency under 15ms globally.",
            probability=0.75,
            made_at="2026-06-01",
            resolves_at="2026-07-01",
            resolution_criteria="Independent benchmark telemetry validates global p99 latency <15ms across 100k vector index.",
            category="technology",
            status="correct",
            resolved_at="2026-06-26",
            evidence_url="https://blog.cloudflare.com/vectorize-performance",
            postmortem="Correct. Edge-located vector indexes met sub-15ms p99 latency SLA."
        ),
        Prediction(
            id="hist-pred-11",
            statement="Within 30 days of launch, hosted Postgres provider announces per-gigabyte disk billing for HNSW vector indexes.",
            probability=0.55,
            made_at="2026-04-15",
            resolves_at="2026-05-15",
            resolution_criteria="Official billing docs show separate metered storage line-item for vector indexes.",
            category="market",
            status="wrong",
            resolved_at="2026-05-15",
            evidence_url="https://supabase.com/docs/guides/database/pricing",
            postmortem="Wrong. Provider bundled vector disk storage into standard compute tiers rather than unbundling index metering."
        ),

        # --- 90-Day Horizon Historical Predictions ---
        Prediction(
            id="hist-pred-02",
            statement="Within 90 days, a top-3 cloud provider enforces mandatory multi-factor hardware keys for root accounts.",
            probability=0.75,
            made_at="2026-02-15",
            resolves_at="2026-05-15",
            resolution_criteria="Official security bulletin mandating hardware FIDO2 keys for root account logins.",
            category="adoption",
            status="correct",
            resolved_at="2026-05-01",
            evidence_url="https://aws.amazon.com/blogs/security/mfa-fido-announcement",
            postmortem="Correct. AWS and Google Cloud both mandated FIDO2 MFA for organization root accounts."
        ),
        Prediction(
            id="hist-pred-03",
            statement="Within 90 days, EU AI Act guidelines mandate synthetic watermarking in all commercial code completion tools.",
            probability=0.60,
            made_at="2026-01-10",
            resolves_at="2026-04-10",
            resolution_criteria="Final EU AI Office regulatory text explicitly mandates synthetic watermarking in code tools.",
            category="market",
            status="wrong",
            resolved_at="2026-04-10",
            evidence_url="https://digital-strategy.ec.europa.eu/en/policies/ai-office",
            postmortem="Wrong. The AI Office retained watermarking for video/audio, but exempted standalone code completion tools."
        ),
        Prediction(
            id="hist-pred-04",
            statement="Within 90 days, PyTorch 2.5 includes native support for dynamic shape FP8 tensor cores.",
            probability=0.70,
            made_at="2026-02-01",
            resolves_at="2026-05-01",
            resolution_criteria="PyTorch release notes officially confirm dynamic FP8 execution in standard inductor.",
            category="technology",
            status="correct",
            resolved_at="2026-04-28",
            evidence_url="https://github.com/pytorch/pytorch/releases/tag/v2.5.0",
            postmortem="Correct. PyTorch 2.5 included native FP8 dynamic shape support."
        ),
        Prediction(
            id="hist-pred-05",
            statement="Within 90 days, an open-source Apache-2.0 weight model ranks in the top 5 on LMSYS Coding Leaderboard.",
            probability=0.65,
            made_at="2026-01-05",
            resolves_at="2026-04-05",
            resolution_criteria="LMSYS Coding Arena leaderboard public standings show an Apache-2.0 model in ranks 1 through 5.",
            category="adoption",
            status="correct",
            resolved_at="2026-03-20",
            evidence_url="https://chat.lmsys.org/?leaderboard",
            postmortem="Correct. DeepSeek-Coder-V2 achieved position #4 on the LMSYS coding leaderboard."
        ),
        Prediction(
            id="hist-pred-12",
            statement="Within 90 days of model release, quantized 405B parameter model achieves inference on single 8xH100 node.",
            probability=0.70,
            made_at="2026-03-10",
            resolves_at="2026-06-10",
            resolution_criteria="Reproducible GitHub repository demonstrates >15 tokens/sec per stream on 8xH100 using FP4/FP8.",
            category="technology",
            status="correct",
            resolved_at="2026-05-30",
            evidence_url="https://github.com/vllm-project/vllm/issues/6890",
            postmortem="Correct. FP4 tensor sharding allowed 405B parameter models to serve on single 8-GPU nodes."
        ),
        Prediction(
            id="hist-pred-13",
            statement="Within 90 days, leading frontier chat UI introduces 1-click artifact code deployment to live URLs.",
            probability=0.85,
            made_at="2026-02-20",
            resolves_at="2026-05-20",
            resolution_criteria="Chat interface includes native button to publish interactive React artifacts to unique public subdomains.",
            category="adoption",
            status="correct",
            resolved_at="2026-05-12",
            evidence_url="https://www.anthropic.com/news/artifacts-sharing",
            postmortem="Correct. Anthropic Artifacts sharing allowed direct one-click public URL previews."
        ),
        Prediction(
            id="hist-pred-14",
            statement="Within 90 days of TPU v5e general availability, cloud spot market discount exceeds 65% against on-demand.",
            probability=0.75,
            made_at="2026-01-15",
            resolves_at="2026-04-15",
            resolution_criteria="Google Cloud public pricing table records preemptible/spot TPU v5e pricing >65% below on-demand.",
            category="market",
            status="correct",
            resolved_at="2026-04-02",
            evidence_url="https://cloud.google.com/tpu/pricing",
            postmortem="Correct. Spot discounts on TPU v5e reached 70% in central regions."
        ),
        Prediction(
            id="hist-pred-16",
            statement="Within 90 days of version 1.2 release, Bun passes 100% of Node.js cluster module compatibility test suite.",
            probability=0.60,
            made_at="2026-03-01",
            resolves_at="2026-06-01",
            resolution_criteria="Bun compatibility tracker reports 100% pass on node:cluster standard conformance tests.",
            category="technology",
            status="wrong",
            resolved_at="2026-06-01",
            evidence_url="https://bun.sh/docs/runtime/nodejs-apis",
            postmortem="Wrong. Bun prioritized HTTP server multithreading over legacy process-forking cluster emulation."
        ),

        # --- 365-Day Horizon Historical Predictions ---
        Prediction(
            id="hist-pred-17",
            statement="Within 365 days of pgvector 0.7 release, at least two dedicated vector databases add native Postgres wire protocol compatibility.",
            probability=0.70,
            made_at="2025-10-01",
            resolves_at="2026-10-01",
            resolution_criteria="Official docs of at least 2 standalone vector DBs confirm psql client compatibility.",
            category="adoption",
            status="correct",
            resolved_at="2026-09-15",
            evidence_url="https://qdrant.tech/docs/interfaces/postgresql",
            postmortem="Correct. Qdrant and Milvus added Postgres protocol adaptors to prevent migration friction."
        ),
        Prediction(
            id="hist-pred-18",
            statement="Within 365 days, leading commercial coding assistant launches multi-file autonomous workspace refactoring in GA.",
            probability=0.85,
            made_at="2025-11-01",
            resolves_at="2026-11-01",
            resolution_criteria="Official release notes document multi-file diff generation and dependency-aware edits in production tiers.",
            category="technology",
            status="correct",
            resolved_at="2026-10-29",
            evidence_url="https://github.blog/news-insights/product-news/copilot-workspace-ga",
            postmortem="Correct. Multi-file edit capabilities reached general availability across major IDE assistants."
        ),
        Prediction(
            id="hist-pred-19",
            statement="Within 365 days, SWE-bench Verified replaces MMLU as the primary benchmark cited in frontier lab technical reports.",
            probability=0.80,
            made_at="2025-09-15",
            resolves_at="2026-09-15",
            resolution_criteria="Frontier model announcements cite SWE-bench resolution rates prominently on headline benchmark graphs.",
            category="market",
            status="correct",
            resolved_at="2026-08-30",
            evidence_url="https://swebench.com",
            postmortem="Correct. SWE-bench Verified became the industry de-facto metric for frontier agent capability."
        ),
        Prediction(
            id="hist-pred-20",
            statement="Within 365 days of initial reasoning model launch, production generation latency falls below 150ms per reasoning token.",
            probability=0.65,
            made_at="2025-10-15",
            resolves_at="2026-10-15",
            resolution_criteria="Benchmarking APIs confirm time-per-output-token <150ms on extended chain-of-thought generations.",
            category="technology",
            status="correct",
            resolved_at="2026-10-01",
            evidence_url="https://artificialanalysis.ai/models",
            postmortem="Correct. Speculative decoding and optimized KV cache compression reduced reasoning latency to 110ms/tok."
        ),
        Prediction(
            id="hist-pred-21",
            statement="Within 365 days, a European sovereign cloud consortium announces deployment of >10,000 high-end AI accelerators.",
            probability=0.75,
            made_at="2025-08-01",
            resolves_at="2026-08-01",
            resolution_criteria="Consortium press release and independent auditor verify commissioning of 10k+ clusters in EU datacenter.",
            category="market",
            status="correct",
            resolved_at="2026-07-15",
            evidence_url="https://ec.europa.eu/commission/presscorner/detail/en/ip_24_eu_ai_factories",
            postmortem="Correct. EuroHPC AI Factories initiative confirmed deployment of 16,000 GPU cluster."
        ),
        Prediction(
            id="hist-pred-22",
            statement="Within 365 days, US antitrust regulator issues binding consent decree prohibiting exclusive cloud compute credits for AI startups.",
            probability=0.55,
            made_at="2025-11-01",
            resolves_at="2026-11-01",
            resolution_criteria="FTC or DOJ public docket publishes formal signed consent decree barring compute-for-equity exclusivity.",
            category="market",
            status="wrong",
            resolved_at="2026-11-01",
            evidence_url="https://www.ftc.gov/news-events/news/press-releases/2026/11/ai-market-study-findings",
            postmortem="Wrong. The FTC published an extensive inquiry report detailing compute lock-in, but issued guidance rather than a binding consent decree."
        ),
        Prediction(
            id="hist-pred-23",
            statement="Within 30 days of release, PostgreSQL 17 includes native JSON_TABLE support conforming to SQL:2016.",
            probability=0.85,
            made_at="2026-09-01",
            resolves_at="2026-09-30",
            resolution_criteria="PostgreSQL official release notes confirm JSON_TABLE function in core query planner.",
            category="technology",
            status="correct",
            resolved_at="2026-09-26",
            evidence_url="https://www.postgresql.org/about/news/postgresql-17-released-2722/",
            postmortem="Correct. PostgreSQL 17 shipped JSON_TABLE in general availability."
        ),
        Prediction(
            id="hist-pred-24",
            statement="Within 90 days of launch, GitHub Copilot Chat exposes Claude 3.5 Sonnet to Enterprise users.",
            probability=0.80,
            made_at="2026-08-01",
            resolves_at="2026-11-01",
            resolution_criteria="GitHub Copilot settings allow selecting Anthropic Claude models for enterprise seats.",
            category="adoption",
            status="correct",
            resolved_at="2026-10-29",
            evidence_url="https://github.blog/news-insights/product-news/bringing-developer-choice-to-copilot/",
            postmortem="Correct. GitHub enabled multi-model choice including Claude 3.5 Sonnet for Enterprise seats."
        ),
    ]

    with db.get_connection() as conn:
        cursor = conn.cursor()
        for p in historical:
            cursor.execute("""
                INSERT OR REPLACE INTO predictions (
                    id, card_id, statement, probability, made_at, resolves_at,
                    resolution_criteria, category, status, resolved_at, evidence_url, postmortem
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.id, p.card_id, p.statement, p.probability, p.made_at, p.resolves_at,
                p.resolution_criteria, p.category, p.status, p.resolved_at, p.evidence_url, p.postmortem
            ))
        conn.commit()


def init_and_seed():
    db = Database("brief.sqlite3")
    issue = generate_seed_issue()
    db.save_issue(issue)
    seed_historical_predictions(db)
    print("Database seeded successfully with today's issue and historical predictions.")


if __name__ == "__main__":
    init_and_seed()
