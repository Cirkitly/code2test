"""Tests for code2test/events.py — M1B.1 acceptance.

The GeneratorEvent types are pure value dataclasses. These tests verify:

* Frozen / immutable
* Field assignment via constructor works
* Tuple default for failure_ids works (not list, to keep frozen)
* null_sink() emits events without effect, returns an object that accepts the call
* Five concrete event types exist and are GeneratorEvent subclasses
"""

from __future__ import annotations

import dataclasses

import pytest

from code2test.events import (
    DiagnosisTriggered,
    GeneratorEvent,
    IntentExtracted,
    RewriteAttempted,
    TestsGenerated,
    VerificationCompleted,
    new_run_id,
    null_sink,
)


def test_new_run_id_is_unique():
    a = new_run_id()
    b = new_run_id()
    assert a != b
    assert isinstance(a, str)
    assert len(a) >= 8


def test_intent_extracted_is_frozen():
    e = IntentExtracted(run_id="r", component_id="c",
                        confidence=0.7, accepted=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.confidence = 0.5  # type: ignore[misc]


def test_all_events_subclass_generator_event():
    for cls in (IntentExtracted, TestsGenerated, VerificationCompleted,
                DiagnosisTriggered, RewriteAttempted):
        assert issubclass(cls, GeneratorEvent)


def test_intent_extracted_fields():
    e = IntentExtracted(run_id="r1", component_id="normalize_path",
                        confidence=0.92, accepted=True)
    assert e.run_id == "r1"
    assert e.component_id == "normalize_path"
    assert e.confidence == pytest.approx(0.92)
    assert e.accepted is True


def test_tests_generated_fields():
    e = TestsGenerated(run_id="r1", component_id="x",
                       test_file_path="tests/test_x.py", test_count=4)
    assert e.test_count == 4
    assert e.test_file_path == "tests/test_x.py"


def test_verification_completed_default_failure_ids_is_tuple():
    e = VerificationCompleted(run_id="r", component_id="x",
                              passed=3, failed=0)
    assert e.failure_ids == ()
    assert isinstance(e.failure_ids, tuple)


def test_verification_completed_with_failures():
    e = VerificationCompleted(run_id="r", component_id="x",
                              passed=2, failed=1,
                              failure_ids=("test_none",))
    assert e.passed + e.failed == 3
    assert e.failure_ids == ("test_none",)


def test_diagnosis_triggered_cause_is_string():
    e = DiagnosisTriggered(run_id="r", component_id="x",
                           failure_id="t1", cause="TEST_WRONG",
                           diagnosis_confidence=0.7)
    assert e.cause == "TEST_WRONG"


def test_rewrite_attempted_default_strategy():
    e = RewriteAttempted(run_id="r", component_id="x",
                         failure_id="t1", success=True)
    assert e.strategy == "test_rewrite"


def test_null_sink_accepts_any_event():
    sink = null_sink()
    ev = IntentExtracted(run_id="r", component_id="x",
                         confidence=0.5, accepted=True)
    # must not raise; result is None
    assert sink.emit(ev) is None


def test_generator_event_is_dataclass():
    assert dataclasses.is_dataclass(GeneratorEvent)
