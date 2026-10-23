"""The assistant: retrieve -> build a grounded prompt -> answer with citations.

Two operating modes:
* full mode        (GEMINI_API_KEY set): hybrid retrieval + AI-written, cited answer
* search-only mode (no key, free)      : BM25 retrieval, returns the top sources only
"""

import json
import re
import time
from dataclasses import dataclass, field

from .chunking import Chunk
from .config import CHUNKS_FILE, HAS_GEMINI, INDEX_DIR, TOP_K
from .retrieval import BM25Retriever, HybridRetriever

SYSTEM_PROMPT = """You are a careful assistant that answers questions about Korean visa \
and residence rules (체류자격) using ONLY the numbered sources provided.

Rules:
1. Answer in the same language as the question (Korean or English).
2. Every factual sentence must end with a citation like [1] or [2][3] pointing to the sources.
3. If the sources do not contain the answer, say so plainly and suggest contacting the \
Immigration Contact Center (☎ 1345) or HiKorea. Never guess or use outside knowledge.
4. Quote visa codes, periods, and amounts exactly as written in the sources.
5. Keep it concise: a direct answer first, then the key conditions as a short list.
6. End with: "This is general information, not legal advice. Rules change; confirm with \
1345 or HiKorea." (translate it if answering in Korean)."""

SEARCH_ONLY_NOTE = (
    "Search-only mode (no AI answer): these are the most relevant official passages "
    "for your question. Add a Gemini API key to get a written, cited answer."
)


@dataclass
class Answer:
    question: str
    text: str
    sources: list[Chunk]
    mode: str = "hybrid"
    cited: list[int] = field(default_factory=list)   # 1-based source numbers used
    latency_s: float = 0.0
    usage: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """JSON-friendly form, used by the API."""
        return {
            "question": self.question,
            "answer": self.text,
            "mode": self.mode,
            "cited": self.cited,
            "latency_s": self.latency_s,
            "usage": self.usage,
            "sources": [
                {"n": i, "citation": c.citation(), "url": c.source_url,
                 "chunk_id": c.chunk_id, "text": c.text}
                for i, c in enumerate(self.sources, start=1)
            ],
        }


def load_chunks(path=CHUNKS_FILE) -> list[Chunk]:
    with open(path, encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f if line.strip()]


def build_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] {c.citation()}\nSource: {c.source_url}\n{c.text}")
    return "\n\n---\n\n".join(blocks)


def cited_numbers(text: str, n_sources: int) -> list[int]:
    nums = {int(n) for n in re.findall(r"\[(\d+)\]", text)}
    return sorted(n for n in nums if 1 <= n <= n_sources)


class VisaAssistant:
    def __init__(self, mode: str = "hybrid", top_k: int = TOP_K,
                 chunks: list[Chunk] | None = None, use_llm: bool | None = None):
        self.chunks = chunks if chunks is not None else load_chunks()
        self.by_id = {c.chunk_id: c for c in self.chunks}
        self.top_k = top_k
        self.use_llm = HAS_GEMINI if use_llm is None else use_llm

        bm25 = BM25Retriever(self.chunks)
        self.retrievers = {"bm25": bm25}
        if self.use_llm:
            from . import llm
            from .retrieval import VectorRetriever

            vector = VectorRetriever(llm.embed, persist_dir=str(INDEX_DIR),
                                     query_embed_fn=llm.embed_query)
            self.retrievers["vector"] = vector
            self.retrievers["hybrid"] = HybridRetriever(bm25, vector)
        self.mode = mode if mode in self.retrievers else "bm25"

    @property
    def available_modes(self) -> list[str]:
        order = ["hybrid", "bm25", "vector"]
        return [m for m in order if m in self.retrievers]

    def retrieve(self, question: str, mode: str | None = None, k: int | None = None) -> list[Chunk]:
        mode = mode if mode in self.retrievers else self.mode
        ranked = self.retrievers[mode].search(question)
        return [self.by_id[cid] for cid, _ in ranked[: k or self.top_k] if cid in self.by_id]

    def ask(self, question: str, mode: str | None = None) -> Answer:
        start = time.perf_counter()
        mode = mode if mode in self.retrievers else self.mode
        sources = self.retrieve(question, mode)

        if not self.use_llm:
            text = SEARCH_ONLY_NOTE if sources else (
                "No matching passages found. Try different keywords, or contact ☎ 1345."
            )
            return Answer(question, text, sources, mode="search-only",
                          latency_s=round(time.perf_counter() - start, 2))

        from . import llm

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Sources:\n\n{build_context(sources)}\n\nQuestion: {question}"},
        ]
        text, usage = llm.chat(messages)
        return Answer(
            question=question,
            text=text,
            sources=sources,
            mode=mode,
            cited=cited_numbers(text, len(sources)),
            latency_s=round(time.perf_counter() - start, 2),
            usage=usage,
        )
