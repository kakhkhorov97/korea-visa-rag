"""Each model/corpus gets its own index, so partial rebuilds cannot replace it."""
import hashlib
import json
from pathlib import Path
from typing import Sequence

from .chunking import Chunk


def index_path(chunks: Sequence[Chunk], model: str, root: Path) -> Path:
    payload = [model, sorted((c.chunk_id, f'{c.title} {c.section}\n{c.text}') for c in chunks)]
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    return root / digest
