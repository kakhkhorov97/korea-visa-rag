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
from .config import CHUNKS_FILE, HAS_GEMINI, INDEX_DIR, TOP_K, GEMINI_EMBED_MODEL
from .retrieval import BM25Retriever, HybridRetriever

SYSTEM_PROMPT = """You are a careful assistant that answers questions about Korean visa \
and residence rules (체류자격) using ONLY the numbered sources provided.

Rules:
1. Answer in the same language as the question (Korean or English).
2. Every factual claim needs evidence from numbered sources. The app adds [n] citations.
3. If the sources do not contain the answer, say so plainly and suggest contacting the \
Immigration Contact Center (☎ 1345) or HiKorea. Never guess or use outside knowledge.
4. Quote visa codes, periods, and amounts exactly as written in the sources.
5. Keep it concise: a direct answer first, then the key conditions as a short list.
6. The app adds the general-information disclaimer in the required language."""

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
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON-friendly form, used by the API."""
        return {
            "question": self.question,
            "answer": self.text,
            "mode": self.mode,
            "cited": self.cited,
            "latency_s": self.latency_s,
            "usage": self.usage,
            "evidence": self.evidence,
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


def response_language(question: str) -> str:
    """Choose from the question alone, never from the Korean retrieved sources.

    Visa codes carry no language. Mixed questions use the more numerous word
    groups, with Korean winning ties. Code-only queries default to English.
    This is a small English/Korean heuristic, not a general language detector.
    """
    question = re.sub(r"\b[A-Z]-\d+(?:-\d+)?\b", "", question, flags=re.I)
    english = len(re.findall(r"[A-Za-z]{2,}", question))
    korean = len(re.findall(r"[가-힣ㄱ-ㅎㅏ-ㅣ]+", question))
    return "Korean" if korean and korean >= english else "English"


def language_instruction(language: str) -> str:
    """Keep translated explanations separate from original source labels."""
    return (
        f"Required answer language: {language}. Write every explanation, list item, "
        f"refusal and the final disclaimer in {language}. The sources are Korean; "
        "their language must not determine your answer language. Translate supported "
        "information faithfully without adding claims. Original official titles and "
        "short Korean terms in parentheses may remain Korean. Keep [n] citations."
    )


def answer_matches_language(text: str, language: str) -> bool:
    """Reject a mostly wrong-script answer, allowing short original terms.

    This guard catches language drift; it does not validate legal accuracy or
    prove that every word has the requested language. No extra AI call is made.
    """
    prose = re.sub(r"\([^()]*\)", "", text)
    latin = len(re.findall(r"[A-Za-z]", prose))
    hangul = len(re.findall(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", prose))
    if language == "English":
        return latin > 0 and latin >= hangul
    return hangul > 0 and hangul * 2 >= latin


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

            from .index_cache import index_path

            path = index_path(self.chunks, GEMINI_EMBED_MODEL, INDEX_DIR)
            if path.exists():
                vector = VectorRetriever(llm.embed, persist_dir=str(path),
                                         query_embed_fn=llm.embed_query)
                if vector.matches(self.chunks):
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

    def ask(self, question: str, mode: str | None = None, *, source_only: bool = False) -> Answer:
        start = time.perf_counter()
        mode = 'bm25' if source_only else mode if mode in self.retrievers else self.mode
        sources = self.retrieve(question, mode)

        if source_only or not self.use_llm:
            text = SEARCH_ONLY_NOTE if sources else (
                "No matching passages found. Try different keywords, or contact ☎ 1345."
            )
            return Answer(question, text, sources, mode="search-only",
                          latency_s=round(time.perf_counter() - start, 2))

        from . import llm
        from .grounding import GroundedReply, GROUNDING_INSTRUCTION, checked_claims, abstention, disclaimer
        from .errors import ProviderError

        language = response_language(question)
        instruction = language_instruction(language)
        if not sources:
            return Answer(question, abstention(language) + '\n\n' + disclaimer(language), [], mode=mode,
                          latency_s=round(time.perf_counter() - start, 2))
        messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{instruction}\n\n{GROUNDING_INSTRUCTION}"},
            {"role": "user", "content": (
                f"Sources:\n\n{build_context(sources)}\n\n"
                f"Question: {question}\n\n{instruction}"
            )},
        ]
        raw, usage = llm.chat(messages, response_schema=GroundedReply.model_json_schema())
        try:
            text, complete, evidence = checked_claims(raw, sources)
        except (ValueError, TypeError):
            raise ProviderError('The answer could not be checked against the sources. Please try keyword search.') from None
        if not text:
            return Answer(question, abstention(language) + '\n\n' + disclaimer(language), [], mode=mode,
                          latency_s=round(time.perf_counter() - start, 2), usage=usage)
        if not answer_matches_language(text, language):
            message = (
                "The answer was not generated in English. Please try again, or use "
                "keyword search to read the original source passages."
                if language == "English" else
                "한국어 답변을 생성하지 못했습니다. 다시 질문하거나 키워드 검색으로 원문을 확인해 주세요."
            )
            raise ProviderError(message)
        if not complete:
            text += ('\n\nThe sources cover only part of this question. Confirm the remaining details with 1345 or HiKorea.'
                     if language == 'English' else
                     '\n\n자료가 질문의 일부만 다룹니다. 나머지 내용은 1345 또는 하이코리아에서 확인해 주세요.')
        text += '\n\n' + disclaimer(language)
        return Answer(
            question=question,
            text=text,
            sources=sources,
            mode=mode,
            cited=cited_numbers(text, len(sources)),
            latency_s=round(time.perf_counter() - start, 2),
            usage=usage,
            evidence=evidence,
        )
