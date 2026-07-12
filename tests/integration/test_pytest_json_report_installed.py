"""Fixture: pytest-json-report is installed and produces a usable JSON.

v1.1 task 3b discovered that the harness's verifier never produced real
counts because ``--json-report`` is a pytest *plugin* that has to be
installed; it isn't a pytest built-in. Without it, the verifier's
``--json-report-file=`` arg fails, the produced JSON file is empty,
and the ``Failed to parse JSON report`` warning fires repeatedly.

This test is small but valuable: if ``pytest-json-report`` is removed
from ``pyproject.toml [project] dependencies`` by accident, CI catches
the regression before the bench produces misleading numbers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_jsonreport  # noqa: F401  -- presence-only import


def test_pytest_json_report_module_imports():
    """The plugin module is importable; missing-install fails at
    collection time.
    """
    assert pytest_jsonreport is not None


def test_pytest_json_report_produces_a_usable_file(tmp_path):
    """A trivial pytest invocation with ``--json-report`` writes a
    file the verifier can actually parse. The structure we depend on
    is ``{"summary": {...}, "tests": [...]}``.
    """
    test_file = tmp_path / "test_trivial.py"
    test_file.write_text("def test_one():\n    assert True\n")
    json_path = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(test_file), "-v", "--tb=short",
            "--json-report", f"--json-report-file={json_path}",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
        timeout=60,
    )
    if not json_path.exists():
        pytest.fail(
            f"pytest --json-report produced no file. "
            f"exit={result.returncode}; stderr={result.stderr[:400]}"
        )
    payload = json.loads(json_path.read_text())
    assert "tests" in payload
    assert "summary" in payload
    assert payload["summary"]["total"] >= 1
