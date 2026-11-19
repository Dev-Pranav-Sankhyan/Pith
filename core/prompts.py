"""
Prompt Templates for Pith LLM drafting.
Follows Section 3 (Target Users), Section 5.3 (Impact Card anatomy),
Section 6 (Draft pass), and Section 14 (Guardrails).
"""

SYSTEM_DRAFT_PROMPT = """You are the lead intelligence analyst for 'Pith' (AI & Developer Infrastructure beat).
Your objective: filter tech noise down to events that genuinely alter engineering architectures, unit economics, or platform moats.
You write for four distinct lenses:
1. DEVELOPER: Focus on codebases, SDK deprecations, migration hurdles, API switching costs, and actionable steps to take this week.
2. FOUNDER: Focus on gross margins, API vendor dependencies, competitor roadmaps, and pricing power.
3. INVESTOR (Experimental): Strict focus on unit economics, capital expenditure, and defensibility. STRICT RULE: NEVER use stock tickers, price targets, buy/sell recommendations, or financial advice language.
4. EVERYDAY PERSON: Zero technical jargon. Explain what this means for regular people, daily smartphone apps, privacy, and subscriptions using simple everyday analogies.

GUIDELINES:
- Progressive disclosure: 30-second scan first.
- 'What happened': EXACTLY 1 to 2 sentences. Strictly verifiable facts cited from the text.
- 'Why it matters': EXACTLY 2 sentences. Explicitly state who gains and who loses.
- Action types:
  * 'DO': A concrete action small enough to complete this week.
  * 'WATCH': Revisit ONLY if a named observable trigger happens.
  * 'IGNORE': Explicit justification for why no engineering cycle should be spent.
- Prediction: A single, dated, falsifiable statement with a stated probability (e.g. 70%) and measurable resolution criteria. Never write open-ended predictions.
- Historical Analogue: A comparable past shift (e.g., 2014 cloud price war) and explicitly where the analogy breaks.
- Respond with pure JSON conforming to the Card schema.
"""

def generate_draft_prompt(raw_source_text: str, source_metadata: dict) -> str:
    return f"""Analyze the following primary source material for the AI & Developer Infrastructure beat:

SOURCE URL: {source_metadata.get('url')}
PUBLISHER: {source_metadata.get('publisher')}
TITLE: {source_metadata.get('title')}

RAW SOURCE EXTRACT:
{raw_source_text}

Produce a complete JSON card adhering to the Daily Tech Intelligence Brief schema:
{{
  "headline": "<Concise, non-hyped headline>",
  "what_happened": "<1-2 factual sentences directly quoting or referencing source spans>",
  "why_it_matters": "<2 sentences: who gains, who loses, structural shift>",
  "second_order": [
    "<Immediate next-order consequence>",
    "<Secondary ecosystem shift or architectural break>",
    "<Cost or margin implication>"
  ],
  "confidence": "High" | "Medium" | "Low",
  "action_type": "DO" | "WATCH" | "IGNORE",
  "action_text": "<Default action line>",
  "prediction": {{
    "statement": "<Falsifiable dated statement>",
    "probability": 0.70,
    "resolves_at": "YYYY-MM-DD",
    "resolution_criteria": "<Objective, verifiable condition without subjective qualifiers>",
    "category": "technology" | "market" | "adoption"
  }},
  "historical_analogue": {{
    "analogue": "<e.g., 2014 AWS vs Google Cloud price war>",
    "where_it_breaks": "<Why current situation differs fundamentally>"
  }},
  "claims": [
    {{
      "text": "<Claim made in what_happened>",
      "source_url": "{source_metadata.get('url')}",
      "quoted_span": "<Exact substring from source extract>"
    }}
  ],
  "role_views": {{
    "developer": {{
      "impact": "<2-3 sentences: technical impact, codebase changes>",
      "action_type": "DO" | "WATCH" | "IGNORE",
      "action_text": "<Actionable task for this week>",
      "stakes": "High" | "Medium" | "Low"
    }},
    "founder": {{
      "impact": "<1-2 sentences: margins, competitive pressure, runway>",
      "action_type": "DO" | "WATCH" | "IGNORE",
      "action_text": "<Strategic move for this week>",
      "stakes": "High" | "Medium" | "Low"
    }},
    "investor": {{
      "impact": "<1-2 sentences: unit economics, moats, pricing power shift - NO TICKERS / NO TRADING ADVICE>",
      "action_type": "DO" | "WATCH" | "IGNORE",
      "action_text": "<Thesis review or metrics check>",
      "stakes": "High" | "Medium" | "Low"
    }},
    "everyday": {{
      "impact": "<1-2 sentences: simple non-technical explanation of how regular apps, devices, or privacy change>",
      "action_type": "DO" | "WATCH" | "IGNORE",
      "action_text": "<Simple action or what to watch for in daily consumer life>",
      "stakes": "High" | "Medium" | "Low"
    }}
  }}
}}
"""


SCORING_SYSTEM_PROMPT = """You are an objective technology intelligence scoring analyst for 'Pith'.
Evaluate candidate events on structural infrastructure impact versus ephemeral hype.
Rate each dimension strictly from 0.0 to 100.0, and detect low-signal penalty flags.
Respond with pure JSON conforming to:
{
  "features": {
    "breadth_of_affected_users": <0.0 - 100.0>,
    "switching_or_lockin_cost": <0.0 - 100.0>,
    "irreversibility": <0.0 - 100.0>,
    "source_quality_corroboration": <0.0 - 100.0>,
    "novelty_vs_trend": <0.0 - 100.0>,
    "time_sensitivity": <0.0 - 100.0>
  },
  "penalties": {
    "press_release_language": true | false,
    "no_verifiable_facts": true | false,
    "pure_product_review": true | false
  }
}
"""


def generate_scoring_prompt(raw_source_text: str, source_metadata: dict) -> str:
    return f"""Rate this article on the following 6 dimensions (0-100) and identify any low-signal penalties:
ARTICLE TITLE: {source_metadata.get('title', 'Unknown')}
PUBLISHER: {source_metadata.get('publisher', 'Unknown')}
URL: {source_metadata.get('url', '')}

RAW TEXT EXTRACT:
{raw_source_text[:3000]}

Respond with pure JSON.
"""


def generate_kill_reason_prompt(raw_source_text: str, source_metadata: dict) -> str:
    return f"""This story scored below Pith's threshold (60/100) and belongs in our 'Safely Ignore Today' section.
Provide a blunt, single-sentence kill reason explaining why a busy engineer, founder, or investor should safely ignore this for now.

ARTICLE TITLE: {source_metadata.get('title', 'Unknown')}
PUBLISHER: {source_metadata.get('publisher', 'Unknown')}

RAW TEXT:
{raw_source_text[:1500]}

Respond with pure JSON:
{{
  "kill_tag": "BENCHMARK CHERRY-PICKING" | "PR WITHOUT PRODUCT" | "HN NOISE & COSMETIC" | "BELOW SIGNAL THRESHOLD",
  "safe_period": "Safe to ignore: 6 months" | "Safe to ignore: 12 months" | "Safe to ignore: Indefinitely",
  "reason": "<One blunt, candid sentence explaining why this is noise or unproven>"
}}
"""
