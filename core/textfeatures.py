"""
Deterministic text feature extraction for the For You feed (no AI / no ML models).

Every article is turned into a sparse feature set:
  * topics    – rule-based classification from keyword lexicons (+ the feed's own section)
  * keywords  – TF-IDF weighted, lightly-stemmed terms from title + summary
  * entities  – capitalised multi-word phrases (people, companies, places)
  * source    – the publisher

These features are what the recommender learns user affinities over.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Tuple

STOPWORDS = set("""
a about above after again against all also am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few
for from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him
himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll
she's should shouldn't so some such than that that's the their theirs them themselves then there there's these
they they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's whom why why's with won't would
wouldn't you you'd you'll you're you've your yours yourself yourselves says said say new news will just like get
gets got one two three first last year years week weeks day days today time now may might us via amid over after
make makes made take takes still back well even much many people report reports reported according latest live
updates update video watch read more could would told within without around since per across show shows set
""".split())

# Topic lexicons: stemmed tokens -> weight. Kept deliberately broad so that any
# general-news article lands in at least one bucket.
_RAW_LEXICON: Dict[str, Dict[str, float]] = {
    "AI": {w: 1.0 for w in "ai artificial intelligence openai anthropic gpt llm chatbot chatgpt claude gemini model neural machine learning deepmind nvidia agent copilot generative".split()},
    "Technology": {w: 1.0 for w in "tech software app apple google microsoft meta amazon iphone android startup chip semiconductor cloud cyber hack hacker data smartphone silicon developer browser internet gadget robot".split()},
    "Business": {w: 1.0 for w in "business company compani firm ceo profit revenue earn deal merger acquisit invest investor bank economi economy inflat tariff trade job jobs market retail sale price brand".split()},
    "Markets": {w: 1.0 for w in "stock stocks share shares nasdaq dow s&p index bond yield fed rate crypto bitcoin ether trader wall sensex nifty rally slump".split()},
    "Politics": {w: 1.0 for w in "elect election vote voter parliament congress senat senate presid president minist minister govern government polit polici policy law court suprem campaign democrat republican parti party bill".split()},
    "World": {w: 1.0 for w in "war ukrain ukraine russia china gaza israel iran un nato border refuge refugee militari military troop diplomat summit sanction peace ceasefir ceasefire protest".split()},
    "Science": {w: 1.0 for w in "scienc science scientist research studi study physic physics biolog biology chemistri fossil discov discovery genet dna quantum species lab experiment".split()},
    "Space": {w: 1.0 for w in "space nasa isro spacex rocket orbit moon mars satellit satellite astronaut launch telescop telescope galaxi galaxy planet asteroid".split()},
    "Health": {w: 1.0 for w in "health medic medical doctor hospit hospital diseas disease vaccin vaccine cancer drug patient covid virus mental nhs diet obes obesity therapi therapy".split()},
    "Climate": {w: 1.0 for w in "climat climate weather storm flood heat wildfir wildfire emiss emission carbon renew renewable solar energi energy environ environment pollut pollution hurrican hurricane".split()},
    "Sports": {w: 1.0 for w in "sport sports football soccer cricket tenni tennis nba nfl match team player coach leagu league cup goal score championship olymp olympics ipl f1 formula win".split()},
    "Entertainment": {w: 1.0 for w in "film movi movie music album singer actor actress celebr celebrity tv seri series netflix hollywood bollywood show award oscar concert star festiv festival".split()},
    "Gaming": {w: 1.0 for w in "game gamer gaming playstat playstation xbox nintendo switch steam esport esports console studio rpg shooter".split()},
}

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9&'\-]*[a-z0-9]|[a-z0-9]")
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_RE = re.compile(r"\b([A-Z][a-zA-Z0-9&\.\-]+(?:\s+(?:of|de|the|and)?\s*[A-Z][a-zA-Z0-9&\.\-]+){0,3})")
_SENTENCE_STARTERS = {"The", "A", "An", "In", "On", "At", "How", "Why", "What", "When", "Who", "This", "That",
                      "It", "As", "After", "Before", "Is", "Are", "Can", "New", "Watch", "Live", "Here", "We", "I"}


def strip_html(text: str) -> str:
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(_TAG_RE.sub(" ", text or ""))).strip()


def stem(word: str) -> str:
    """Tiny suffix-stripping stemmer (Porter-lite). Good enough to merge plural/tense variants."""
    if len(word) <= 3 or not word.isalpha():
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    for suf in ("ing", "ed"):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 4:
        return word[:-1]
    return word


# stem -> most recently seen surface form, for human-readable profile display
SURFACE: Dict[str, str] = {}


TOPIC_LEXICON: Dict[str, Dict[str, float]] = {
    topic: {stem(w.lower()): wt for w, wt in lex.items()} for topic, lex in _RAW_LEXICON.items()
}
TOPICS: List[str] = list(TOPIC_LEXICON.keys())


def tokenize(text: str) -> List[str]:
    out = []
    for tok in _TOKEN_RE.findall((text or "").lower()):
        tok = tok.strip("'-")
        if len(tok) < 2 or tok in STOPWORDS or tok.isdigit():
            continue
        st = stem(tok)
        if st not in SURFACE or len(tok) < len(SURFACE[st]):
            SURFACE[st] = tok
        out.append(st)
    return out


def display_term(term: str) -> str:
    return SURFACE.get(term, term)


def extract_entities(text: str, limit: int = 6) -> List[str]:
    found: Counter = Counter()
    for m in _ENTITY_RE.finditer(text or ""):
        phrase = m.group(1).strip(" .")
        words = phrase.split()
        if words and words[0] in _SENTENCE_STARTERS:
            words = words[1:]
        phrase = " ".join(words)
        if len(phrase) < 3 or phrase.lower() in STOPWORDS or phrase.isupper() and len(phrase) > 6:
            continue
        found[phrase] += 1
    return [p for p, _ in found.most_common(limit)]


def classify_topics(tokens: Iterable[str], feed_topic: str | None = None) -> Dict[str, float]:
    """Returns {topic: strength 0..1}. The feed's own section gets a strong prior."""
    counts = Counter(tokens)
    raw: Dict[str, float] = {}
    for topic, lex in TOPIC_LEXICON.items():
        s = sum(counts[t] * w for t, w in lex.items() if t in counts)
        if s > 0:
            raw[topic] = s
    if feed_topic in TOPIC_LEXICON:
        raw[feed_topic] = raw.get(feed_topic, 0) + 2.5
    if not raw:
        return {"World": 0.5}
    top = max(raw.values())
    scored = {t: round(v / top, 3) for t, v in raw.items() if v / top >= 0.34}
    return dict(sorted(scored.items(), key=lambda kv: -kv[1])[:3])


def term_frequencies(title: str, summary: str) -> Counter:
    # Title words count double: headlines carry most of the signal.
    return Counter(tokenize(title) * 2 + tokenize(summary))


def tfidf_keywords(tf: Counter, df: Dict[str, int], n_docs: int, limit: int = 12) -> Dict[str, float]:
    if not tf:
        return {}
    scores = {}
    max_tf = max(tf.values())
    for term, c in tf.items():
        idf = math.log((1 + n_docs) / (1 + df.get(term, 0))) + 1.0
        scores[term] = (0.5 + 0.5 * c / max_tf) * idf
    top = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
    norm = math.sqrt(sum(v * v for _, v in top)) or 1.0
    return {k: round(v / norm, 4) for k, v in top}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def estimate_read_seconds(word_count: int) -> float:
    # External article bodies are typically ~6x the RSS summary; floor at 45s.
    return max(45.0, min(600.0, word_count * 6 / 230 * 60))


def featurize(title: str, summary: str, feed_topic: str | None) -> Tuple[Counter, Dict[str, float], List[str]]:
    tf = term_frequencies(title, summary)
    topics = classify_topics(list(tf.elements()), feed_topic)
    entities = extract_entities(f"{title}. {summary}")
    return tf, topics, entities
