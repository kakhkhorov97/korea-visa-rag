"""Snapshot persistence and public-data boundaries, without cloud/API credentials."""
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from visarag import snapshot
from visarag.assistant import load_chunks
from visarag.index_cache import index_path
from visarag.retrieval import VectorRetriever

RAW = Path(__file__).resolve().parents[1] / 'data/public_raw'
MODEL = 'test-embedding-model'


def test_snapshot_survives_two_empty_filesystems_without_embedding(tmp_path):
    chunks = snapshot.public_chunks(RAW)
    original = tmp_path / 'original'
    VectorRetriever(lambda texts: [[1.0, 0.1] for _ in texts],
                    str(index_path(chunks, MODEL, original))).build(chunks)
    data = snapshot.export_snapshot(RAW, original, MODEL)
    digest = hashlib.sha256(data).hexdigest()
    for target in [tmp_path / 'restart', tmp_path / 'new-deployment']:
        result = snapshot.restore_snapshot(data, digest, RAW, target, MODEL)
        assert result['vectors'] is True
        restored = load_chunks(target / 'processed/chunks.jsonl')
        assert restored == chunks  # URLs, citation labels and retrieval dates survive.
        index = VectorRetriever(snapshot.no_embeddings,
                                str(index_path(chunks, MODEL, target / 'index')))
        assert index.matches(chunks)
        assert index.collection.get(include=['embeddings'])['embeddings'].shape == (len(chunks), 2)


def test_bm25_snapshot_needs_no_vector_database(tmp_path):
    data = snapshot.export_snapshot(RAW, tmp_path / 'absent', MODEL, bm25_only=True)
    result = snapshot.restore_snapshot(data, hashlib.sha256(data).hexdigest(), RAW, tmp_path, MODEL)
    assert result['chunks'] == len(snapshot.public_chunks(RAW)) and result['vectors'] is False
    assert not (tmp_path / 'index').exists()


@pytest.mark.parametrize('mutation', ['checksum', 'private', 'model', 'missing-vector', 'nan'])
def test_invalid_snapshots_fail_before_writing(tmp_path, mutation):
    data = snapshot.export_snapshot(RAW, tmp_path, MODEL, bm25_only=True)
    payload = json.loads(data)
    if mutation == 'private':
        payload['chunks'][0]['text'] = 'PRIVATE DOCUMENT CANARY'
    elif mutation == 'model':
        payload['model'] = 'different-model'
    elif mutation == 'missing-vector':
        payload['vectors'] = {}
    elif mutation == 'nan':
        payload['vectors'] = {c['chunk_id']: [float('nan')] for c in payload['chunks']}
    data = json.dumps(payload).encode()
    digest = '0' * 64 if mutation == 'checksum' else hashlib.sha256(data).hexdigest()
    target = tmp_path / 'serving'
    with pytest.raises(ValueError):
        snapshot.restore_snapshot(data, digest, RAW, target, MODEL)
    assert not target.exists()


def test_export_rejects_absent_index_instead_of_embedding(tmp_path):
    with pytest.raises(ValueError, match='No existing public vector index'):
        snapshot.export_snapshot(RAW, tmp_path, MODEL)


def test_download_pins_generation_and_checks_digest(monkeypatch):
    from google.cloud import storage
    data = b'fixture'
    blob = Mock(size=len(data))
    blob.download_as_bytes.return_value = data
    client = Mock()
    client.bucket.return_value.blob.return_value = blob
    monkeypatch.setattr(storage, 'Client', lambda: client)
    digest = hashlib.sha256(data).hexdigest()
    assert snapshot.download_snapshot('gs://private/releases/fixture.json', '123', digest) == data
    client.bucket.return_value.blob.assert_called_once_with('releases/fixture.json', generation=123)
    blob.download_as_bytes.assert_called_once_with(if_generation_match=123, timeout=60, retry=None)
    with pytest.raises(ValueError, match='SHA-256'):
        snapshot.download_snapshot('gs://private/releases/fixture.json', '123', '0' * 64)
    blob.size = snapshot.MAX_SNAPSHOT_BYTES + 1
    with pytest.raises(ValueError, match='size limit'):
        snapshot.download_snapshot('gs://private/releases/fixture.json', '123', digest)


def test_cloud_run_refuses_unpinned_startup(monkeypatch):
    from scripts import serve
    monkeypatch.setenv('K_SERVICE', 'visa-test')
    monkeypatch.delenv('VISARAG_SNAPSHOT_URI', raising=False)
    with pytest.raises(RuntimeError, match='pinned durable'):
        serve.main()


def test_cloud_startup_restores_before_starting_server(tmp_path, monkeypatch):
    from scripts import serve
    from visarag import config
    import uvicorn

    data = snapshot.export_snapshot(RAW, tmp_path, MODEL, bm25_only=True)
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(config, 'RAW_DIR', RAW)
    monkeypatch.setattr(config, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(config, 'GEMINI_EMBED_MODEL', MODEL)
    monkeypatch.setenv('K_SERVICE', 'visa-test')
    monkeypatch.setenv('VISARAG_SNAPSHOT_URI', 'gs://private/releases/test.json')
    monkeypatch.setenv('VISARAG_SNAPSHOT_GENERATION', '123')
    monkeypatch.setenv('VISARAG_SNAPSHOT_SHA256', digest)
    monkeypatch.setenv('PORT', '8080')
    download = Mock(return_value=data)
    monkeypatch.setattr(snapshot, 'download_snapshot', download)
    monkeypatch.setattr(serve.subprocess, 'run', lambda *a, **kw: pytest.fail('Must not rebuild'))

    def verify_startup(*args, **kwargs):
        assert len(load_chunks(tmp_path / 'processed/chunks.jsonl')) == len(snapshot.public_chunks(RAW))
        assert kwargs['port'] == 8080 and kwargs['workers'] == 1
        assert kwargs['proxy_headers'] is False

    server = Mock(side_effect=verify_startup)
    monkeypatch.setattr(uvicorn, 'run', server)
    serve.main()
    download.assert_called_once_with('gs://private/releases/test.json', '123', digest)
    server.assert_called_once()
