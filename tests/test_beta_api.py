"""Privacy/access checks run before retrieval, embeddings or answer generation."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from visarag import api
from visarag.assistant import Answer, VisaAssistant
from visarag.limits import UsageLimits


@pytest.fixture
def beta(monkeypatch, tmp_path):
    engine = SimpleNamespace(use_llm=True, available_modes=['bm25','hybrid'], mode='bm25',
        ask=Mock(return_value=Answer('Question','Reply',[])), retrieve=Mock(return_value=[]))
    monkeypatch.setattr(api,'PUBLIC_BETA',True)
    monkeypatch.setattr(api,'get_assistant',lambda:engine)
    monkeypatch.setattr(api,'get_limits',lambda:UsageLimits(tmp_path/'test.db',100,100,1))
    return TestClient(api.app),engine


@pytest.mark.parametrize('question', ['My email is person@example.com', 'My ID is 901101-5123456',
    'Call 010-1234-5678', 'My passport is M12345678'])
def test_identifiers_never_reach_provider(beta, question):
    client,engine=beta
    assert client.post('/api/ask',json={'question':question,'ai_ack':True}).status_code==422
    assert client.get('/api/search',params={'q':question,'mode':'hybrid','ai_ack':True}).status_code==422
    engine.ask.assert_not_called();engine.retrieve.assert_not_called()


def test_ack_required_for_ai_and_semantic_search(beta):
    client,engine=beta
    assert client.post('/api/ask',json={'question':'What is E-9?'}).status_code==403
    assert client.get('/api/search',params={'q':'D-10','mode':'hybrid'}).status_code==403
    engine.ask.assert_not_called();engine.retrieve.assert_not_called()
    assert client.post('/api/ask',json={'question':'What is E-9?','ai_ack':True}).status_code==200


def test_source_search_does_not_require_ai_ack(beta):
    client,engine=beta
    assert client.post('/api/ask',json={'question':'D-10 구직','source_only':True}).status_code==200
    engine.ask.assert_called_once_with('D-10 구직',mode='bm25',source_only=True)
    assert client.get('/api/search',params={'q':'D-10','mode':'bm25'}).status_code==200


def test_privacy_page_is_available(beta):
    client,_=beta
    response=client.get('/privacy')
    assert response.status_code==200 and 'does not verify age or location' in response.text


def test_source_only_override_never_uses_vectors_or_llm(monkeypatch):
    from visarag import llm
    from visarag.chunking import Chunk
    chunk=Chunk('fixture','fixture','Fixture','','테스트 비자 자료입니다.','https://example.invalid','2026-10-26')
    engine=VisaAssistant(chunks=[chunk],use_llm=False)
    engine.use_llm=True
    engine.retrievers['bm25']=Mock(search=Mock(return_value=[('fixture',1.0)]))
    vector=Mock();vector.search.side_effect=AssertionError('Must not embed source-only query')
    engine.retrievers['hybrid']=vector;engine.mode='hybrid'
    monkeypatch.setattr(llm,'chat',Mock(side_effect=AssertionError('Must not generate source-only answer')))
    answer=engine.ask('비자',mode='hybrid',source_only=True)
    assert answer.mode=='search-only' and answer.sources
    vector.search.assert_not_called()
