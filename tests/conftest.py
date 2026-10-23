"""Keep API usage accounting isolated from the developer's persistent database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest


@pytest.fixture(autouse=True)
def api_usage_database(tmp_path, monkeypatch):
    from visarag import api
    from visarag.limits import UsageLimits
    limits = UsageLimits(tmp_path / 'api-usage.sqlite3', 100, 100, 2)
    monkeypatch.setattr(api, 'get_limits', lambda: limits)
