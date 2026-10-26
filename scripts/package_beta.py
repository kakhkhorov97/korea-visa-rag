"""Create a reviewable, credential-free Cloud Shell release archive.

Run locally after tests. The archive is an explicit allowlist and contains the
beta manifests for deployment commands; Cloud Build still follows .gcloudignore.
"""
from hashlib import sha256
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/visa-beta-release-20261026.zip')


def files() -> list[Path]:
    paths = [ROOT / name for name in (
        '.gcloudignore', '.dockerignore', 'Dockerfile.beta', 'cloudbuild.beta.yaml',
        'requirements.txt', 'scripts/build_index.py', 'scripts/serve.py',
    )]
    for folder, pattern in [('src/visarag', '*.py'), ('web', '*'),
                            ('data/public_raw', '*.txt'), ('deploy', 'beta-*')]:
        paths.extend(path for path in (ROOT / folder).rglob(pattern) if path.is_file())
    paths = sorted(set(paths))
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f'Release path is unsafe: {path}')
    return paths


def main() -> None:
    selected = files()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, 'w', ZIP_DEFLATED) as archive:
        for path in selected:
            archive.write(path, path.relative_to(ROOT))
    digest = sha256(OUTPUT.read_bytes()).hexdigest()
    print(f'{OUTPUT} files={len(selected)} bytes={OUTPUT.stat().st_size} sha256={digest}')


if __name__ == '__main__':
    main()
