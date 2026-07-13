"""Unit tests for code2testbench.report.AcceptanceReport.

Verifies the eight-number schema, the net_improvement helper, and JSON
round-trip. These tests do NOT touch code2test/ -- that's the M1D.1
architectural invariant.
"""

from __future__ import annotations

import json
import math

import pytest

from code2testbench.report import AcceptanceReport


def _r(initial, diagnosis, rewrite_attempt, rewrite_success, final,
       generation_success=1.0, vpr_before=1.0, vpr_after=1.0):
    """Convenience constructor that keeps the positional order obvious."""
    return AcceptanceReport(
        initial_acceptance_rate=initial,
        diagnosis_trigger_rate=diagnosis,
        rewrite_attempt_rate=rewrite_attempt,
        rewrite_success_rate=rewrite_success,
        final_acceptance_rate=final,
        generation_success_rate=generation_success,
        verification_pass_rate_before_rewrite=vpr_before,
        verification_pass_rate_after_rewrite=vpr_after,
    )


def test_net_improvement_subtracts_initial_from_final():
    r = _r(0.48, 0.30, 0.20, 0.50, 0.71)
    assert math.isclose(r.net_improvement(), 0.23, rel_tol=1e-9)


def test_net_improvement_negative_when_repair_makes_worse():
    r = _r(0.80, 0.10, 0.05, 0.20, 0.50)
    assert math.isclose(r.net_improvement(), -0.30, rel_tol=1e-9)


def test_net_improvement_zero_when_unchanged():
    r = _r(0.40, 0.20, 0.10, 0.10, 0.40)
    assert r.net_improvement() == 0.0


def test_from_dict_round_trip():
    src = {
        "initial_acceptance_rate": 0.50,
        "diagnosis_trigger_rate": 0.25,
        "rewrite_attempt_rate": 0.12,
        "rewrite_success_rate": 0.40,
        "final_acceptance_rate": 0.66,
        "generation_success_rate": 1.0,
        "verification_pass_rate_before_rewrite": 0.75,
        "verification_pass_rate_after_rewrite": 0.50,
    }
    r = AcceptanceReport.from_dict(src)
    assert r.initial_acceptance_rate == 0.50
    assert r.final_acceptance_rate == 0.66
    assert r.rewrite_success_rate == 0.40
    assert r.generation_success_rate == 1.0
    assert r.verification_pass_rate_before_rewrite == 0.75
    assert r.verification_pass_rate_after_rewrite == 0.50
    assert r.to_dict() == {**src, "net_improvement": pytest.approx(0.16)}


def test_from_dict_rejects_unknown_keys():
    with pytest.raises(ValueError):
        AcceptanceReport.from_dict({
            "initial_acceptance_rate": 0.5,
            "diagnosis_trigger_rate": 0.5,
            "rewrite_attempt_rate": 0.5,
            "rewrite_success_rate": 0.5,
            "final_acceptance_rate": 0.5,
            "generation_success_rate": 0.5,
            "verification_pass_rate_before_rewrite": 0.5,
            "verification_pass_rate_after_rewrite": 0.5,
            "extra_field": "no",  # not allowed
        })


def test_to_dict_contains_net_improvement():
    r = _r(0.4, 0.2, 0.1, 0.5, 0.6)
    d = r.to_dict()
    assert d["net_improvement"] == pytest.approx(0.2)
    assert set(d) == {
        "initial_acceptance_rate",
        "diagnosis_trigger_rate",
        "rewrite_attempt_rate",
        "rewrite_success_rate",
        "final_acceptance_rate",
        "generation_success_rate",
        "verification_pass_rate_before_rewrite",
        "verification_pass_rate_after_rewrite",
        "net_improvement",
    }


def test_rewrite_success_rate_independent_from_final():
    """rewrite_success_rate is per-event, final_acceptance_rate is per-run.

    A rewrite can succeed at producing a passing test (event-level) while
    the post-rewrite suite has worse outcomes than before (run-level).
    The two metrics must be tracked independently so the data can
    distinguish 'rewrite itself worked' from 'rewrite improved things'.
    """
    # 4 rewrites attempted, all of which produced a passing test
    # (rewrite_success_rate = 1.0). But only 1 of those rewrites ended
    # with a component that previously had failing tests now passing
    # all of them (final_acceptance_rate = 0.25).
    r = _r(initial=0.6, diagnosis=1.0, rewrite_attempt=1.0,
           rewrite_success=1.0, final=0.25)
    assert r.rewrite_success_rate == 1.0
    assert r.final_acceptance_rate == 0.25
    # net_improvement = -0.35: the run got worse despite every rewrite
    # producing a passing test.
    assert r.net_improvement() < 0


def test_generation_success_rate_round_trip():
    """The new rate round-trips through from_dict/to_dict without loss."""
    src = {
        "initial_acceptance_rate": 0.5,
        "diagnosis_trigger_rate": 0.5,
        "rewrite_attempt_rate": 0.5,
        "rewrite_success_rate": 0.5,
        "final_acceptance_rate": 0.5,
        "generation_success_rate": 0.75,
        "verification_pass_rate_before_rewrite": 0.5,
        "verification_pass_rate_after_rewrite": 0.5,
    }
    r = AcceptanceReport.from_dict(src)
    assert r.generation_success_rate == 0.75
    d = r.to_dict()
    assert d["generation_success_rate"] == 0.75
    assert "generation_success_rate" in d


def test_verification_pass_rates_distinguish_before_and_after():
    """verification_pass_rate_before_rewrite is the user-facing "did
    tests pass before we tried to repair?" number. verification_pass_
    rate_after_rewrite is "did tests pass after the loop ran?"

    The two metrics differ in two ways:
      - denominator: before uses _initial_total (all components
        considered), after uses _rerun_components_total (only those
        that the loop re-verified).
      - meaning: before is a closed-form rate; after is a conditional
        rate (given the loop engaged).

    A 1-component corpus with 1 failed component, where the rewrite
    succeeds and the rerun passes, gives before=0.0 and after=1.0.
    """
    r = _r(
        initial=1.0, diagnosis=1.0, rewrite_attempt=1.0,
        rewrite_success=1.0, final=1.0,
        generation_success=1.0,
        vpr_before=0.0,
        vpr_after=1.0,
    )
    assert r.verification_pass_rate_before_rewrite == 0.0
    assert r.verification_pass_rate_after_rewrite == 1.0


def test_verification_pass_rate_after_rewrite_nan_when_no_rerun():
    """When no components had a rerun event (the loop had nothing
    to repair), the after-rewrite rate is NaN -- no signal.
    """
    r = _r(
        initial=1.0, diagnosis=1.0, rewrite_attempt=1.0,
        rewrite_success=1.0, final=1.0,
        generation_success=1.0,
        vpr_before=1.0,
        vpr_after=float("nan"),
    )
    assert math.isnan(r.verification_pass_rate_after_rewrite)
