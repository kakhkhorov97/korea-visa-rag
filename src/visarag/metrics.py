"""Retrieval metrics. Pure functions, so they are easy to unit-test.

hit@k     - did at least one correct chunk appear in the top k?  (most intuitive)
recall@k  - what fraction of all correct chunks appeared in the top k?
MRR       - 1 / (position of the first correct chunk), averaged. Rewards
            putting the right chunk first, not just somewhere in the list.
"""

from statistics import mean


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(cid in relevant for cid in retrieved[:k]) else 0.0


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant & set(retrieved[:k])) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


def summarize(rows: list[dict], k: int) -> dict:
    return {
        f"hit@{k}": round(mean(r["hit"] for r in rows), 3),
        f"recall@{k}": round(mean(r["recall"] for r in rows), 3),
        "MRR": round(mean(r["rr"] for r in rows), 3),
        "n": len(rows),
    }
