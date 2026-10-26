"""Check the beta archive's public-data boundary and bucket retention scope."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_contains_only_reviewed_public_data():
    spec = importlib.util.spec_from_file_location('package_beta', ROOT / 'scripts/package_beta.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = {p.relative_to(ROOT).as_posix() for p in module.files()}
    assert len({n for n in names if n.startswith('data/public_raw/') and n.endswith('.txt')}) == 44
    assert {'Dockerfile.beta', 'cloudbuild.beta.yaml', 'web/privacy.html', 'web/favicon.svg',
            'src/visarag/cloud_limits.py', 'src/visarag/grounding.py'} <= names
    for ignore_file in ('.gcloudignore', '.dockerignore'):
        assert '!web/*.svg' in (ROOT / ignore_file).read_text()
    assert not any(n.startswith(('data/raw/', 'data/originals/', 'data/releases/', '.git/'))
                   or n.endswith(('.env', '.sqlite3', '.hwp')) for n in names)


def test_beta_lifecycle_keeps_existing_rule_and_excludes_releases():
    prior = json.loads((ROOT / 'deploy/storage-lifecycle.json').read_text())['rule']
    proposed = json.loads((ROOT / 'deploy/beta-lifecycle.json').read_text())['rule']
    assert all(rule in proposed for rule in prior)
    assert {'action': {'type': 'Delete'}, 'condition': {'age': 30,
            'matchesPrefix': ['usage/public-beta/']}} in proposed
    prefixes = [p for rule in proposed for p in rule['condition'].get('matchesPrefix', [])]
    assert not any(p.startswith(('releases/', 'documents/')) for p in prefixes)
