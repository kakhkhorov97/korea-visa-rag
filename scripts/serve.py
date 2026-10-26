"""Restore a pinned cloud snapshot, or build local chunks without embedding calls."""
import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    if os.getenv('VISARAG_PUBLIC_BETA', '').lower() == 'true' and not os.getenv('VISARAG_USAGE_URI'):
        raise RuntimeError('Public beta requires a durable VISARAG_USAGE_URI')
    if os.getenv('K_SERVICE') and not os.getenv('VISARAG_SNAPSHOT_URI'):
        raise RuntimeError('Cloud Run requires a pinned durable VISARAG_SNAPSHOT_URI')
    if os.getenv('VISARAG_SNAPSHOT_URI'):
        from visarag.config import RAW_DIR, DATA_DIR, GEMINI_EMBED_MODEL
        from visarag.snapshot import download_snapshot, restore_snapshot
        digest = os.environ['VISARAG_SNAPSHOT_SHA256']
        data = download_snapshot(os.environ['VISARAG_SNAPSHOT_URI'],
                                 os.environ['VISARAG_SNAPSHOT_GENERATION'], digest)
        result = restore_snapshot(data, digest, RAW_DIR, DATA_DIR, GEMINI_EMBED_MODEL)
        print(f'Restored public snapshot: {result}', flush=True)
    else:
        subprocess.run([sys.executable, str(root / 'scripts/build_index.py'), '--no-embed'], check=True)
    import uvicorn
    uvicorn.run('visarag.api:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')),
                proxy_headers=False, access_log=False, workers=1)


if __name__ == '__main__':
    main()
