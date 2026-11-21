"""
Offline demo articles so the For You feed works without network access
(sandboxed dev, tests, first boot on a plane). They are clearly flagged
`is_demo` in the UI and are deleted automatically the first time a live
RSS refresh succeeds. Content is synthetic, not real reporting.
"""

from __future__ import annotations

import datetime as dt
import random
import re
from typing import Dict, List

from core.newsfeed import FOR_YOU_DB, store_articles

_TEMPLATES: Dict[str, List[str]] = {
    "AI": [
        "{co} releases open-weight language model that rivals frontier systems on coding",
        "Researchers show small AI models can match larger ones with better training data",
        "{co} adds AI agent that can book travel and fill out forms for users",
        "Regulators publish draft rules for testing generative AI before release",
        "Chip shortage eases as {chip} ramps production of AI accelerators",
        "Study finds AI coding assistants speed up junior developers the most",
    ],
    "Technology": [
        "{co} unveils new smartphone with week-long battery life",
        "Major browser update blocks third-party tracking cookies by default",
        "Cybersecurity firm warns of ransomware campaign targeting hospitals",
        "{co} announces cloud price cuts as data centre competition heats up",
        "Open source developers push back on new software licence changes",
        "Startup builds repairable laptop with swappable chips",
    ],
    "Business": [
        "{co} shares jump after quarterly revenue beats expectations",
        "Retail sales slow as shoppers cut back ahead of the holidays",
        "Airline merger approved after regulators demand route sell-offs",
        "Central bank holds interest rates steady, signals cuts next year",
        "Electric vehicle maker cuts prices to defend market share",
        "Small businesses report hiring rebound in services sector",
    ],
    "Markets": [
        "Stocks rally to record high as inflation data cools",
        "Bitcoin swings sharply as traders weigh new crypto regulation",
        "Bond yields fall after weaker-than-expected jobs report",
        "Sensex and Nifty climb as foreign investors return to Indian equities",
        "Oil prices slide on signs of rising global supply",
    ],
    "Politics": [
        "Parliament passes landmark data protection bill after long debate",
        "Election campaign enters final week with candidates neck and neck",
        "Supreme Court to hear challenge to new voting law",
        "Government unveils budget focused on infrastructure and jobs",
        "Coalition talks stall over disagreement on tax policy",
    ],
    "World": [
        "Ceasefire talks resume as diplomats push for lasting peace deal",
        "Leaders gather for climate and trade summit amid tensions",
        "UN warns of food shortages as conflict disrupts grain exports",
        "Thousands protest in capital over rising cost of living",
        "NATO allies agree to boost defence spending targets",
    ],
    "Science": [
        "Scientists discover new species of deep-sea fish near volcanic vents",
        "Quantum computer completes calculation beyond classical reach, study claims",
        "Fossil find rewrites timeline of early bird evolution",
        "Gene therapy restores partial sight in clinical trial",
        "Physicists measure gravity at smallest scale yet",
    ],
    "Space": [
        "NASA sets launch date for crewed lunar flyby mission",
        "ISRO successfully tests reusable rocket landing",
        "Telescope spots water vapour in atmosphere of distant planet",
        "SpaceX launches batch of satellites for global broadband",
        "Asteroid sample reveals building blocks of life",
    ],
    "Health": [
        "New vaccine shows strong protection against seasonal flu strains",
        "Doctors warn of rising cases of mental health issues among teenagers",
        "Study links ultra-processed food to higher heart disease risk",
        "Hospital waiting lists fall for first time in three years",
        "Weight-loss drug approved for wider use by regulator",
    ],
    "Climate": [
        "Record heatwave pushes power grids to the limit",
        "Solar and wind overtake coal in global electricity generation",
        "Floods displace thousands after week of heavy monsoon rain",
        "Carbon emissions from aviation return to pre-pandemic levels",
        "Wildfire season starts early as drought grips region",
    ],
    "Sports": [
        "India beat Australia in thrilling cricket final",
        "Champions League: late goal sends holders into quarter-finals",
        "Tennis star wins fifth grand slam title in straight sets",
        "IPL auction sees record bid for young fast bowler",
        "Formula 1 title race goes down to final round",
        "NBA rookie scores 50 points in breakout game",
    ],
    "Entertainment": [
        "Blockbuster sequel breaks opening weekend box office record",
        "Streaming service announces price rise and ad-supported plan",
        "Bollywood film becomes highest-grossing release of the year",
        "Music festival lineup headlined by reunion of iconic band",
        "Award season kicks off with surprise nominations",
    ],
    "Gaming": [
        "Nintendo reveals release date for next console",
        "Indie game tops Steam charts after viral launch",
        "PlayStation studio announces open-world RPG sequel",
        "Esports league signs record broadcast deal",
        "Xbox brings cloud gaming to more countries",
    ],
}
_FILL = {"co": ["Apple", "Google", "Microsoft", "Meta", "Amazon", "Samsung", "OpenAI", "Anthropic", "Nvidia", "Infosys"],
         "chip": ["TSMC", "Nvidia", "Samsung", "Intel"]}
_PUBLISHERS = ["Demo Wire", "Demo Daily", "Demo Times", "Demo Ledger", "Demo Post"]

_SUMMARY = ("Demo article for offline testing of Pith For You. {title}. Analysts and readers are watching "
            "closely to see what happens next and what it means for the wider {topic_l} landscape.")


def build_demo_articles(seed: int = 7) -> List[dict]:
    rng = random.Random(seed)
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for topic, templates in _TEMPLATES.items():
        for i, tpl in enumerate(templates):
            title = tpl.format(**{k: rng.choice(v) for k, v in _FILL.items()})
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]
            out.append({
                "title": title,
                "url": f"https://example.com/pith-demo/{topic.lower()}/{slug}",
                "summary": _SUMMARY.format(title=title, topic_l=topic.lower()),
                "publisher": rng.choice(_PUBLISHERS),
                "feed_id": "demo",
                "feed_topic": topic,
                "image_url": None,
                "published_at": (now - dt.timedelta(minutes=rng.randint(5, 60 * 40))).isoformat(timespec="seconds"),
            })
    return out


def seed_demo(db_path: str = FOR_YOU_DB) -> int:
    return store_articles(build_demo_articles(), db_path, is_demo=True)
