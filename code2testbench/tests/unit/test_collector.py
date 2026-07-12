"""Unit tests for code2testbench.collector.EventCollector.

The collector implements the sink contract from code2test.events and
must produce a valid AcceptanceReport from a synthetic event stream.
"""

from __future__ import annotations

import math
from datetime import datetime

import pytest

from code2test.events import (
    DiagnosisTriggered,
    IntentExtracted,
    RewriteAttempted,
    TestsGenerated,
    VerificationCompleted,
)

from code2testbench.collector import EventCollector
from code2testbench.report import AcceptanceReport


def test_collector_empty_run_yields_nan():
    sink = EventCollector()
    report = sink.report()
    assert math.isnan(report.initial_acceptance_rate)
    assert math.isnan(report.diagnosis_trigger_rate)
    assert math.isnan(report.rewrite_attempt_rate)
    assert math.isnan(report.final_acceptance_rate)


def test_collector_counts_initial_acceptance():
    sink = EventCollector()
    for i in range(4):
        sink.emit(IntentExtracted(
            run_id="r", component_id=f"c{i}",
            confidence=0.5, accepted=True,
        ))
    sink.emit(IntentExtracted(
        run_id="r", component_id="c4", confidence=0.3, accepted=False,
    ))
    report = sink.report()
    assert report.initial_acceptance_rate == pytest.approx(0.8)


def test_collector_counts_diagnosis_triggered():
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=2, failed=2, failure_ids=("a", "b"),
    ))
    sink.emit(DiagnosisTriggered(
        run_id="r", component_id="c", failure_id="a",
        cause="TEST_WRONG", diagnosis_confidence=0.7,
    ))
    report = sink.report()
    # 1 diagnosis triggered out of 2 failures = 0.5
    assert report.diagnosis_trigger_rate == pytest.approx(0.5)


def test_collector_counts_rewrite_attempts():
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=1, failed=3, failure_ids=("a", "b", "c"),
    ))
    # only 2 of 3 failures trigger rewrites
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a", success=True,
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="b", success=False,
    ))
    report = sink.report()
    # 2 attempts out of 3 failures = 0.6666...
    assert report.rewrite_attempt_rate == pytest.approx(2/3)


def test_collector_counts_final_acceptance_as_successful_rewrites():
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=1, failed=2, failure_ids=("a", "b"),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a", success=True,
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="b", success=True,
    ))
    report = sink.report()
    # 2 successful rewrites out of 2 attempts = 1.0
    assert report.final_acceptance_rate == pytest.approx(1.0)


def test_collector_unknown_event_raises():
    sink = EventCollector()
    class Surprise:
        pass
    with pytest.raises(TypeError, match="does not understand"):
        sink.emit(Surprise())


def test_collector_intent_with_low_confidence_counts_as_rejected():
    sink = EventCollector()
    sink.emit(IntentExtracted(run_id="r", component_id="c",
                              confidence=0.10, accepted=False))
    sink.emit(IntentExtracted(run_id="r", component_id="d",
                              confidence=0.95, accepted=True))
    report = sink.report()
    assert report.initial_acceptance_rate == pytest.approx(0.5)
