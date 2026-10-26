"""Check the beta archive's public-data boundary and bucket retention scope."""
import importlib.util
import json
from pathlib import Path
import yaml

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


def test_github_release_requires_manual_main_branch_and_keyless_auth():
    workflow = yaml.load((ROOT / '.github/workflows/deploy-cloud-run.yml').read_text(),
                         Loader=yaml.BaseLoader)
    assert list(workflow['on']) == ['workflow_dispatch']
    assert workflow['permissions'] == {'contents': 'read', 'id-token': 'write'}
    job = workflow['jobs']['deploy']
    assert "github.ref == 'refs/heads/main'" in job['if']
    assert job['environment'] == 'production'
    auth = next(step for step in job['steps'] if step.get('uses', '').startswith('google-github-actions/auth@'))
    assert 'workload_identity_provider' in auth['with']
    assert 'credentials_json' not in auth['with']
    script = (ROOT / 'scripts/deploy_from_github.sh').read_text()
    assert '--no-traffic --tag=ci-candidate' in script
    assert script.index('candidate-ai-answer.json') < script.index('--to-revisions="${CANDIDATE_REVISION}=100"')
    assert '--to-revisions="${GOOD_REVISION}=100"' in script
    assert 'VISARAG_SNAPSHOT_SHA256' in script
