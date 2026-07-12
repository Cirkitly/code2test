"""Corpus integrity tests.

These verify that:

  1. The manifest exists and parses.
  2. Every entry references a path that exists and has a code/ dir.
  3. The hidden ground-truth tests still pass against vendored source.
  4. Every repo has at least one component declared.

This is the M1D.4 integrity gate; if any of these fail, the corpus is
broken and benchmark numbers from it would be meaningless.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent.parent.parent  # code2testbench/
CORPUS = HERE / "corpus"
MANIFEST = CORPUS / "manifest.json"


def _read_manifest():
    if not MANIFEST.exists():
        pytest.skip(f"manifest not found at {MANIFEST}")
    return json.loads(MANIFEST.read_text())


def test_manifest_parses():
    m = _read_manifest()
    assert m["schema_version"] == 1
    assert m["frozen"] is True
    assert len(m["repos"]) == 5, "v1.0 ships with exactly 5 vendored repos"


def test_every_repo_has_components_dir():
    m = _read_manifest()
    for repo in m["repos"]:
        p = HERE / repo["path"]
        assert p.is_dir(), f"missing repo path: {p}"
        comp = p / repo.get("components_dir", "code")
        assert comp.is_dir(), f"missing components dir: {comp}"
        assert any(comp.glob("*.py")), f"empty components dir: {comp}"


def test_every_repo_has_hidden_tests():
    m = _read_manifest()
    for repo in m["repos"]:
        hidden = HERE / repo["ground_truth"]
        assert hidden.exists(), f"missing hidden test: {hidden}"


def test_repo1_corpus_tests_pass():
    """repo1's ground-truth suite passes against the vendored source."""
    _check_corpus_hidden_pass("repo1")


def test_repo2_corpus_tests_pass():
    _check_corpus_hidden_pass("repo2")


def test_repo3_corpus_tests_pass():
    _check_corpus_hidden_pass("repo3")


def test_repo4_corpus_tests_pass():
    _check_corpus_hidden_pass("repo4")


def test_repo5_corpus_tests_pass():
    _check_corpus_hidden_pass("repo5")


def _check_corpus_hidden_pass(repo_name: str) -> None:
    repo = HERE / "corpus" / repo_name
    hidden = repo / "hidden"
    if not hidden.exists():
        pytest.skip(f"hidden dir missing for {repo_name}")
    # Run the hidden ground-truth tests directly with pytest.
    res = subprocess.run(
        [sys.executable, "-m", "pytest", str(hidden), "-q", "--no-cov",
         "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True,
        env={**os.environ,
             "PYTHONPATH": str(repo / "code"),
             "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=60,
    )
    assert res.returncode == 0, (
        f"hidden ground-truth tests failed for {repo_name}:\n"
        f"{res.stdout}\n{res.stderr}"
    )
