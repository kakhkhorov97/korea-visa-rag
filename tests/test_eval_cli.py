"""Check evaluation argument errors without an index or API key."""

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("k", ["0", "-1", "-10"])
def test_eval_rejects_nonpositive_k(tmp_path, k):
    # An absent question file proves validation happens before loading any data.
    result = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "run_eval.py"),
         "--questions", str(tmp_path / "missing.jsonl"), "--k", k],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "--k must be at least 1" in result.stderr
    assert "Traceback" not in result.stderr
