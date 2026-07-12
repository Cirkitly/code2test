"""Failure-mode corpus is well-formed and points at hidden ground truth.

The failure-mode corpus exists to exercise the diagnosis_agent and
the rewrite loop. These tests pin its structure so future refactors
of the bench surface cannot silently remove or rename components.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent  # tests/integration -> code2testbench
_MANIFEST = _REPO_ROOT / "corpus" / "manifest_failure_modes.json"
_CORPUS_DIR = _REPO_ROOT / "corpus" / "repo_failure_modes"


def test_manifest_failure_modes_exists():
    assert _MANIFEST.exists(), f"manifest missing: {_MANIFEST}"


def test_manifest_failure_modes_is_json_with_one_repo():
    """Schema_version is 1, the manifest is not frozen, and exactly
    one repo entry points at repo_failure_modes."""
    payload = json.loads(_MANIFEST.read_text())
    assert payload["schema_version"] == 1
    assert payload.get("frozen") is False
    repos = payload["repos"]
    assert len(repos) == 1
    repo = repos[0]
    assert repo["name"] == "repo_failure_modes"
    assert repo["path"] == "corpus/repo_failure_modes"


def test_manifest_components_match_actual_code_functions():
    """The manifest's components list must match the function names
    in code/validators.py. A drift here would silently mean the bench
    tries to verify wrong components."""
    payload = json.loads(_MANIFEST.read_text())
    components = payload["repos"][0]["components"]

    src_path = _CORPUS_DIR / "code" / "validators.py"
    assert src_path.exists(), f"missing {src_path}"
    src = src_path.read_text()
    # Cheap name extraction. ast.parse would be cleaner but we want
    # this to be readable in CI logs.
    for name in components:
        assert f"def {name}(" in src, f"function {name} not in {src_path}"


def test_hidden_tests_fail_against_buggy_implementation():
    """The hidden ground-truth tests are designed to fail on the
    buggy implementation. If they pass, the corpus is no longer
    exercising the failure-mode path."""
    test_path = _CORPUS_DIR / "hidden" / "test_validators.py"
    assert test_path.exists()

    code_dir = _CORPUS_DIR / "code"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "--no-cov", "-q"],
        capture_output=True, text=True,
        cwd=str(code_dir),  # so validators.py is importable
        timeout=60,
    )
    # Some tests should fail (the bug-pattern tests). If 0 failed,
    # the corpus has lost its bite.
    output = result.stdout + result.stderr
    assert "failed" in output, f"unexpected pytest output: {output[:600]}"
    # Reject the case where all tests passed: that means the bug
    # patterns are no longer exercised.
    assert result.returncode != 0, (
        "Hidden tests passed; the failure-mode corpus has lost its "
        "bite. Restore at least one bug to the implementation."
    )


def test_harness_reports_diagnosis_on_failure_modes():
    """End-to-end probe: running the harness against the
    failure-mode manifest with --confidence 0.0 must report
    diagnosis_trigger_rate > 0 (or NaN if no failure was detected).

    Skipped if OPENAI_API_KEY is not set -- this is an integration
    test that requires the configured LLM provider.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set; integration probe requires it")

    out_path = _REPO_ROOT / "latest_report_failure_modes.json"
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "code2testbench.runner",
                "--provider", "openai",
                "--model", os.environ.get("OPENAI_MODEL", "MiniMax-M3"),
                "--confidence", "0.0",
                "--manifest", str(_MANIFEST.relative_to(_REPO_ROOT)),
                "--out", str(out_path.relative_to(_REPO_ROOT)),
            ],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
            timeout=600,
        )
        assert result.returncode == 0, (
            f"harness failed: stdout={result.stdout[-400:]} "
            f"stderr={result.stderr[-400:]}"
        )
        assert out_path.exists()
        payload = json.loads(out_path.read_text())
        # We expect diagnosis_trigger_rate > 0 because every test
        # against the buggy implementation should trigger diagnosis.
        dtr = payload.get("diagnosis_trigger_rate")
        assert isinstance(dtr, float)
        # Allow 0.0 if the LLM produced no test cases (a known edge),
        # but require NaN-equivalence (i.e., not blocked) otherwise.
        assert dtr > 0.0 or dtr != dtr, (
            f"diagnosis_trigger_rate={dtr} but the failure-mode "
            "corpus was designed to trigger diagnosis on every test"
        )
    finally:
        if out_path.exists():
            out_path.unlink()
