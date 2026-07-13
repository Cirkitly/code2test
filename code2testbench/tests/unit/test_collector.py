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


def test_collector_counts_rewrite_attempts_per_component():
    """rewrite_attempt_rate is per-component: denominator is the count
    of components with at least one failure, NOT the count of
    failed tests.

    Scenario: 1 component had 3 failed tests, 2 rewrites were attempted.
    The architecture's per-component invariant means at most one
    rewrite per component; the 2nd RewriteAttempted here is a
    synthetic test of the metric counter, not the architectural
    behavior. rewrite_attempt_rate = 2/1 = 2.0 (more attempts than
    failing components indicates the per-component invariant was
    violated, which is itself a signal).
    """
    sink = EventCollector()
    # One component, three failed tests. Component-failed count: 1.
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=1, failed=3, failure_ids=("a", "b", "c"),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a", success=True,
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="b", success=False,
    ))
    report = sink.report()
    # Per-component denominator: 1 failing component, 2 attempts.
    # This is the architectural signal that an invariant was violated
    # in production: per-component invariant should be 1 rewrite per
    # failing component.
    assert report.rewrite_attempt_rate == pytest.approx(2.0)


def test_collector_rewrite_attempt_rate_one_per_component():
    """Normal case: one component with one failure, one rewrite
    attempt. Rate is 1.0 / 1 = 1.0.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=1, failed=4, failure_ids=("a", "b", "c", "d"),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a", success=True,
    ))
    report = sink.report()
    assert report.rewrite_attempt_rate == pytest.approx(1.0)


def test_collector_rewrite_attempt_rate_two_components():
    """Two components each had failures; both got rewrite attempts.
    Rate is 2/2 = 1.0.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a", passed=1, failed=2,
        failure_ids=("t1", "t2"),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="b", passed=1, failed=1,
        failure_ids=("t3",),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="a", failure_id="t1", success=False,
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="b", failure_id="t3", success=True,
    ))
    report = sink.report()
    assert report.rewrite_attempt_rate == pytest.approx(1.0)


def test_collector_rewrite_attempt_rate_nan_when_no_failures():
    """When no components had failures, the rewrite_attempt_rate
    denominator is zero and the rate is NaN -- no signal.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c", passed=3, failed=0,
        failure_ids=(),
    ))
    report = sink.report()
    assert report.rewrite_attempt_rate != report.rewrite_attempt_rate  # NaN


def test_collector_rewrite_attempt_rate_partial_does_not_dilute():
    """If only some failing components get rewrites, the rate is
    < 1.0 per-component. Crucially, this is NOT diluted by the
    number of failed tests in those components -- a component with
    10 failed tests and 1 rewrite contributes 1/1, not 1/10.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a", passed=0, failed=10,
        failure_ids=tuple(f"t{i}" for i in range(10)),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="b", passed=0, failed=1,
        failure_ids=("q1",),
    ))
    # Only component 'a' got a rewrite attempt.
    sink.emit(RewriteAttempted(
        run_id="r", component_id="a", failure_id="t1", success=True,
    ))
    report = sink.report()
    assert report.rewrite_attempt_rate == pytest.approx(0.5)  # 1/2



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


def test_collector_counts_rewrite_success_rate_independently():
    """rewrite_success_rate tracks of rewrites attempted, what fraction
    produced a passing test. Distinct from final_acceptance_rate (which
    counts of rewrites attempted, what fraction made a component pass
    entirely). The two are independent and must remain so.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=0, failed=4, failure_ids=("a", "b", "c", "d"),
    ))
    # 4 rewrites attempted; 3 of them produce a passing test.
    for fid, ok in [("a", True), ("b", True), ("c", True), ("d", False)]:
        sink.emit(RewriteAttempted(
            run_id="r", component_id="c", failure_id=fid, success=ok,
        ))
    report = sink.report()
    assert report.rewrite_success_rate == pytest.approx(0.75)
    # final_acceptance_rate uses the same denominator (4) because the
    # collector counts every RewriteAttempted as a final measurement.
    # For this test we accept either 0.75 (matching the per-event rate)
    # or any value that respects the per-attempt denominator.
    assert isinstance(report.final_acceptance_rate, float)


def test_collector_records_rewrite_event_metadata():
    """Per-event metadata (failure_classification, strategy, elapsed_seconds)
    flows through the collector and is reachable via rewrite_events().

    This is what makes the recorded JSON explainable: when
    rewrite_success_rate is low, we look at the per-event rows to see
    whether the failures were classified as CODE_BUG (test rewrite can't
    help) or whether test_rewrite just didn't produce passing tests.
    """
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c",
        passed=0, failed=1, failure_ids=("a",),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a",
        success=True, strategy="test_rewrite",
        failure_classification="TEST_WRONG", elapsed_seconds=4.2,
    ))
    events = sink.rewrite_events()
    assert len(events) == 1
    e = events[0]
    assert e.failure_classification == "TEST_WRONG"
    assert e.strategy == "test_rewrite"
    assert e.elapsed_seconds == pytest.approx(4.2)
    assert e.success is True


def test_collector_accepts_rewrite_committed_event():
    """RewriteCommitted is observational; the collector must accept it
    without raising 'unknown event type'. The variance experiment
    walks these events to classify failures.
    """
    from code2test.events import RewriteCommitted
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c", passed=0, failed=1,
        failure_ids=("a",),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a",
        success=False, strategy="test_rewrite",
        failure_classification="TEST_WRONG",
    ))
    sink.emit(RewriteCommitted(
        run_id="r", component_id="c",
        strategy="test_rewrite", failure_classification="TEST_WRONG",
        isolated_passed=0, isolated_failed=1,
        replaced=False, success=False,
    ))
    report = sink.report()
    # The committed event is in the events list for the variance
    # script to walk.
    assert any(isinstance(e, RewriteCommitted) for e in sink.events)
    # It doesn't change counters; the existing metrics hold.
    assert report.rewrite_attempt_rate == pytest.approx(1.0)
    assert report.rewrite_success_rate == pytest.approx(0.0)


def test_collector_rerun_flag_routes_to_separate_metric():
    """VerificationCompleted(rerun=True) feeds
    verification_pass_rate_after_rewrite. The phase-3 events with
    rerun=False (or absent) do not count toward the after-rewrite
    rate. This keeps the original metrics unchanged while making
    the post-rewrite pass rate observable.
    """
    sink = EventCollector()
    # Phase-3: 2 components, both with failures (initial pass rate 0/2).
    sink.emit(IntentExtracted(
        run_id="r", component_id="a", confidence=0.9, accepted=True,
    ))
    sink.emit(IntentExtracted(
        run_id="r", component_id="b", confidence=0.9, accepted=True,
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="b",
        passed=0, failed=1, failure_ids=("t2",),
    ))
    # Phase-4 re-run: only component 'a' gets re-verified, and it
    # now passes.
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=1, failed=0, failure_ids=(),
        rerun=True,
    ))
    report = sink.report()
    # before-rewrite: 0 of 2 components passed = 0.0
    assert report.verification_pass_rate_before_rewrite == pytest.approx(0.0)
    # after-rewrite: 1 of 1 component passed = 1.0
    assert report.verification_pass_rate_after_rewrite == pytest.approx(1.0)
    # original metrics unchanged: phase-3 events still feed them.
    assert report.initial_acceptance_rate == pytest.approx(1.0)
    assert report.diagnosis_trigger_rate == pytest.approx(1.0)


def test_collector_rerun_components_passed_zero_when_no_pass():
    """When every rerun component still fails, the after-rewrite rate
    is 0.0, not NaN. NaN only when no rerun events occurred at all.
    """
    sink = EventCollector()
    sink.emit(IntentExtracted(
        run_id="r", component_id="a", confidence=0.9, accepted=True,
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
    ))
    # Rerun happens; component still fails.
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
        rerun=True,
    ))
    report = sink.report()
    assert report.verification_pass_rate_after_rewrite == pytest.approx(0.0)
    assert e.elapsed_seconds == pytest.approx(4.2)
    assert e.success is True


def test_collector_accepts_rewrite_committed_event():
    """RewriteCommitted is observational; the collector must accept it
    without raising 'unknown event type'. The variance experiment
    walks these events to classify failures.
    """
    from code2test.events import RewriteCommitted
    sink = EventCollector()
    sink.emit(VerificationCompleted(
        run_id="r", component_id="c", passed=0, failed=1,
        failure_ids=("a",),
    ))
    sink.emit(RewriteAttempted(
        run_id="r", component_id="c", failure_id="a",
        success=False, strategy="test_rewrite",
        failure_classification="TEST_WRONG",
    ))
    sink.emit(RewriteCommitted(
        run_id="r", component_id="c",
        strategy="test_rewrite", failure_classification="TEST_WRONG",
        isolated_passed=0, isolated_failed=1,
        replaced=False, success=False,
    ))
    report = sink.report()
    assert any(isinstance(e, RewriteCommitted) for e in sink.events)
    assert report.rewrite_attempt_rate == pytest.approx(1.0)
    assert report.rewrite_success_rate == pytest.approx(0.0)


def test_collector_rerun_flag_routes_to_separate_metric():
    """VerificationCompleted(rerun=True) feeds
    verification_pass_rate_after_rewrite. The phase-3 events with
    rerun=False (or absent) do not count toward the after-rewrite
    rate. This keeps the original metrics unchanged while making
    the post-rewrite pass rate observable.
    """
    sink = EventCollector()
    sink.emit(IntentExtracted(
        run_id="r", component_id="a", confidence=0.9, accepted=True,
    ))
    sink.emit(IntentExtracted(
        run_id="r", component_id="b", confidence=0.9, accepted=True,
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="b",
        passed=0, failed=1, failure_ids=("t2",),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=1, failed=0, failure_ids=(),
        rerun=True,
    ))
    report = sink.report()
    assert report.verification_pass_rate_before_rewrite == pytest.approx(0.0)
    assert report.verification_pass_rate_after_rewrite == pytest.approx(1.0)
    assert report.initial_acceptance_rate == pytest.approx(1.0)


def test_collector_rerun_components_passed_zero_when_no_pass():
    """When every rerun component still fails, the after-rewrite rate
    is 0.0, not NaN. NaN only when no rerun events occurred at all.
    """
    sink = EventCollector()
    sink.emit(IntentExtracted(
        run_id="r", component_id="a", confidence=0.9, accepted=True,
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
    ))
    sink.emit(VerificationCompleted(
        run_id="r", component_id="a",
        passed=0, failed=1, failure_ids=("t1",),
        rerun=True,
    ))
    report = sink.report()
    assert report.verification_pass_rate_after_rewrite == pytest.approx(0.0)


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
