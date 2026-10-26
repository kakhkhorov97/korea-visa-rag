"""Keep local operating-system metadata out of source control."""
from pathlib import Path
import subprocess


def test_finder_metadata_is_ignored_at_any_depth():
    root = Path(__file__).resolve().parents[1]
    paths = ['.DS_Store', 'data/.DS_Store', 'tests/fixtures/.DS_Store']
    result = subprocess.run(
        ['git', 'check-ignore', '--no-index', '--stdin'],
        cwd=root,
        input='\n'.join(paths) + '\n',
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == paths


def test_local_artifacts_and_env_variants_are_ignored():
    root = Path(__file__).resolve().parents[1]
    paths = [
        'data/originals/example.hwp',
        '.impeccable/design.json',
        '.impeccable/review/example.png',
        '.env.local',
        '.env.production',
    ]
    result = subprocess.run(
        ['git', 'check-ignore', '--no-index', '--stdin'],
        cwd=root, input='\n'.join(paths) + '\n',
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.splitlines() == paths
    template = subprocess.run(
        ['git', 'check-ignore', '--no-index', '.env.example'],
        cwd=root, capture_output=True, text=True,
    )
    assert template.returncode == 1
