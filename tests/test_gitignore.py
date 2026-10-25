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
