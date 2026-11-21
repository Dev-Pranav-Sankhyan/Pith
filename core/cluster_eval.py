"""Pairwise precision/recall/F1 of ClusterEngine against a hand-labelled set."""

import json
from collections import Counter
from itertools import combinations
from typing import Dict, List

from core.textfeatures import featurize, tfidf_keywords


def featurize_articles(items: List[Dict]) -> List[Dict]:
    """Turn raw {id,title,summary,...} dicts into the shape ClusterEngine expects."""
    tfs = []
    df: Counter = Counter()
    for it in items:
        tf, topics, entities = featurize(it["title"], it.get("summary", ""), None)
        tfs.append((tf, topics, entities))
        df.update(set(tf))
    out = []
    for it, (tf, topics, entities) in zip(items, tfs):
        kw = tfidf_keywords(tf, df, len(items))
        out.append({**it, "topics": topics, "entities": entities, "keywords": kw,
                    "kwset": set(list(kw)[:8]), "word_count": len(it.get("summary", "").split())})
    return out


def pairwise_scores(items: List[Dict], clusters) -> Dict[str, float]:
    gold = {it["id"]: it["event"] for it in items}
    pred = {}
    for c in clusters:
        for a in c.articles:
            pred[a["id"]] = c.id
    tp = fp = fn = 0
    for x, y in combinations(gold, 2):
        same_gold, same_pred = gold[x] == gold[y], pred[x] == pred[y]
        tp += same_gold and same_pred
        fp += (not same_gold) and same_pred
        fn += same_gold and not same_pred
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
            "clusters": len(clusters), "gold_events": len(set(gold.values()))}


def evaluate(path: str = "tests/fixtures/cluster_gold.json") -> Dict[str, float]:
    from core.clustering import ClusterEngine
    items = json.load(open(path))["articles"]
    arts = featurize_articles(items)
    return pairwise_scores(items, ClusterEngine.cluster_articles(arts))


if __name__ == "__main__":
    print(evaluate())
