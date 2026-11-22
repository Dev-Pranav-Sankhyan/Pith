"""
Interests from a connected account, used to warm up a reader's For You profile.

What is read (once, at sign-in; nothing is fetched later and no token is kept):
* GitHub: bio, company, location, your public repositories (language, topics, description) and
  the repositories you starred.
* X: bio and location, plus the accounts you follow when X's API tier allows it.
* Google and LinkedIn: only your locale's country (their sign-in shares little else). LinkedIn
  also adds a light nudge toward business news.

What is kept: the derived interests (topic / keyword / entity weights), an optional region, and
a short plain-language summary. No bio, repo list or follow list is stored.

Applying is idempotent: each sync stores the weights it applied, and the next sync applies only
the difference, so signing in again never inflates the profile. "Forget" subtracts them again.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from core import prefs as prefs_mod
from core.newsfeed import FOR_YOU_DB, _write_lock, connect, now_iso
from core.textfeatures import TOPICS, classify_topics, display_term, tokenize

TOPIC_SCALE = 2.6        # onboarding's picked topics are 3.0; imported ones sit just below
KEYWORD_SCALE = 1.4
ENTITY_WEIGHT = 1.1
MAX_KEYWORDS = 12
MAX_ENTITIES = 8

# GitHub language -> the word news stories would use.
LANGUAGE_TERMS = {
    "Python": "python", "Rust": "rust", "TypeScript": "typescript", "JavaScript": "javascript", "Java": "java",
    "Kotlin": "kotlin", "Swift": "swift", "Go": "golang", "Ruby": "ruby", "PHP": "php", "C#": "dotnet",
    "Jupyter Notebook": "machine learning", "Cuda": "cuda", "Solidity": "ethereum", "Dart": "flutter",
    "Scala": "scala", "Elixir": "elixir", "Haskell": "haskell", "Zig": "zig", "R": "statistics",
}
# GitHub organisations whose news coverage uses a different spelling.
ORG_ENTITIES = {
    "openai": "OpenAI", "anthropics": "Anthropic", "huggingface": "Hugging Face", "google": "Google",
    "google-deepmind": "DeepMind", "deepmind": "DeepMind", "microsoft": "Microsoft", "facebookresearch": "Meta",
    "meta-llama": "Meta", "facebook": "Meta", "nvidia": "Nvidia", "apple": "Apple", "aws": "Amazon",
    "awslabs": "Amazon", "vercel": "Vercel", "pytorch": "PyTorch", "tensorflow": "TensorFlow",
    "kubernetes": "Kubernetes", "rust-lang": "Rust", "golang": "Go", "nodejs": "Node.js", "docker": "Docker",
    "mistralai": "Mistral", "deepseek-ai": "DeepSeek", "ollama": "Ollama", "langchain-ai": "LangChain",
    "vllm-project": "vLLM", "apache": "Apache", "cloudflare": "Cloudflare", "stripe": "Stripe",
    "supabase": "Supabase", "tesla": "Tesla", "spacex": "SpaceX", "nasa": "NASA", "github": "GitHub",
}
# Words too generic to be an interest on their own.
GENERIC = set(tokenize(
    "app apps project projects simple tool tools library awesome list collection code repo repository "
    "personal website site config dotfiles template example examples demo test tests learning course "
    "notes based using built build written fast small minimal clone tutorial my your love working work "
    "engineer developer software stuff things https http www com io github twitter account official "
    "views own opinions tweets posting"))

COUNTRY_REGION: Dict[str, str] = {}
for _region, _codes in {
    "americas": "US CA MX BR AR CL CO PE UY VE EC BO PY CR PA DO GT HN SV NI JM TT PR CU",
    "uk": "GB UK",
    "india": "IN",
    "europe": "DE FR NL BE LU ES PT IT IE AT CH SE NO DK FI IS PL CZ SK HU RO BG GR HR SI RS BA ME MK AL "
              "EE LV LT UA MD BY CY MT",
    "asia": "CN JP KR SG HK TW ID MY TH VN PH BD PK LK NP KH MM MN AU NZ",
    "africa": "NG KE ZA GH EG MA TN DZ ET UG TZ RW SN CI CM ZM ZW BW NA AO MZ",
    "middle-east": "AE SA IL QA KW BH OM JO LB TR IR IQ",
}.items():
    for _c in _codes.split():
        COUNTRY_REGION[_c] = _region

PLACE_REGION = [
    ("india", "india"), ("bengaluru", "india"), ("bangalore", "india"), ("mumbai", "india"), ("delhi", "india"),
    ("hyderabad", "india"), ("pune", "india"), ("chennai", "india"), ("kolkata", "india"), ("gurgaon", "india"),
    ("noida", "india"), ("united kingdom", "uk"), ("uk", "uk"), ("england", "uk"), ("london", "uk"),
    ("scotland", "uk"), ("manchester", "uk"), ("wales", "uk"), ("usa", "americas"), ("united states", "americas"),
    ("san francisco", "americas"), ("sf", "americas"), ("bay area", "americas"), ("new york", "americas"),
    ("nyc", "americas"), ("seattle", "americas"), ("los angeles", "americas"), ("austin", "americas"),
    ("boston", "americas"), ("chicago", "americas"), ("canada", "americas"), ("toronto", "americas"),
    ("vancouver", "americas"), ("brazil", "americas"), ("são paulo", "americas"), ("mexico", "americas"),
    ("argentina", "americas"), ("germany", "europe"), ("berlin", "europe"), ("munich", "europe"),
    ("france", "europe"), ("paris", "europe"), ("netherlands", "europe"), ("amsterdam", "europe"),
    ("spain", "europe"), ("madrid", "europe"), ("barcelona", "europe"), ("italy", "europe"), ("sweden", "europe"),
    ("stockholm", "europe"), ("poland", "europe"), ("ireland", "europe"), ("dublin", "europe"),
    ("switzerland", "europe"), ("zurich", "europe"), ("portugal", "europe"), ("lisbon", "europe"),
    ("ukraine", "europe"), ("japan", "asia"), ("tokyo", "asia"), ("china", "asia"), ("beijing", "asia"),
    ("shanghai", "asia"), ("shenzhen", "asia"), ("singapore", "asia"), ("korea", "asia"), ("seoul", "asia"),
    ("indonesia", "asia"), ("jakarta", "asia"), ("vietnam", "asia"), ("philippines", "asia"),
    ("hong kong", "asia"), ("taiwan", "asia"), ("australia", "asia"), ("sydney", "asia"), ("melbourne", "asia"),
    ("nigeria", "africa"), ("lagos", "africa"), ("kenya", "africa"), ("nairobi", "africa"),
    ("south africa", "africa"), ("cape town", "africa"), ("ghana", "africa"), ("egypt", "africa"),
    ("cairo", "africa"), ("uae", "middle-east"), ("dubai", "middle-east"), ("abu dhabi", "middle-east"),
    ("israel", "middle-east"), ("tel aviv", "middle-east"), ("saudi", "middle-east"), ("riyadh", "middle-east"),
    ("qatar", "middle-east"), ("turkey", "middle-east"), ("istanbul", "middle-east"),
]

PROVIDER_NAMES = {"google": "Google", "github": "GitHub", "x": "X", "linkedin": "LinkedIn"}


# ---------------------------------------------------------------- derivation
def region_from_place(text: str) -> Optional[str]:
    low = (text or "").lower()
    for place, region in PLACE_REGION:
        if re.search(r"(?<![a-z])" + re.escape(place) + r"(?![a-z])", low):
            return region
    return None


def _corpus_keywords(db_path: str) -> set:
    try:
        from core.recommender import CORPUS
        corpus = CORPUS.get(db_path)
        out: set = set()
        for a in corpus.articles.values():
            out.update(a["keywords"].keys())
        return out
    except Exception:  # an empty or unreadable corpus just means "don't filter"
        return set()


def _topics_from(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    found = classify_topics(tokens)
    if found == {"World": 0.5} and "world" not in tokens:   # classify_topics' "nothing matched" fallback
        return {}
    return found


def derive(profile: Dict[str, Any], db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """Turns a provider profile into weights + a summary. Pure apart from reading the corpus vocabulary."""
    provider = profile.get("provider", "")
    data = profile.get("data") or {}
    texts: List[str] = []
    keyword_counts: Counter = Counter()
    entities: Counter = Counter()
    evidence: List[str] = []
    topics: Dict[str, float] = {}
    region: Optional[str] = None
    region_source = ""

    if provider == "github":
        repos = [r for r in data.get("repos", []) if not r.get("fork")]
        starred = data.get("starred", [])
        texts += [data.get("bio", ""), data.get("company", "")]
        langs: Counter = Counter(r["language"] for r in repos if r.get("language"))
        langs.update(r["language"] for r in starred if r.get("language"))
        for repo_list, weight in ((repos, 2), (starred, 1)):
            for r in repo_list:
                texts.append(r.get("description", ""))
                texts.append(" ".join(t.replace("-", " ") for t in r.get("topics", [])))
                for t in r.get("topics", []):
                    for tok in tokenize(t.replace("-", " ")):
                        keyword_counts[tok] += weight
        for lang, n in langs.most_common(4):
            term = LANGUAGE_TERMS.get(lang)
            if term:
                for tok in tokenize(term):
                    keyword_counts[tok] += 3 * n
        for r in starred:
            name = ORG_ENTITIES.get((r.get("owner") or "").lower())
            if name:
                entities[name] += 1
        company = (data.get("company") or "").strip().lstrip("@")
        if company and ORG_ENTITIES.get(company.lower()):
            entities[ORG_ENTITIES[company.lower()]] += 3
        if repos or starred:
            topics["Technology"] = 0.5          # active on GitHub: a floor, the text decides the rest
            top_langs = [l for l, _ in langs.most_common(3)]
            evidence.append(f"{len(repos)} of your repositories and {len(starred)} stars"
                            + (f", mostly {', '.join(top_langs)}" if top_langs else ""))
        if data.get("bio"):
            evidence.append("Your GitHub bio")
        region = region_from_place(data.get("location", ""))
        region_source = "your GitHub location"
    elif provider == "x":
        texts.append(data.get("bio", ""))
        for tag in re.findall(r"#(\w{3,30})", data.get("bio", "")):
            for tok in tokenize(re.sub(r"([a-z])([A-Z])", r"\1 \2", tag)):
                keyword_counts[tok] += 2
        following = data.get("following", [])
        for acct in following:
            texts.append(acct.get("description", ""))
            name = (acct.get("name") or "").strip()
            if 3 <= len(name) <= 40 and name[:1].isupper():
                entities[name] += 1
        if following:
            evidence.append(f"The {len(following)} accounts you follow on X")
        if data.get("bio"):
            evidence.append("Your X bio")
        region = region_from_place(data.get("location", ""))
        region_source = "your X location"
    elif provider in ("google", "linkedin"):
        country = (data.get("country") or "").upper()
        region = COUNTRY_REGION.get(country)
        region_source = f"your {PROVIDER_NAMES[provider]} locale ({country})" if country else ""
        if provider == "linkedin":
            topics["Business"] = 0.35
            evidence.append("Signing in with LinkedIn: a light nudge toward business news")

    tokens = [t for text in texts for t in tokenize(text)]
    for t, s in _topics_from(tokens).items():
        topics[t] = max(topics.get(t, 0.0), s)
    for tok in tokens:
        keyword_counts[tok] += 1

    # Terms the news already uses rank first; the rest still count, since they start mattering the
    # day a story mentions them.
    vocab = _corpus_keywords(db_path)
    candidates = [(k, n) for k, n in keyword_counts.most_common(80)
                  if k not in GENERIC and len(k) >= 3 and not k.isdigit() and n >= 2]
    ranked = sorted(candidates, key=lambda kn: (not vocab or kn[0] in vocab, kn[1]), reverse=True)[:MAX_KEYWORDS]
    top_n = ranked[0][1] if ranked else 1
    keywords = {k: round(KEYWORD_SCALE * max(0.35, n / top_n), 3) for k, n in ranked}

    weights = {
        "topic": {t: round(TOPIC_SCALE * s, 3) for t, s in topics.items() if t in TOPICS and s > 0},
        "keyword": keywords,
        "entity": {e: ENTITY_WEIGHT for e, _ in entities.most_common(MAX_ENTITIES)},
    }
    if region and region_source:
        evidence.append(f"Region from {region_source}")
    notes = list(data.get("notes") or [])
    summary = {
        "topics": sorted(weights["topic"], key=lambda t: -weights["topic"][t]),
        "keywords": [display_term(k) for k in keywords],
        "entities": list(weights["entity"]),
        "region": region,
        "evidence": evidence,
        "notes": notes,
    }
    return {"weights": weights, "region": region, "summary": summary}


# ---------------------------------------------------------------- applying
def _diff(new: Dict[str, Dict[str, float]], old: Dict[str, Dict[str, float]]) -> List[Tuple[str, str, float]]:
    out = []
    for kind in set(new) | set(old):
        n, o = new.get(kind, {}), old.get(kind, {})
        for key in set(n) | set(o):
            delta = n.get(key, 0.0) - o.get(key, 0.0)
            if abs(delta) > 1e-6:
                out.append((kind, key, delta))
    return out


def _explicit_region(conn, user_id: int) -> Optional[str]:
    row = conn.execute("SELECT value FROM user_prefs WHERE user_id=? AND key='region'", (user_id,)).fetchone()
    return json.loads(row["value"]) if row and row["value"] else None


def sync(user_id: int, profile: Dict[str, Any], db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """Derives and applies this provider's interests for the reader. Safe to call on every sign-in."""
    from core.recommender import Recommender
    derived = derive(profile, db_path)
    provider = profile["provider"]
    rec = Recommender(db_path)
    with _write_lock, connect(db_path) as conn:
        row = conn.execute("SELECT applied_json, summary_json FROM social_signals WHERE user_id=? AND provider=?",
                           (user_id, provider)).fetchone()
        old = json.loads(row["applied_json"]) if row else {}
        old_summary = json.loads(row["summary_json"]) if row else {}
        old_weights = {k: v for k, v in old.items() if k in ("topic", "keyword", "entity")}
        updates = _diff(derived["weights"], old_weights)
        rec._apply(conn, user_id, updates)
        # Region: only filled in when the reader hasn't chosen one, and only ever replaced or
        # removed later if it is still the value this import set.
        ours = old_summary.get("region") if old.get("region_set") else None
        current = _explicit_region(conn, user_id)
        region = derived["region"]
        if region and (current is None or current == ours):
            conn.execute("""INSERT INTO user_prefs (user_id, key, value, updated_at) VALUES (?, 'region', ?, ?)
                            ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                         (user_id, json.dumps(region), now_iso()))
            region_set = True
        elif ours and current == ours:
            region, region_set = ours, True
        else:
            region_set = False
        applied = dict(derived["weights"], region_set=region_set)
        summary = dict(derived["summary"], region=region, region_applied=region_set)
        conn.execute("""INSERT INTO social_signals (user_id, provider, applied_json, summary_json, updated_at)
                        VALUES (?,?,?,?,?) ON CONFLICT(user_id, provider) DO UPDATE SET
                        applied_json=excluded.applied_json, summary_json=excluded.summary_json,
                        updated_at=excluded.updated_at""",
                     (user_id, provider, json.dumps(applied), json.dumps(summary), now_iso()))
        if updates:
            conn.execute("INSERT INTO events (user_id, kind, meta, created_at) VALUES (?,?,?,?)",
                         (user_id, "social_import", json.dumps({"provider": provider, "changes": len(updates)}),
                          now_iso()))
    return summary


def forget(user_id: int, provider: str, db_path: str = FOR_YOU_DB) -> bool:
    """Subtracts what this provider contributed and deletes the record. The reader's own reading stays."""
    from core.recommender import Recommender
    rec = Recommender(db_path)
    with _write_lock, connect(db_path) as conn:
        row = conn.execute("SELECT applied_json, summary_json FROM social_signals WHERE user_id=? AND provider=?",
                           (user_id, provider)).fetchone()
        if not row:
            return False
        applied = json.loads(row["applied_json"])
        summary = json.loads(row["summary_json"])
        rec._apply(conn, user_id, _diff({}, {k: v for k, v in applied.items() if k in ("topic", "keyword", "entity")}))
        if applied.get("region_set") and _explicit_region(conn, user_id) == summary.get("region"):
            conn.execute("DELETE FROM user_prefs WHERE user_id=? AND key='region'", (user_id,))
        conn.execute("DELETE FROM social_signals WHERE user_id=? AND provider=?", (user_id, provider))
    return True


def summaries(user_id: int, db_path: str = FOR_YOU_DB) -> Dict[str, Dict[str, Any]]:
    with connect(db_path) as conn:
        return {r["provider"]: dict(json.loads(r["summary_json"]), updated_at=r["updated_at"])
                for r in conn.execute("SELECT provider, summary_json, updated_at FROM social_signals WHERE user_id=?",
                                      (user_id,))}


def imported_topics(user_id: int, db_path: str = FOR_YOU_DB) -> List[str]:
    """Topics from all connected accounts, strongest first: used to pre-fill onboarding."""
    seen: Dict[str, int] = {}
    for s in summaries(user_id, db_path).values():
        for i, t in enumerate(s.get("topics", [])):
            seen[t] = min(seen.get(t, 99), i)
    return sorted(seen, key=lambda t: seen[t])


def connections(user_id: int, db_path: str = FOR_YOU_DB) -> Dict[str, Any]:
    """What the For You sidebar shows: each connected account, what it contributed, what can be added."""
    from core import oauth
    sums = summaries(user_id, db_path)
    linked = oauth.identities(user_id, db_path)
    can_drop = len(linked) > 1 or oauth.has_password(user_id, db_path)
    out = []
    for ident in linked:
        p = ident["provider"]
        out.append({"provider": p, "name": PROVIDER_NAMES.get(p, p), "handle": ident["handle"],
                    "display_name": ident["display_name"], "connected_at": ident["created_at"],
                    "imported": sums.get(p), "can_disconnect": can_drop})
    connected = {i["provider"] for i in linked}
    available = [p for p in oauth.provider_list() if p["configured"] and p["id"] not in connected]
    return {"accounts": out, "available": available}
