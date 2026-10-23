"""Deployment regressions use real Chroma/FastAPI, without provider requests."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.genai import errors

from visarag import api, llm
from visarag.assistant import VisaAssistant
from visarag.chunking import Chunk
from visarag.errors import ProviderError
from visarag.index_cache import index_path
from visarag.limits import UsageLimits
from visarag.retrieval import VectorRetriever


@pytest.fixture(autouse=True)
def isolated_limits(tmp_path, monkeypatch):
    limits = UsageLimits(tmp_path / 'usage.db', 100, 100, 2)
    monkeypatch.setattr(api, 'get_limits', lambda: limits)


def sample_chunks():
    return [Chunk(str(i), 'test', 'Fixture', '', f'허가 {i}', 'https://example.invalid', '2026-10-24')
            for i in range(4)]


def test_index_resume_and_reuse(tmp_path):
    chunks = sample_chunks()
    calls = []
    def interrupted(texts):
        calls.append(texts)
        if len(calls) == 2:
            raise RuntimeError('interrupted')
        return [[1.0, 0.1] for _ in texts]
    retriever = VectorRetriever(interrupted, str(tmp_path))
    with pytest.raises(RuntimeError):
        retriever.build(chunks, batch_size=2)
    assert not retriever.matches(chunks)
    embed = Mock(side_effect=lambda texts: [[1.0, 0.1] for _ in texts])
    resumed = VectorRetriever(embed, str(tmp_path))
    resumed.build(chunks, batch_size=2)
    assert len(embed.call_args.args[0]) == 2
    assert resumed.matches(chunks)
    embed.reset_mock()
    resumed.build(chunks)
    embed.assert_not_called()


def test_cache_changes_with_model_or_text(tmp_path):
    chunks = sample_chunks()
    first = index_path(chunks, 'model-a', tmp_path)
    assert first == index_path(list(reversed(chunks)), 'model-a', tmp_path)
    assert first != index_path(chunks, 'model-b', tmp_path)
    chunks[0].text += ' changed'
    assert first != index_path(chunks, 'model-a', tmp_path)


def test_missing_cache_never_embeds_on_startup(tmp_path, monkeypatch):
    from visarag import assistant
    monkeypatch.setattr(assistant, 'INDEX_DIR', tmp_path)
    monkeypatch.setattr(llm, 'embed', lambda _: pytest.fail('Startup must not embed'))
    engine = VisaAssistant(chunks=sample_chunks(), use_llm=True)
    assert engine.available_modes == ['bm25']
    assert engine.use_llm  # AI answers can still use keyword retrieval.


def test_limits_survive_restart_and_release_slots(tmp_path):
    path = tmp_path / 'usage.db'
    limits = UsageLimits(path, 2, 1, 1)
    with pytest.raises(RuntimeError):
        with limits.reserve('alice', True):
            raise RuntimeError('provider failed')
    with limits.reserve('alice', False):
        pass
    with pytest.raises(HTTPException) as minute:
        with limits.reserve('alice', False):
            pass
    assert minute.value.status_code == 429
    restarted = UsageLimits(path, 2, 1, 1)
    with pytest.raises(HTTPException) as daily:
        with restarted.reserve('bob', True):
            pass
    assert 'daily' in daily.value.detail
    with restarted.reserve('bob', False):
        pass


def test_limits_reject_parallel_ai(tmp_path):
    limits = UsageLimits(tmp_path / 'usage.db', 20, 100, 1)
    with limits.reserve('alice', True):
        with pytest.raises(HTTPException) as busy:
            with limits.reserve('bob', True):
                pass
        assert busy.value.status_code == 503
    with limits.reserve('bob', True):
        pass


@pytest.mark.parametrize('failure,status', [
    (errors.ClientError(429, {'error': {'message': 'secret-key-in-upstream-url'}}), 429),
    (errors.ClientError(403, {'error': {'message': 'secret-key-in-upstream-url'}}), 503),
    (httpx.ReadTimeout('secret-key-in-upstream-url'), 504),
    (httpx.ConnectError('secret-key-in-upstream-url'), 503),
])
def test_provider_errors_are_safe(failure, status, monkeypatch):
    models = SimpleNamespace(embed_content=Mock(side_effect=failure))
    monkeypatch.setattr(llm, 'client', lambda: SimpleNamespace(models=models))
    with pytest.raises(ProviderError) as error:
        llm.embed(['hello'])
    assert error.value.status_code == status
    assert 'secret-key' not in str(error.value)


def test_api_provider_failure_and_rate_limit(tmp_path, monkeypatch):
    calls = Mock(side_effect=ProviderError('Safe failure', 429))
    assistant = SimpleNamespace(use_llm=True, ask=calls)
    monkeypatch.setattr(api, 'get_assistant', lambda: assistant)
    limits = UsageLimits(tmp_path / 'limits.db', 1, 2, 1)
    monkeypatch.setattr(api, 'get_limits', lambda: limits)
    client = TestClient(api.app)
    first = client.post('/api/ask', json={'question': 'D-10 visa'})
    assert first.status_code == 429 and first.json()['detail'] == 'Safe failure'
    second = client.post('/api/ask', json={'question': 'D-10 visa'})
    assert second.status_code == 429
    calls.assert_called_once()


def test_public_corpus_and_container_are_statute_only():
    from visarag.config import ROOT
    from visarag.documents import load_documents
    documents = load_documents(ROOT / 'data/public_raw')
    assert len(documents) >= 17
    for doc in documents:
        assert doc.doc_type == 'law'
        assert doc.source_url.startswith('https://www.law.go.kr/')
        assert doc.retrieved and doc.extra['text_sha256']
    dockerfile = (ROOT / 'Dockerfile').read_text()
    assert 'COPY . .' not in dockerfile
    assert 'COPY data/public_raw/' in dockerfile
    assert 'COPY data/raw/' not in dockerfile
    startup = (ROOT / 'scripts/serve.py').read_text()
    assert "'--no-embed'" in startup
