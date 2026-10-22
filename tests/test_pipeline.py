"""Run with:  pytest -q
These tests need no API key: the vector test uses a fake embedding function."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from visarag.assistant import build_context, cited_numbers  # noqa: E402
from visarag.chunking import chunk_document, chunk_guide  # noqa: E402
from visarag.documents import Document, parse_document  # noqa: E402
from visarag.metrics import hit_at_k, recall_at_k, reciprocal_rank  # noqa: E402
from visarag.retrieval import BM25Retriever, reciprocal_rank_fusion  # noqa: E402
from visarag.tokenizer import extract_visa_codes, tokenize  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "fake_law.txt"


@pytest.fixture(scope="module")
def doc():
    return parse_document(FIXTURE.read_text(encoding="utf-8"), "fake_law")


@pytest.fixture(scope="module")
def chunks(doc):
    return chunk_document(doc)


def test_metadata_parsed(doc):
    assert doc.title == "테스트용 가짜 법령"
    assert doc.doc_type == "law"
    assert doc.source_url == "https://example.com/fake-law"


def test_law_split_by_article(chunks):
    sections = [c.section for c in chunks]
    assert sections == ["전문", "제1조(목적)", "제2조(구직 체류자격)", "제2조의2(시간제 취업)", "제3조(체류자격 변경)"]
    article2 = chunks[2].text
    assert "①" in article2 and "②" in article2 and "둘째 호" in article2   # 항/호 stay together


def test_citation_label(chunks):
    assert chunks[3].citation() == "테스트용 가짜 법령 제2조의2(시간제 취업)"


def test_guide_windows_respect_max_size():
    text = "\n\n".join(f"문단 {i} " + "가" * 300 for i in range(10))
    pieces = chunk_guide(Document("g", "가이드", text))
    assert len(pieces) > 1
    assert all(len(p.text) <= 900 for p in pieces)


def test_visa_codes():
    assert extract_visa_codes("D-10 비자와 e - 7 - 1") == ["D-10", "E-7", "E-7-1"]


def test_tokenizer_strips_particles():
    toks = tokenize("비자를 변경하려면")
    assert "비자" in toks and "를" not in toks


def test_bm25_finds_visa_code(chunks):
    bm25 = BM25Retriever(chunks)
    top_id, _ = bm25.search("D-10 구직 체류기간")[0]
    assert top_id == chunks[2].chunk_id
    top_id, _ = bm25.search("유학생 시간제 취업 허가")[0]
    assert top_id == chunks[3].chunk_id


def test_rrf_rewards_agreement():
    fused = reciprocal_rank_fusion([[("a", 9), ("b", 5)], [("b", 0.9), ("c", 0.8)]])
    assert fused[0][0] == "b"            # ranked by both retrievers -> wins


def test_metrics():
    retrieved, relevant = ["x", "a", "y"], {"a", "z"}
    assert hit_at_k(retrieved, relevant, 1) == 0.0
    assert hit_at_k(retrieved, relevant, 2) == 1.0
    assert recall_at_k(retrieved, relevant, 3) == 0.5
    assert reciprocal_rank(retrieved, relevant) == 0.5


def test_citation_parsing_and_context(chunks):
    assert cited_numbers("A [1]. B [2][3]. Bad [9].", 3) == [1, 2, 3]
    ctx = build_context(chunks[:2])
    assert ctx.startswith("[1] 테스트용 가짜 법령") and "[2]" in ctx


def test_search_only_assistant(chunks):
    from visarag.assistant import VisaAssistant

    a = VisaAssistant(chunks=chunks, use_llm=False)
    assert a.available_modes == ["bm25"]
    ans = a.ask("유학생 시간제 취업 허가", mode="hybrid")      # falls back to bm25
    assert ans.mode == "search-only"
    assert ans.sources[0].chunk_id == chunks[3].chunk_id
    d = ans.to_dict()
    assert d["sources"][0]["n"] == 1 and d["sources"][0]["url"].startswith("https://")


def test_api_endpoints(chunks):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from visarag import api
    from visarag.assistant import VisaAssistant

    fake = VisaAssistant(chunks=chunks, use_llm=False)
    original = api.get_assistant
    api.get_assistant = lambda: fake
    try:
        client = TestClient(api.app)
        health = client.get("/api/health").json()
        assert health["llm"] is False and health["chunks"] == len(chunks)
        res = client.post("/api/ask", json={"question": "D-10 구직 체류기간"}).json()
        assert res["mode"] == "search-only" and res["sources"][0]["chunk_id"] == chunks[2].chunk_id
        assert client.post("/api/ask", json={"question": ""}).status_code == 422
        assert client.get("/").status_code == 200
    finally:
        api.get_assistant = original


def test_telegram_formatting(chunks):
    from visarag.assistant import Answer
    from visarag.telegram_bot import format_answer_html, parse_mode_arg, truncate

    ans = Answer("q", "Yes **with permission** [1]. <script>", chunks[2:4], mode="hybrid", cited=[1])
    out = format_answer_html(ans)
    assert "<b>with permission</b>" in out and "<b>[1]</b>" in out
    assert "&lt;script&gt;" in out and "<script>" not in out        # user/LLM text is escaped
    assert '✅ [1] <a href="https://example.com/fake-law">' in out
    assert "▫️ [2]" in out

    search_only = format_answer_html(Answer("q", "note", chunks[2:3], mode="search-only"))
    assert "<i>제2조(구직 체류자격)" in search_only                    # passage preview shown

    long = "\n".join(["line " * 50] * 40)
    assert len(truncate(long)) <= 4096
    assert parse_mode_arg(["BM25"], ["bm25"]) == "bm25"
    assert parse_mode_arg(["vector"], ["bm25"]) is None


def test_vector_retriever_with_fake_embeddings(chunks):
    pytest.importorskip("chromadb")
    from visarag.retrieval import VectorRetriever

    vocab = ["구직", "시간제", "변경", "목적"]

    def fake_embed(texts):        # bag-of-keywords vectors, deterministic and free
        return [[float(t.count(w)) + 0.01 for w in vocab] for t in texts]

    vr = VectorRetriever(fake_embed)
    vr.build(chunks)
    top_id, _ = vr.search("시간제")[0]
    assert top_id == chunks[3].chunk_id
