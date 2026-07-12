"""Unit tests for code2testbench.report.AcceptanceReport.

Verifies the four-number schema, the net_improvement helper, and JSON
round-trip. These tests do NOT touch code2test/ — that's the M1D.1
architectural invariant.
"""

from __future__ import annotations

import json
import math

import pytest

from code2testbench.report import AcceptanceReport


def test_net_improvement_subtracts_initial_from_final():
    r = AcceptanceReport(0.48, 0.30, 0.20, 0.71)
    assert math.isclose(r.net_improvement(), 0.23, rel_tol=1e-9)


def test_net_improvement_negative_when_repair_makes_worse():
    r = AcceptanceReport(0.80, 0.10, 0.05, 0.50)
    assert math.isclose(r.net_improvement(), -0.30, rel_tol=1e-9)


def test_net_improvement_zero_when_unchanged():
    r = AcceptanceReport(0.40, 0.20, 0.10, 0.40)
    assert r.net_improvement() == 0.0


def test_from_dict_round_trip():
    src = {
        "initial_acceptance_rate": 0.50,
        "diagnosis_trigger_rate": 0.25,
        "rewrite_attempt_rate": 0.12,
        "final_acceptance_rate": 0.66,
    }
    r = AcceptanceReport.from_dict(src)
    assert r.initial_acceptance_rate == 0.50
    assert r.final_acceptance_rate == 0.66
    assert r.to_dict() == {**src, "net_improvement": pytest.approx(0.16)}


def test_from_dict_rejects_unknown_keys():
    with pytest.raises(ValueError):
        AcceptanceReport.from_dict({
            "initial_acceptance_rate": 0.5,
            "diagnosis_trigger_rate": 0.5,
            "rewrite_attempt_rate": 0.5,
            "final_acceptance_rate": 0.5,
            "extra_field": "no",  # not allowed
        })


def test_to_dict_contains_net_improvement():
    r = AcceptanceReport(0.4, 0.2, 0.1, 0.6)
    d = r.to_dict()
    assert d["net_improvement"] == pytest.approx(0.2)
    assert set(d) == {
        "initial_acceptance_rate",
        "diagnosis_trigger_rate",
        "rewrite_attempt_rate",
        "final_acceptance_rate",
        "net_improvement",
    }
