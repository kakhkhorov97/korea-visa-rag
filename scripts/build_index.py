"""Turn data/raw/*.txt into chunks and a searchable vector index.

Run after adding or changing documents:
  python scripts/build_index.py            # chunk + embed (embeds only if GEMINI_API_KEY is set)
  python scripts/build_index.py --no-embed # chunk only, free (search-only mode still works)
"""

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visarag.chunking import chunk_document  # noqa: E402
from visarag.config import CHUNKS_FILE, INDEX_DIR, RAW_DIR  # noqa: E402
from visarag.documents import load_documents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-embed", action="store_true", help="skip the embedding step")
    args = parser.parse_args()

    docs = load_documents(RAW_DIR)
    if not docs:
        sys.exit(f"No documents in {RAW_DIR}. See data/raw/README.md.")

    chunks = [c for d in docs for c in chunk_document(d)]
    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

    per_doc = Counter(c.doc_id for c in chunks)
    lengths = sorted(len(c.text) for c in chunks)
    print(f"{len(docs)} documents -> {len(chunks)} chunks")
    for doc_id, n in per_doc.items():
        print(f"  {doc_id}: {n} chunks")
    print(f"chunk length: median {lengths[len(lengths) // 2]} chars, max {lengths[-1]} chars")

    from visarag.config import HAS_GEMINI

    if args.no_embed or not HAS_GEMINI:
        if not HAS_GEMINI:
            print("No GEMINI_API_KEY: skipped embeddings. The app will run in free search-only mode.")
        return
    from visarag import llm
    from visarag.retrieval import VectorRetriever

    shutil.rmtree(INDEX_DIR, ignore_errors=True)       # rebuild from scratch
    VectorRetriever(llm.embed, persist_dir=str(INDEX_DIR)).build(chunks)
    print(f"Vector index saved to {INDEX_DIR}")


if __name__ == "__main__":
    main()
