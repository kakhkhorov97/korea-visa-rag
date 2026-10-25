"""Export reviewed public sources and existing vectors locally. Never calls Gemini."""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from visarag.config import ROOT, INDEX_DIR, GEMINI_EMBED_MODEL
from visarag.snapshot import export_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index-root', type=Path, default=INDEX_DIR)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/releases')
    parser.add_argument('--bm25-only', action='store_true', help='Explicitly omit vectors')
    args = parser.parse_args()
    data = export_snapshot(ROOT / 'data/public_raw', args.index_root, GEMINI_EMBED_MODEL,
                           bm25_only=args.bm25_only)
    digest = hashlib.sha256(data).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / f'{digest}.json'
    path.write_bytes(data)
    print(f'Snapshot: {path}\nSHA-256: {digest}\nBytes: {len(data)}')


if __name__ == '__main__':
    main()
