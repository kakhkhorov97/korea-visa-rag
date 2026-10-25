"""Portable public-corpus snapshots, restored without any embedding API calls.

Cloud Storage holds the durable copy. Chroma is a disposable local serving copy,
never a SQLite database mounted on an object-storage filesystem.
"""
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

from .chunking import chunk_document
from .documents import load_documents
from .index_cache import index_path
from .retrieval import VectorRetriever

MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024


def public_chunks(raw_dir: Path):
    """Use only the reviewed public corpus packaged with this application."""
    documents = load_documents(raw_dir)
    if not documents or any(
        d.doc_type != 'law' or not d.retrieved
        or urlsplit(d.source_url).scheme != 'https'
        or urlsplit(d.source_url).netloc != 'www.law.go.kr'
        for d in documents
    ):
        raise ValueError('Snapshots require the reviewed public statute corpus')
    return [c for d in documents for c in chunk_document(d)]


def no_embeddings(_texts):
    raise RuntimeError('Snapshot operations must never call an embedding provider')


def export_snapshot(raw_dir: Path, index_root: Path, model: str, *, bm25_only=False) -> bytes:
    chunks = public_chunks(raw_dir)
    vectors = None
    if not bm25_only:
        path = index_path(chunks, model, index_root)
        if not (path / 'chroma.sqlite3').is_file():
            raise ValueError('No existing public vector index; use --bm25-only or prepare it explicitly')
        retriever = VectorRetriever(no_embeddings, persist_dir=str(path))
        if not retriever.matches(chunks):
            raise ValueError('The vector index does not match the complete public corpus')
        stored = retriever.collection.get(include=['embeddings'])
        vectors = dict(zip(stored['ids'], stored['embeddings'].tolist()))
    payload = {'version': 1, 'model': model,
               'chunks': [c.to_dict() for c in chunks], 'vectors': vectors}
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    if len(data) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Snapshot exceeds the small-demo size limit')
    return data


def restore_snapshot(data: bytes, sha256: str, raw_dir: Path, data_dir: Path, model: str):
    """Validate before writing, including exact equality with packaged public sources."""
    if len(data) > MAX_SNAPSHOT_BYTES or hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError('Snapshot size or SHA-256 mismatch')
    payload = json.loads(data)
    chunks = public_chunks(raw_dir)
    if (payload.get('version') != 1 or payload.get('model') != model
            or payload.get('chunks') != [c.to_dict() for c in chunks]):
        raise ValueError('Snapshot does not match this image public corpus/model')
    vectors = payload.get('vectors')
    if vectors is not None:
        ids = {c.chunk_id for c in chunks}
        if not isinstance(vectors, dict) or set(vectors) != ids:
            raise ValueError('Snapshot vectors must cover every public chunk exactly')
        dimension = None
        for vector in vectors.values():
            if not isinstance(vector, list) or not vector:
                raise ValueError('Invalid snapshot vector')
            dimension = dimension or len(vector)
            if len(vector) != dimension or any(
                type(x) not in {int, float} or not math.isfinite(x) for x in vector
            ):
                raise ValueError('Invalid snapshot vector values or dimensions')
        path = index_path(chunks, model, data_dir / 'index')
        retriever = VectorRetriever(no_embeddings, persist_dir=str(path))
        retriever.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[vectors[c.chunk_id] for c in chunks],
            documents=[f'{c.title} {c.section}\n{c.text}' for c in chunks],
        )
        if not retriever.matches(chunks):
            raise ValueError('Restored index verification failed')
    processed = data_dir / 'processed'
    processed.mkdir(parents=True, exist_ok=True)
    temporary = processed / 'chunks.jsonl.tmp'
    temporary.write_text(''.join(json.dumps(c.to_dict(), ensure_ascii=False) + '\n' for c in chunks))
    temporary.replace(processed / 'chunks.jsonl')
    return {'sha256': sha256, 'chunks': len(chunks), 'vectors': vectors is not None}


def download_snapshot(uri: str, generation: str, sha256: str) -> bytes:
    """Read one pinned object using the Cloud Run service identity, never a key file."""
    parsed = urlsplit(uri)
    if (parsed.scheme != 'gs' or not parsed.netloc or not parsed.path.strip('/')
            or parsed.query or parsed.fragment or not generation.isdecimal()
            or int(generation) < 1 or not re.fullmatch(r'[0-9a-f]{64}', sha256)):
        raise ValueError('Set a gs:// object, positive generation and lowercase SHA-256')
    from google.cloud import storage

    client = storage.Client()
    blob = client.bucket(parsed.netloc).blob(parsed.path.lstrip('/'), generation=int(generation))
    blob.reload(timeout=30, retry=None)
    if blob.size is None or blob.size > MAX_SNAPSHOT_BYTES:
        raise ValueError('Cloud snapshot exceeds the small-demo size limit')
    data = blob.download_as_bytes(if_generation_match=int(generation), timeout=60, retry=None)
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError('Cloud snapshot SHA-256 mismatch')
    return data
