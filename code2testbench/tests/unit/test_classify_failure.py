"""Unit tests for the variance experiment's failure classifier.

The classifier partitions RewriteCommitted events into named
buckets. The buckets drive the variance report's "where is the
pipeline stopping?" answer. Pinning each branch ensures we can
trust the report's findings.
"""

from __future__ import annotations

import pytest

from code2testbench.run_variance_experiment import _classify_failure


def test_strategy_mismatch_when_classifier_wrong_route():
    """TEST_WRONG -> test_rewrite is the deterministic route. If a
    rewrite landed on skip with that cause, that's a strategy
    mismatch and we want it flagged.
    """
    assert _classify_failure({
        "strategy": "skip",
        "failure_classification": "TEST_WRONG",
        "success": False,
        "isolated_passed": 0,
        "isolated_failed": 0,
        "replaced": False,
    }) == "strategy_mismatch"


def test_strategy_skip_is_its_own_category_for_code_bug():
    """CODE_BUG -> skip is the deterministic route. The classifier
    tracks it as strategy_skip, NOT as 'other' or any failure
    category. The variance report says 'the loop said nothing to
    do because the source has a bug;' that's not the loop being
    broken, that's the loop working as designed.
    """
    assert _classify_failure({
        "strategy": "skip",
        "failure_classification": "CODE_BUG",
        "success": False,
        "isolated_passed": 0,
        "isolated_failed": 0,
        "replaced": False,
    }) == "strategy_skip"


def test_verifier_failure_when_candidate_failed_in_isolation():
    """isolated_failed > 0 and success=False means the candidate
    ran in the coordinator's verifier path and didn't pass.
    """
    assert _classify_failure({
        "strategy": "test_rewrite",
        "failure_classification": "TEST_WRONG",
        "success": False,
        "isolated_passed": 2,
        "isolated_failed": 1,
        "replaced": False,
    }) == "verifier_failure"


def test_transactional_replacement_failure_when_passed_not_replaced():
    """isolated_passed > 0 with success=False and replaced=False
    means the candidate passed in isolation but the generator
    didn't swap the production file. That's the transactional
    bug we've tested in isolation -- catching it in production
    means the bug is in the swap path, not the verifier.
    """
    assert _classify_failure({
        "strategy": "test_rewrite",
        "failure_classification": "TEST_WRONG",
        "success": False,
        "isolated_passed": 4,
        "isolated_failed": 0,
        "replaced": False,
    }) == "transactional_replacement_failure"


def test_success_returns_success_label():
    """success=True with replaced=True means the rewrite worked
    end-to-end. Returns 'success' so the caller can distinguish
    successful rewrites from failures.
    """
    assert _classify_failure({
        "strategy": "test_rewrite",
        "failure_classification": "TEST_WRONG",
        "success": True,
        "isolated_passed": 4,
        "isolated_failed": 0,
        "replaced": True,
    }) == "success"


def test_unknown_failure_path_falls_to_other():
    """When success=False but isolated_failed==0 and isolated_passed==0
    and not replaced, the failure path is unaccounted for. The
    classifier returns 'other' so the variance report surfaces
    this category rather than hiding it.
    """
    assert _classify_failure({
        "strategy": "test_rewrite",
        "failure_classification": "TEST_WRONG",
        "success": False,
        "isolated_passed": 0,
        "isolated_failed": 0,
        "replaced": False,
    }) == "other"
