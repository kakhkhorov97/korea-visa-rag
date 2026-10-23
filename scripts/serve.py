"""Build free chunks at startup. Embeddings require a separate explicit command."""
import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / 'scripts/build_index.py'), '--no-embed'], check=True)
    import uvicorn
    uvicorn.run('visarag.api:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')),
                proxy_headers=False, workers=1)


if __name__ == '__main__':
    main()
