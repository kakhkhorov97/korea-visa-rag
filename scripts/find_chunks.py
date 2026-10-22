"""Helper for labeling the evaluation set: search chunks by keyword and print their IDs.

  python scripts/find_chunks.py "D-10"
  python scripts/find_chunks.py "시간제 취업"

Copy the chunk_id(s) that truly answer a question into eval/questions.jsonl.
Uses BM25 only, so it is free and needs no API key.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visarag.assistant import load_chunks  # noqa: E402
from visarag.retrieval import BM25Retriever  # noqa: E402

query = " ".join(sys.argv[1:]) or sys.exit('Usage: python scripts/find_chunks.py "search words"')
chunks = load_chunks()
by_id = {c.chunk_id: c for c in chunks}
for cid, score in BM25Retriever(chunks).search(query, k=10):
    c = by_id[cid]
    preview = c.text.replace("\n", " ")[:120]
    print(f"{cid}  ({score:.1f})  {c.citation()}\n    {preview}…\n")
