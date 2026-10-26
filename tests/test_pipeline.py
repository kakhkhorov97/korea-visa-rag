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


@pytest.mark.parametrize("comment", ["", " # source section", "\t# source section"])
def test_metadata_preserves_url_fragments(comment):
    raw = (
        "---\n"
        f"source_url: https://example.com/guide#article-2{comment}\n"
        "doc_type: guide # split by heading\n"
        "---\n"
        "Fixture text, not legal content.\n"
    )
    doc = parse_document(raw, "anchored_source")
    assert doc.source_url == "https://example.com/guide#article-2"
    assert doc.doc_type == "guide"
    assert doc.text == "Fixture text, not legal content."


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
        res = client.post("/api/ask", json={"question": "  D-10 구직 체류기간\n"}).json()
        assert res["question"] == "D-10 구직 체류기간"
        assert res["mode"] == "search-only" and res["sources"][0]["chunk_id"] == chunks[2].chunk_id
        assert client.post("/api/ask", json={"question": ""}).status_code == 422
        assert client.get("/").status_code == 200
        assert health["modes"] == ["bm25"]  # UI disables unavailable search methods.
        for asset in ["/static/app.js", "/static/styles.css"]:
            response = client.get(asset)
            assert response.status_code == 200 and response.text.strip()
    finally:
        api.get_assistant = original


@pytest.mark.parametrize("question", ["", "   ", "\t\n", " a ", "가" * 501, None, 42])
def test_api_rejects_invalid_questions(question, monkeypatch):
    from fastapi.testclient import TestClient

    from visarag import api

    def unexpected_assistant():
        pytest.fail("Invalid questions must be rejected before loading the assistant")

    monkeypatch.setattr(api, "get_assistant", unexpected_assistant)
    response = TestClient(api.app).post("/api/ask", json={"question": question})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "question"]


@pytest.mark.parametrize("query", ["", "   ", "\t\n", " a ", "가" * 501])
def test_search_rejects_invalid_queries(query, monkeypatch):
    from fastapi.testclient import TestClient

    from visarag import api

    def unexpected_assistant():
        pytest.fail("Invalid search queries must be rejected before loading the assistant")

    monkeypatch.setattr(api, "get_assistant", unexpected_assistant)
    response = TestClient(api.app).get("/api/search", params={"q": query})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "q"]


def test_search_trims_query(chunks, monkeypatch):
    from fastapi.testclient import TestClient

    from visarag import api

    class SearchAssistant:
        available_modes = ["bm25"]
        mode = "bm25"
        def retrieve(self, query, mode, k):
            assert query == "D-10 구직"
            assert mode == "bm25" and k == 5
            return chunks[:1]

    monkeypatch.setattr(api, "get_assistant", lambda: SearchAssistant())
    response = TestClient(api.app).get("/api/search", params={"q": "  D-10 구직\n"})
    assert response.status_code == 200
    assert response.json()["query"] == "D-10 구직"
    assert response.json()["results"][0]["chunk_id"] == chunks[0].chunk_id


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

    queries = []

    def fake_query_embed(texts):
        queries.extend(texts)
        return fake_embed(texts)

    vr = VectorRetriever(fake_embed, query_embed_fn=fake_query_embed)
    vr.build(chunks)
    top_id, _ = vr.search("시간제")[0]
    assert top_id == chunks[3].chunk_id
    assert queries == ["시간제"]


def test_vector_build_respects_small_embedding_batches(chunks, tmp_path):
    from dataclasses import replace

    from visarag.retrieval import VectorRetriever

    documents = [replace(chunks[i % len(chunks)], chunk_id=f"batch-test-{i}") for i in range(12)]

    def limited_embed(texts):
        if len(texts) > 5:
            pytest.fail("Embedding request exceeds the project's small-batch limit")
        return [[1.0, 0.0] for _ in texts]

    retriever = VectorRetriever(limited_embed, persist_dir=str(tmp_path))
    retriever.build(documents)
    assert set(retriever.collection.get(include=[])["ids"]) == {c.chunk_id for c in documents}


@pytest.fixture
def gemini_models(monkeypatch):
    """Use real SDK types, but replace the network client so tests stay free."""
    from unittest.mock import Mock

    from visarag import llm

    fake = Mock()
    monkeypatch.setattr(llm, "client", lambda: fake)
    return fake.models


def test_gemini_embeddings_use_document_and_query_tasks(gemini_models):
    from google.genai import types

    from visarag import llm

    gemini_models.embed_content.return_value = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[1.0, 0.0]),
                    types.ContentEmbedding(values=[0.0, 1.0])]
    )
    assert llm.embed(["article one", "article two"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert gemini_models.embed_content.call_args.kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"
    gemini_models.embed_content.return_value = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[1.0, 0.0])]
    )
    assert llm.embed_query(["question"]) == [[1.0, 0.0]]
    assert gemini_models.embed_content.call_args.kwargs["config"].task_type == "RETRIEVAL_QUERY"


def test_gemini_empty_embedding_input_makes_no_request(gemini_models):
    from visarag import llm

    assert llm.embed([]) == []
    gemini_models.embed_content.assert_not_called()


def test_gemini_rejects_missing_embeddings(gemini_models):
    from google.genai import types

    from visarag import llm

    gemini_models.embed_content.return_value = types.EmbedContentResponse(embeddings=[])
    from visarag.errors import ProviderError
    with pytest.raises(ProviderError, match="one embedding per input"):
        llm.embed(["article"])


def test_gemini_chat_preserves_instructions_roles_and_usage(gemini_models):
    from google.genai import types

    from visarag import llm

    gemini_models.generate_content.return_value = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text="Answer [1].")]))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=10, candidates_token_count=5, total_token_count=18),
    )
    answer, usage = llm.chat([
        {"role": "system", "content": "Use only the sources and cite them."},
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "Sources: [1] passage. Question: can I work?"},
    ])
    request = gemini_models.generate_content.call_args.kwargs
    assert request["config"].system_instruction == "Use only the sources and cite them."
    assert [c.role for c in request["contents"]] == ["user", "model", "user"]
    assert request["contents"][-1].parts[0].text.startswith("Sources: [1]")
    assert answer == "Answer [1]."
    assert usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 18}


def test_gemini_rejects_empty_answer(gemini_models):
    from google.genai import types

    from visarag import llm

    gemini_models.generate_content.return_value = types.GenerateContentResponse()
    from visarag.errors import ProviderError
    with pytest.raises(ProviderError, match="no answer text"):
        llm.chat([{"role": "user", "content": "question"}])


def test_gemini_requires_key(monkeypatch):
    from visarag import llm

    llm.client.cache_clear()
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        llm.client()


def test_gemini_client_bounds_requests_and_is_cached(monkeypatch):
    from unittest.mock import Mock

    from google import genai
    from visarag import llm

    factory = Mock()
    monkeypatch.setattr(genai, "Client", factory)
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "test-key-not-a-real-credential")
    llm.client.cache_clear()
    try:
        assert llm.client() is llm.client()
        factory.assert_called_once()
        options = factory.call_args.kwargs["http_options"]
        assert options.timeout == 60_000
        assert options.retry_options.attempts == 1
    finally:
        llm.client.cache_clear()


def test_gemini_assistant_answers_with_citations(chunks, gemini_models, monkeypatch, tmp_path):
    from google.genai import types

    from visarag import assistant, llm
    from visarag.retrieval import VectorRetriever

    def fake_embed_content(*, contents, **kwargs):
        return types.EmbedContentResponse(embeddings=[
            types.ContentEmbedding(values=[float(text.count("시간제")) + 0.01, 1.0])
            for text in contents
        ])

    gemini_models.embed_content.side_effect = fake_embed_content
    gemini_models.generate_content.return_value = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text="테스트 답변 [1].")]))],
    )
    monkeypatch.setattr(assistant, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(assistant, "HAS_GEMINI", True)
    from visarag.index_cache import index_path
    path = index_path(chunks, assistant.GEMINI_EMBED_MODEL, tmp_path)
    VectorRetriever(llm.embed, persist_dir=str(path)).build(chunks)
    engine = assistant.VisaAssistant(chunks=chunks)
    answer = engine.ask("시간제 취업 허가")
    assert engine.available_modes == ["hybrid", "bm25", "vector"]
    assert answer.mode == "hybrid" and answer.cited == [1]
    assert answer.sources[0].chunk_id == chunks[3].chunk_id
    assert gemini_models.embed_content.call_args.kwargs["config"].task_type == "RETRIEVAL_QUERY"
    request = gemini_models.generate_content.call_args.kwargs
    assert chunks[3].text in request["contents"][0].parts[0].text
    assert request["config"].system_instruction == (
        assistant.SYSTEM_PROMPT + "\n\n" + assistant.language_instruction("Korean")
    )


def test_missing_gemini_key_keeps_search_only(chunks, monkeypatch):
    from visarag import assistant, llm

    monkeypatch.setattr(assistant, "HAS_GEMINI", False)
    monkeypatch.setattr(llm, "client", lambda: pytest.fail("Search-only must not call Gemini"))
    engine = assistant.VisaAssistant(chunks=chunks)
    answer = engine.ask("시간제 취업 허가")
    assert engine.available_modes == ["bm25"]
    assert answer.mode == "search-only"
    assert answer.sources[0].chunk_id == chunks[3].chunk_id


@pytest.mark.parametrize("setting", ["true", "1", "YES"])
def test_search_only_setting_disables_saved_gemini_key(setting, monkeypatch):
    import runpy

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setenv("SEARCH_ONLY", setting)
    config = runpy.run_path(str(ROOT / "src" / "visarag" / "config.py"))
    assert config["GEMINI_API_KEY"]
    assert config["SEARCH_ONLY"] is True
    assert config["HAS_GEMINI"] is False


def test_imported_guides_have_official_source_metadata():
    from datetime import date

    from visarag.documents import load_documents

    docs = {d.doc_id: d for d in load_documents(ROOT / "data" / "raw")}
    for visa in ["d2", "d4", "d10", "e7"]:
        doc = docs[f"hikorea_{visa}"]
        assert doc.doc_type == "guide" and len(doc.text) > 1000
        assert doc.source_url.startswith("https://www.hikorea.go.kr/")
        assert date.fromisoformat(doc.retrieved)
        assert len(doc.extra["source_sha256"]) == 64
        assert "KOGL Type 4" in doc.extra["license"]


@pytest.mark.parametrize("question, expected", [
    ("What is the E-9 visa category?", "English"),
    ("Can I extend my D-10 visa?", "English"),
    ("What does 체류자격 mean?", "English"),
    ("E-9 비전문취업은 무엇인가요?", "Korean"),
    ("D-10 체류기간", "Korean"),
    ("E-9 visa가 뭐예요?", "Korean"),
    ("D-10", "English"),
])
def test_response_language_uses_question_without_visa_codes(question, expected):
    from visarag.assistant import response_language
    assert response_language(question) == expected


@pytest.mark.parametrize("text, language, expected", [
    ("The category is Non-professional Employment (비전문취업) [1].", "English", True),
    ("This is the Korean term 체류자격 [1].", "English", True),
    ("비전문취업 자격으로 취업하는 사람입니다 [1].", "English", False),
    ("E-9 비전문취업 자격입니다 [1].", "Korean", True),
    ("The category is non-professional employment [1].", "Korean", False),
    ("[1]", "English", False),
])
def test_answer_language_guard_allows_terms_but_rejects_drift(text, language, expected):
    from visarag.assistant import answer_matches_language
    assert answer_matches_language(text, language) is expected


@pytest.mark.parametrize("question, language, reply", [
    ("What is the E-9 visa category?", "English", "An English answer [1]."),
    ("E-9 비전문취업은 무엇인가요?", "Korean", "한국어 답변입니다 [1]."),
])
def test_assistant_pins_language_despite_korean_sources(chunks, monkeypatch, question, language, reply):
    from visarag import assistant, llm
    engine = assistant.VisaAssistant(chunks=chunks, use_llm=False)
    engine.use_llm = True
    monkeypatch.setattr(engine, "retrieve", lambda *args: [chunks[3]])
    requests = []
    def chat(messages):
        requests.append(messages)
        return reply, {"total_tokens": 12}
    monkeypatch.setattr(llm, "chat", chat)
    result = engine.ask(question, mode="bm25")
    assert result.text == reply and result.cited == [1]
    assert len(requests) == 1
    system, user = requests[0]
    assert system["content"].startswith(assistant.SYSTEM_PROMPT)
    assert f"Required answer language: {language}" in system["content"]
    assert user["content"].endswith(assistant.language_instruction(language))
    assert chunks[3].text in user["content"]


def test_assistant_does_not_return_wrong_language_or_retry(chunks, monkeypatch):
    from unittest.mock import Mock
    from visarag import assistant, llm
    from visarag.errors import ProviderError
    engine = assistant.VisaAssistant(chunks=chunks, use_llm=False)
    engine.use_llm = True
    monkeypatch.setattr(engine, "retrieve", lambda *args: [chunks[3]])
    chat = Mock(return_value=("한국어로 작성된 답변입니다 [1].", {}))
    monkeypatch.setattr(llm, "chat", chat)
    with pytest.raises(ProviderError, match="not generated in English"):
        engine.ask("What is the E-9 visa category?")
    chat.assert_called_once()
