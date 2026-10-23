"""Three ways to find relevant chunks, so we can compare them in evaluation.

* BM25Retriever   - keyword matching. Great for exact terms ("D-10", "체류기간").
* VectorRetriever - meaning matching with embeddings. Finds "can I work part-time
                    as a student?" even when the law says "시간제 취업 허가".
* HybridRetriever - runs both and merges the rankings with Reciprocal Rank
                    Fusion (RRF). Usually beats either one alone.

Each retriever returns a ranked list of (chunk_id, score).
"""

from collections import defaultdict
from typing import Callable, Sequence

from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .config import CANDIDATES_PER_RETRIEVER, RRF_K
from .tokenizer import tokenize

Ranked = list[tuple[str, float]]
EmbedFn = Callable[[list[str]], list[list[float]]]


class BM25Retriever:
    def __init__(self, chunks: Sequence[Chunk]):
        self.ids = [c.chunk_id for c in chunks]
        # Title + section are included so "출입국관리법 시행령 제12조" matches its own chunk.
        corpus = [tokenize(f"{c.title} {c.section} {c.text}") for c in chunks]
        self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, k: int = CANDIDATES_PER_RETRIEVER) -> Ranked:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.ids[i], float(scores[i])) for i in order if scores[i] > 0]


class VectorRetriever:
    """Embeddings stored in a local Chroma database (data/index)."""

    COLLECTION = "visa_chunks"

    def __init__(self, embed_fn: EmbedFn, persist_dir: str | None = None,
                 query_embed_fn: EmbedFn | None = None):
        import chromadb

        self.embed_fn = embed_fn
        self.query_embed_fn = query_embed_fn or embed_fn
        client = chromadb.PersistentClient(path=persist_dir) if persist_dir else chromadb.Client()
        self.collection = client.get_or_create_collection(
            self.COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def matches(self, chunks: Sequence[Chunk]) -> bool:
        """Check IDs and embedded text before advertising a reusable index."""
        stored = self.collection.get(include=["documents"])
        return dict(zip(stored["ids"], stored["documents"])) == {
            c.chunk_id: f"{c.title} {c.section}\n{c.text}" for c in chunks
        }

    def build(self, chunks: Sequence[Chunk], batch_size: int = 5) -> None:
        """Use small batches to reduce bursts against embedding API quotas."""
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        stored = self.collection.get(include=["documents"])
        existing = dict(zip(stored["ids"], stored["documents"]))
        pending = [c for c in chunks if existing.get(c.chunk_id) != f"{c.title} {c.section}\n{c.text}"]
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            texts = [f"{c.title} {c.section}\n{c.text}" for c in batch]
            self.collection.upsert(
                ids=[c.chunk_id for c in batch],
                embeddings=self.embed_fn(texts),
                documents=texts,
            )

    def search(self, query: str, k: int = CANDIDATES_PER_RETRIEVER) -> Ranked:
        if self.collection.count() == 0:
            return []
        res = self.collection.query(
            query_embeddings=self.query_embed_fn([query]),
            n_results=min(k, self.collection.count()),
        )
        # Chroma returns cosine *distance*; convert to similarity so higher = better.
        return [(cid, 1.0 - dist) for cid, dist in zip(res["ids"][0], res["distances"][0])]


def reciprocal_rank_fusion(rankings: Sequence[Ranked], k: int = RRF_K) -> Ranked:
    """score(doc) = sum over rankers of 1 / (k + rank).

    RRF ignores raw scores (BM25 scores and cosine similarities are on different
    scales) and only uses positions, which makes it simple and robust.
    """
    fused: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, (cid, _score) in enumerate(ranking, start=1):
            fused[cid] += 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)


class HybridRetriever:
    def __init__(self, bm25: BM25Retriever, vector: VectorRetriever):
        self.bm25, self.vector = bm25, vector

    def search(self, query: str, k: int = CANDIDATES_PER_RETRIEVER) -> Ranked:
        return reciprocal_rank_fusion([self.bm25.search(query, k), self.vector.search(query, k)])[:k]
