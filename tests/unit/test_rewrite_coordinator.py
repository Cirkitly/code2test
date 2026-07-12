"""Unit tests for code2test.agents.rewrite_coordinator.

The coordinator is a behavioral module: every invariant in its
docstring is enforced here. Future strategy additions extend these
tests; nothing else.

Test surface:
  * select_strategy: pure-function classifier for DiagnosisCause.
  * RewriteCoordinator: orchestration with mocked agents + verifier.
    Per-component idempotency. Transactional on verifier failure.
    Strategy routing for TEST_WRONG / INTENT_WRONG / CODE_BUG /
    unknown-cause.
  * RewriteOutcome: per-event telemetry fields populated by the
    coordinator's return values.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from code2test.agents.rewrite_coordinator import (
    RewriteCoordinator,
    RewriteOutcome,
    Strategy,
    select_strategy,
)
from code2test.core.models import (
    Diagnosis,
    DiagnosisCause,
    Intent,
    TestCase,
    TestFile,
    TestFramework,
    TestStatus,
)


# ---------- helpers -------------------------------------------------------

def _make_intent(component_id: str = "comp") -> Intent:
    return Intent(
        component_id=component_id,
        component_path="f.py",
        intent_text="returns x",
        confidence=0.9,
    )


def _make_test_file(failing: List[str], passing: List[str]) -> TestFile:
    cases = []
    for name in failing:
        cases.append(TestCase(
            name=name, intent_text="", test_code="def test(): pass",
            status=TestStatus.FAILED, failure_message="x",
        ))
    for name in passing:
        cases.append(TestCase(
            name=name, intent_text="", test_code="def test(): pass",
            status=TestStatus.PASSED,
        ))
    return TestFile(
        path="f_test.py", component_id="comp", component_path="f.py",
        test_cases=cases, framework=TestFramework.PYTEST,
    )


def _make_diagnosis(cause: DiagnosisCause) -> Diagnosis:
    return Diagnosis(
        test_name="t", cause=cause, confidence=0.8, explanation="",
    )


def _make_verifier(*, all_passed: bool, syntax_valid: bool = True) -> Any:
    """Build a mock verifier that always passes or fails."""
    verifier = MagicMock()
    verifier.validate_syntax.return_value = (syntax_valid, "")
    result = MagicMock()
    result.all_passed = all_passed
    result.failed = [] if all_passed else ["t1", "t2"]
    verifier.run_tests.return_value = result
    return verifier


def _make_test_agent(new_test_file: TestFile) -> Any:
    agent = MagicMock()
    agent.generate_unit_tests = AsyncMock(return_value=new_test_file)
    return agent


def _make_intent_agent(new_intent: Intent) -> Any:
    agent = MagicMock()
    agent.infer_intent = AsyncMock(return_value=new_intent)
    return agent


def _run(coro):
    """Run an awaitable to completion synchronously."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    # If a loop is already running (rare in tests), we can't block on it.
    raise RuntimeError(
        "_run() called from a running event loop; use await directly."
    )


# ---------- select_strategy ----------------------------------------------

def test_select_strategy_test_wrong_routes_to_test_rewrite():
    assert select_strategy(DiagnosisCause.TEST_WRONG) is Strategy.TEST_REWRITE


def test_select_strategy_intent_wrong_routes_to_intent_rewrite():
    assert select_strategy(DiagnosisCause.INTENT_WRONG) is Strategy.INTENT_REWRITE


def test_select_strategy_code_bug_routes_to_skip():
    assert select_strategy(DiagnosisCause.CODE_BUG) is Strategy.SKIP


def test_select_strategy_unknown_cause_routes_to_skip():
    """Unknown causes default to SKIP -- don't burn LLM budget."""
    assert select_strategy("UNKNOWN_CAUSE") is Strategy.SKIP
    assert select_strategy(None) is Strategy.SKIP


def test_select_strategy_accepts_string_for_backward_compat():
    """The diagnosis agent's DiagnosisResult declares cause as a string;
    the canonical Diagnosis model uses the enum. The classifier must
    accept both without forcing callers to translate.
    """
    assert select_strategy("TEST_WRONG") is Strategy.TEST_REWRITE
    assert select_strategy("INTENT_WRONG") is Strategy.INTENT_REWRITE
    assert select_strategy("CODE_BUG") is Strategy.SKIP


# ---------- RewriteCoordinator: SKIP path ---------------------------------

def test_coordinator_skip_strategy_does_not_call_agents():
    """CODE_BUG -> SKIP. No LLM call, no verifier call."""
    verifier = _make_verifier(all_passed=True)
    test_agent = _make_test_agent(_make_test_file([], []))
    intent_agent = _make_intent_agent(_make_intent())

    coord = RewriteCoordinator(
        test_agent=test_agent, intent_agent=intent_agent, verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.CODE_BUG),
    ))

    assert outcome.strategy is Strategy.SKIP
    assert outcome.success is False
    assert outcome.failure_classification == "CODE_BUG"
    test_agent.generate_unit_tests.assert_not_called()
    intent_agent.infer_intent.assert_not_called()
    verifier.validate_syntax.assert_not_called()


def test_coordinator_skip_carries_telemetry():
    """SKIP outcomes still carry all six telemetry fields so the
    recorded JSON can explain why a CODE_BUG failure was not rewritten.
    """
    verifier = _make_verifier(all_passed=True)
    coord = RewriteCoordinator(
        test_agent=_make_test_agent(_make_test_file([], [])),
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1", "t2", "t3"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.CODE_BUG),
    ))
    assert outcome.failure_classification == "CODE_BUG"
    assert outcome.strategy is Strategy.SKIP
    assert outcome.tests_before == 3
    assert outcome.tests_after == 3  # unchanged
    assert outcome.success is False
    assert outcome.new_test_file is None


# ---------- RewriteCoordinator: TEST_REWRITE path ------------------------

def test_coordinator_test_rewrite_success_commits_candidate():
    """TEST_WRONG -> TEST_REWRITE. Verifier passes -> new_test_file
    is returned for the caller's commit step.
    """
    original = _make_test_file(["t1"], [])
    candidate = _make_test_file([], ["t1"])
    verifier = _make_verifier(all_passed=True)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=original, component={"id": "comp"},
        intent=_make_intent(), diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.strategy is Strategy.TEST_REWRITE
    assert outcome.success is True
    assert outcome.new_test_file is candidate
    assert outcome.failure_classification == "TEST_WRONG"
    assert outcome.tests_before == 1
    assert outcome.tests_after == 0  # all-passed verifier returns empty failed list
    test_agent.generate_unit_tests.assert_called_once()
    intent_agent_call = coord._intent_agent.infer_intent
    intent_agent_call.assert_not_called()  # TEST_REWRITE doesn't re-extract


def test_coordinator_test_rewrite_failure_discards_candidate():
    """Verifier rejects the rewrite -> outcome.success=False and
    new_test_file is None so the caller preserves the original.
    """
    original = _make_test_file(["t1"], [])
    candidate = _make_test_file(["t1"], [])  # verifier says all_passed=False
    verifier = _make_verifier(all_passed=False)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=original, component={"id": "comp"},
        intent=_make_intent(), diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.success is False
    assert outcome.new_test_file is None
    assert outcome.tests_before == 1
    assert outcome.tests_after == 2  # verifier result said ["t1", "t2"]
    test_agent.generate_unit_tests.assert_called_once()


def test_coordinator_test_rewrite_syntax_failure_short_circuits():
    """If validate_syntax returns invalid, the verifier doesn't run."""
    candidate = _make_test_file([], ["t1"])
    verifier = _make_verifier(all_passed=True, syntax_valid=False)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.success is False
    assert outcome.new_test_file is None
    assert "syntactically invalid" in outcome.explanation
    verifier.validate_syntax.assert_called_once()
    verifier.run_tests.assert_not_called()


def test_coordinator_test_rewrite_records_elapsed_time():
    """elapsed_seconds is positive and bounded by a reasonable upper
    limit. Real LLM calls may take seconds; the coordinator's
    bookkeeping is wall-clock, not LLM-token-counted.
    """
    candidate = _make_test_file([], ["t1"])
    verifier = _make_verifier(all_passed=True)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.elapsed_seconds >= 0.0
    assert outcome.elapsed_seconds < 5.0  # mocked; should be near-zero


# ---------- RewriteCoordinator: INTENT_REWRITE path ----------------------

def test_coordinator_intent_rewrite_re_extracts_intent_then_rewrites():
    """INTENT_WRONG -> INTENT_REWRITE. The intent_agent is called
    before the test_agent. The new intent flows into test generation.
    """
    new_intent = Intent(
        component_id="comp", component_path="f.py",
        intent_text="corrected intent", confidence=0.95,
    )
    candidate = _make_test_file([], ["t1"])
    verifier = _make_verifier(all_passed=True)
    intent_agent = _make_intent_agent(new_intent)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent, intent_agent=intent_agent, verifier=verifier,
    )
    original_intent = _make_intent()  # the original
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=original_intent,
        diagnosis=_make_diagnosis(DiagnosisCause.INTENT_WRONG),
    ))
    assert outcome.strategy is Strategy.INTENT_REWRITE
    assert outcome.success is True
    assert outcome.new_test_file is candidate
    intent_agent.infer_intent.assert_called_once()
    test_agent.generate_unit_tests.assert_called_once()
    # The test_agent was called with the *new* intent, not the original.
    call_args = test_agent.generate_unit_tests.call_args
    # args: (component, intent, framework). kwargs also possible.
    if call_args.kwargs:
        assert call_args.kwargs.get("intent") is new_intent
    else:
        assert call_args.args[1] is new_intent


# ---------- Per-component invariant ---------------------------------------

def test_coordinator_per_component_invariant_enforced():
    """A second attempt_rewrite for the same (run, component) returns
    SKIP without calling any agent or verifier. This is the
    architectural invariant: never twice per component per run.
    """
    candidate = _make_test_file([], ["t1"])
    verifier = _make_verifier(all_passed=True)
    test_agent = _make_test_agent(candidate)

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )

    # First call: real work.
    out1 = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert out1.success is True

    # Second call: SKIP without LLM/verifier calls.
    out2 = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert out2.strategy is Strategy.SKIP
    assert "per-component invariant" in out2.explanation

    # Only the first call hit the test_agent.
    assert test_agent.generate_unit_tests.call_count == 1


def test_coordinator_per_run_reset_for_different_components():
    """The per-component invariant is per (run_id, component_id),
    not per component_id alone. A different component in the same
    run gets a fresh attempt.
    """
    verifier = _make_verifier(all_passed=True)
    test_agent = _make_test_agent(_make_test_file([], ["t1"]))

    coord = RewriteCoordinator(
        test_agent=test_agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    out_a = _run(coord.attempt_rewrite(
        run_id="r", component_id="a",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "a"}, intent=_make_intent("a"),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    out_b = _run(coord.attempt_rewrite(
        run_id="r", component_id="b",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "b"}, intent=_make_intent("b"),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert out_a.success is True
    assert out_b.success is True
    assert test_agent.generate_unit_tests.call_count == 2


# ---------- Telemetry contract -------------------------------------------

def test_rewrite_outcome_carries_tests_before_and_after():
    """The telemetry contract: every outcome has tests_before and
    tests_after counts, plus elapsed_seconds. This is what makes
    the benchmark explainable.
    """
    candidate = _make_test_file([], ["t1", "t2"])
    verifier = _make_verifier(all_passed=True)
    coord = RewriteCoordinator(
        test_agent=_make_test_agent(candidate),
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=verifier,
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1", "t2", "t3"], ["p1"]),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.tests_before == 3   # 3 failed in original
    assert outcome.tests_after == 0    # verifier said all passed
    assert outcome.elapsed_seconds >= 0.0
    assert outcome.failure_classification == "TEST_WRONG"


def test_already_attempted_reflects_invariant_state():
    """already_attempted is observable: the generator can check
    whether to even emit a DiagnosisTriggered, since the rewrite
    path is closed for already-attempted components.
    """
    coord = RewriteCoordinator(
        test_agent=_make_test_agent(_make_test_file([], [])),
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=_make_verifier(all_passed=True),
    )
    assert not coord.already_attempted("r", "comp")
    _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.CODE_BUG),
    ))
    assert coord.already_attempted("r", "comp")
    assert not coord.already_attempted("r", "other")
    assert not coord.already_attempted("other_run", "comp")


def test_exception_during_rewrite_returns_failure_outcome_not_raises():
    """If the test_agent raises, the coordinator records a SKIP-like
    failure outcome (strategy still reflects what was attempted)
    rather than crashing the run.
    """
    agent = MagicMock()
    agent.generate_unit_tests = AsyncMock(side_effect=RuntimeError("LLM down"))
    coord = RewriteCoordinator(
        test_agent=agent,
        intent_agent=_make_intent_agent(_make_intent()),
        verifier=_make_verifier(all_passed=True),
    )
    outcome = _run(coord.attempt_rewrite(
        run_id="r", component_id="comp",
        original_test_file=_make_test_file(["t1"], []),
        component={"id": "comp"}, intent=_make_intent(),
        diagnosis=_make_diagnosis(DiagnosisCause.TEST_WRONG),
    ))
    assert outcome.success is False
    assert outcome.new_test_file is None
    assert "RuntimeError" in outcome.explanation
    assert "LLM down" in outcome.explanation
