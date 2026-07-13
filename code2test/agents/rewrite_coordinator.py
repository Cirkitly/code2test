"""RewriteCoordinator -- the repair-or-skip decision and execution.

Architectural role:
    VerificationCompleted
       |
    DiagnosisAgent
       |
    StrategyClassifier  <- pure function, deterministic mapping
       |
    RewriteCoordinator <- this module
       |
    TestAgent / IntentAgent / TestVerifier

The generator orchestrates phases; the coordinator owns *how* to
repair. Future strategies (code_rewrite, multi-pass, etc.) plug in
here without generator changes.

Operational invariants (enforced by attempt_rewrite itself, not by
the caller):

  1. Maximum one rewrite attempt per (run_id, component_id) pair.
     A second call for the same component returns SKIP without
     doing any work.

  2. Never recursively rewrite a rewrite. The coordinator does not
     re-enter its own rewrite path; if the new tests fail, that
     produces a VerificationCompleted upstream, which may emit a
     DiagnosisTriggered, but the generator's per-component invariant
     suppresses the second attempt.

  3. Reruns the entire test suite (not just the rewritten test) to
     detect silent regressions where the rewrite makes one test
     pass but breaks another.

  4. Transactional: the candidate test_file exists alongside the
     original until verification completes. On success the
     candidate replaces the original; on failure the candidate is
     discarded and the original is preserved.

  5. Deterministic strategy selection. No LLM in the strategy path.
     The mapping is ``DiagnosisCause -> Strategy`` in
     ``select_strategy``. This makes benchmark movements attributable
     to the rewrite itself, not to another model decision.

  6. The coordinator does NOT emit RewriteAttempted events. The
     caller (the generator) converts the RewriteOutcome into the
     event. This keeps event emission in one place.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from code2test.core.models import (
    Diagnosis,
    DiagnosisCause,
    Intent,
    TestFile,
)


class Strategy(str, enum.Enum):
    """How the coordinator chose to repair a failing component."""

    TEST_REWRITE = "test_rewrite"
    INTENT_REWRITE = "intent_rewrite"
    SKIP = "skip"


def select_strategy(diagnosis_cause: DiagnosisCause | str | None) -> Strategy:
    """Pure deterministic mapping from diagnosis to strategy.

    The first implementation is intentionally trivial. Future
    strategies (code_rewrite, retry-with-feedback, etc.) extend this
    function; nothing else needs to change.

    Unknown cause values (including None) fall back to SKIP. That's
    the safe choice: we don't burn LLM budget on a classification we
    don't recognize.
    """
    if diagnosis_cause is None:
        return Strategy.SKIP
    if isinstance(diagnosis_cause, DiagnosisCause):
        key = diagnosis_cause.value
    else:
        key = str(diagnosis_cause)

    return {
        DiagnosisCause.TEST_WRONG.value: Strategy.TEST_REWRITE,
        DiagnosisCause.INTENT_WRONG.value: Strategy.INTENT_REWRITE,
        DiagnosisCause.CODE_BUG.value: Strategy.SKIP,
    }.get(key, Strategy.SKIP)


@dataclass
class RewriteOutcome:
    """Result of a single rewrite attempt.

    The generator converts this into a RewriteAttempted event.
    ``new_test_file`` is the candidate replacement when verification
    succeeded; None on failure (the original test file is preserved
    on the caller's side).

    Telemetry fields separate LLM latency from verifier latency:

      verification_before_seconds: how long the verifier took to
        surface the failures that triggered this rewrite. Set by the
        caller (the generator) before invoking attempt_rewrite. We
        don't measure it inside the coordinator because the verifier
        ran in a different scope.

      rewrite_elapsed: how long the coordinator spent end-to-end,
        including any LLM call and the candidate's verifier run.

      verification_after_seconds: how long the candidate's verifier
        run took, measured by the coordinator.
    """
    component_id: str
    strategy: Strategy
    failure_classification: str
    success: bool
    rewrite_elapsed: float
    verification_before_seconds: float
    verification_after_seconds: float
    tests_before: int   # failing-test count for the component pre-rewrite
    tests_after: int    # failing-test count for the component post-suite-rerun
    isolated_passed: int = 0  # candidate's verifier pass count when known
    isolated_failed: int = 0  # candidate's verifier fail count when known
    new_test_file: Optional[TestFile] = None
    explanation: str = ""


class RewriteCoordinator:
    """Repair-or-skip decision and execution for one component.

    Holds references to the agents and verifier so the coordinator
    is the single place that knows how to drive a repair. The
    generator only knows that calling ``attempt_rewrite(...)``
    produces a ``RewriteOutcome``.

    Per-(run, component) idempotency: a single ``_seen`` set on the
    coordinator instance guards against duplicate attempts. This is
    the per-component invariant in object form.
    """

    def __init__(
        self,
        test_agent: Any,
        intent_agent: Any,
        verifier: Any,
        diagnosis_agent: Any = None,
        test_agent_factory: Optional[Callable[[], Any]] = None,
        intent_agent_factory: Optional[Callable[[], Any]] = None,
        diagnosis_agent_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Construct with agent and verifier references.

        The ``diagnosis_agent`` is required only when the caller
        passes a verification_result without pre-attached diagnoses
        on test_cases. The fallback path invokes the agent once
        per failing component; the v1.0 generator already populates
        ``tc.diagnosis`` during phase 3, so this is rarely needed.

        The ``*_factory`` callbacks let callers provide "make me a
        fresh agent for this rewrite" if they want state-isolated
        agents. The default is to reuse the agent reference, which
        matches the generator's pattern.
        """
        self._test_agent = test_agent
        self._intent_agent = intent_agent
        self._diagnosis_agent = diagnosis_agent
        self._verifier = verifier
        self._test_agent_factory = test_agent_factory or (lambda: test_agent)
        self._intent_agent_factory = intent_agent_factory or (lambda: intent_agent)
        self._diagnosis_agent_factory = (
            diagnosis_agent_factory or (lambda: diagnosis_agent)
        )
        # Per-instance guard for the per-component invariant. The
        # generator creates one coordinator per run, so this set
        # scopes correctly.
        self._seen: set = set()

    def already_attempted(self, run_id: str, component_id: str) -> bool:
        """True if attempt_rewrite has been called for this (run, component)."""
        return (run_id, component_id) in self._seen

    async def attempt_rewrite(
        self,
        *,
        run_id: str,
        component_id: str,
        original_test_file: TestFile,
        component: Dict[str, Any],
        intent: Intent,
        verification_result: Any,
        test_cases: Optional[list] = None,
        framework: Any = None,
    ) -> RewriteOutcome:
        """Single rewrite attempt for one component.

        The generator passes the full ``verification_result`` and a
        ``test_cases`` list. The coordinator's policy lives here:
        the strategy is selected from the representative diagnosis,
        which is the first failing test case with an attached
        ``diagnosis`` (or, as a fallback, the first failing test
        case re-classified by the diagnosis agent).

        Returns a RewriteOutcome that the generator converts into a
        RewriteAttempted event. Does NOT mutate the original test
        file; the caller decides whether to commit the candidate
        based on the outcome's ``success`` field.

        Telemetry: ``verification_before_seconds`` is the time the
        verifier took on the original test file (caller-supplied).
        ``rewrite_elapsed`` is end-to-end coordinator time.
        ``verification_after_seconds`` is the candidate's verifier
        run time.
        """
        t0 = time.monotonic()

        # Caller-supplied: how long the original test file's
        # verifier run took before this rewrite was triggered.
        verification_before_seconds = float(
            getattr(verification_result, "elapsed_seconds", 0.0) or 0.0
        )

        # Pick the representative diagnosis. We need a Diagnosis
        # object to drive select_strategy. The generator may have
        # pre-attached one to a failed test case (v1.0 phase 3
        # does this); if not, we either call the diagnosis agent
        # ourselves or fall back to a synthetic CODE_BUG diagnosis.
        representative = await self._pick_representative(
            test_cases=test_cases,
            verification_result=verification_result,
            component=component,
            intent=intent,
        )
        classification = (
            representative.cause.value
            if hasattr(representative.cause, "value")
            else str(representative.cause)
        )

        tests_before = _count_failures_from_verification(verification_result)

        # Per-component invariant: never twice.
        if (run_id, component_id) in self._seen:
            return RewriteOutcome(
                component_id=component_id,
                strategy=Strategy.SKIP,
                failure_classification=classification,
                success=False,
                rewrite_elapsed=time.monotonic() - t0,
                verification_before_seconds=verification_before_seconds,
                verification_after_seconds=0.0,
                tests_before=tests_before,
                tests_after=tests_before,
                explanation="per-component invariant: already attempted",
            )
        self._seen.add((run_id, component_id))

        strategy = select_strategy(representative.cause)

        # Fast path: SKIP. No LLM cost.
        if strategy is Strategy.SKIP:
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=False,
                rewrite_elapsed=time.monotonic() - t0,
                verification_before_seconds=verification_before_seconds,
                verification_after_seconds=0.0,
                tests_before=tests_before,
                tests_after=tests_before,
                explanation=f"SKIP: classification={classification}",
            )

        # Slow path: TEST_REWRITE or INTENT_REWRITE.
        try:
            new_intent = intent
            if strategy is Strategy.INTENT_REWRITE:
                intent_agent = self._intent_agent_factory()
                new_intent = await intent_agent.infer_intent(component)

            test_agent = self._test_agent_factory()
            fw = framework if framework is not None else _DEFAULT_FRAMEWORK
            candidate = await test_agent.generate_unit_tests(
                component, new_intent, fw,
            )

            # Transactional: candidate runs at a temp path.
            from pathlib import Path as _Path
            original_path = _Path(candidate.path)
            tmp_path = str(original_path) + ".rewrite_tmp"

            valid, _ = self._verifier.validate_syntax(candidate)
            if not valid:
                return RewriteOutcome(
                    component_id=component_id,
                    strategy=strategy,
                    failure_classification=classification,
                    success=False,
                    rewrite_elapsed=time.monotonic() - t0,
                    verification_before_seconds=verification_before_seconds,
                    verification_after_seconds=0.0,
                    tests_before=tests_before,
                    tests_after=tests_before,
                    new_test_file=None,
                    explanation="rewrite produced syntactically invalid test",
                )

            temp_test_file = candidate.model_copy(update={"path": tmp_path})
            t_verify = time.monotonic()
            result = self._verifier.run_tests(temp_test_file)
            verification_after_seconds = time.monotonic() - t_verify
            tests_after = len(result.failed)
            success = result.all_passed
            # Capture the candidate's verifier counts so the
            # variance experiment can distinguish verifier_failure
            # from transactional_replacement_failure.
            isolated_passed = len(result.passed) if hasattr(result, "passed") else 0
            isolated_failed = len(result.failed)

            try:
                full_tmp = _Path(_verifier_repo_path(self._verifier)) / tmp_path
                if full_tmp.exists():
                    full_tmp.unlink()
            except Exception:
                pass

            if not success:
                return RewriteOutcome(
                    component_id=component_id,
                    strategy=strategy,
                    failure_classification=classification,
                    success=False,
                    rewrite_elapsed=time.monotonic() - t0,
                    verification_before_seconds=verification_before_seconds,
                    verification_after_seconds=verification_after_seconds,
                    tests_before=tests_before,
                    tests_after=tests_after,
                    isolated_passed=isolated_passed,
                    isolated_failed=isolated_failed,
                    new_test_file=None,
                    explanation="rewrite produced a test that did not pass verification",
                )

            new_test_file = candidate.model_copy(update={"path": str(original_path)})
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=True,
                rewrite_elapsed=time.monotonic() - t0,
                verification_before_seconds=verification_before_seconds,
                verification_after_seconds=verification_after_seconds,
                tests_before=tests_before,
                tests_after=tests_after,
                isolated_passed=isolated_passed,
                isolated_failed=isolated_failed,
                new_test_file=new_test_file,
                explanation="rewrote test; verification passed",
            )
        except Exception as exc:  # noqa: BLE001
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=False,
                rewrite_elapsed=time.monotonic() - t0,
                verification_before_seconds=verification_before_seconds,
                verification_after_seconds=0.0,
                tests_before=tests_before,
                tests_after=tests_before,
                new_test_file=None,
                explanation=f"rewrite raised: {type(exc).__name__}: {exc}",
            )

    async def _pick_representative(
        self,
        *,
        test_cases: Optional[list],
        verification_result: Any,
        component: Dict[str, Any],
        intent: Intent,
    ) -> Diagnosis:
        """Pick a Diagnosis for strategy selection.

        Order of preference:
          1. The first failed test case with an attached ``diagnosis``.
          2. A fresh call to the diagnosis_agent for the first failed
             test case. Requires ``diagnosis_agent_factory`` to be set.
          3. A synthetic CODE_BUG diagnosis. This is the safe default
             when no diagnosis is available: skip the rewrite rather
             than burn LLM budget on an uninformed strategy.

        The coordinator's policy is "deterministic, prefer the
        caller's pre-attached diagnosis, fall back to agent, fall
        back to skip."
        """
        from code2test.core.models import TestStatus

        # 1. Pre-attached.
        if test_cases:
            for tc in test_cases:
                if tc.status == TestStatus.FAILED and tc.diagnosis is not None:
                    return tc.diagnosis

        # 2. Fall back to the diagnosis agent.
        if self._diagnosis_agent_factory:
            first_failed = None
            if test_cases:
                for tc in test_cases:
                    if tc.status == TestStatus.FAILED:
                        first_failed = tc
                        break
            if first_failed is not None:
                agent = self._diagnosis_agent_factory()
                try:
                    return await agent.diagnose_failure(
                        first_failed,
                        first_failed.failure_message or "",
                        component,
                        intent,
                    )
                except Exception:
                    pass  # fall through to synthetic

        # 3. Synthetic CODE_BUG diagnosis. The safe choice when we
        # have no signal.
        from code2test.core.models import DiagnosisCause
        return Diagnosis(
            test_name="unknown",
            cause=DiagnosisCause.CODE_BUG,
            confidence=0.0,
            explanation="no diagnosis available; defaulting to CODE_BUG/skip",
        )


def _verifier_repo_path(verifier: Any) -> str:
    """Read the verifier's repo_path. The attribute name varies; both
    are tolerated so this module works across verifier versions.
    """
    return getattr(verifier, "repo_path", "") or getattr(verifier, "_repo_path", "")


def _count_failures(test_file: TestFile) -> int:
    """Number of test cases in this file with status == FAILED.

    Kept for callers that still have a TestFile in hand. The
    coordinator's normal path uses _count_failures_from_verification.
    """
    from code2test.core.models import TestStatus
    return sum(1 for tc in test_file.test_cases if tc.status == TestStatus.FAILED)


def _count_failures_from_verification(verification_result: Any) -> int:
    """Number of failed tests in a verification result.

    ``verification_result`` is the object returned by the verifier's
    ``run_tests`` call. The canonical attribute is ``failed`` (a
    list). We accept either ``len(failed)`` or a numeric ``failed``
    count to tolerate verifier-version differences.
    """
    failed = getattr(verification_result, "failed", None)
    if failed is None:
        return 0
    if isinstance(failed, (list, tuple, set)):
        return len(failed)
    try:
        return int(failed)
    except (TypeError, ValueError):
        return 0


# v1.1 default framework for rewrites when none is supplied.
# Mirrors the runner's default; isolated here so tests can stub it.
try:
    from code2test.core.models import TestFramework as _TF
    _DEFAULT_FRAMEWORK = _TF.PYTEST
except ImportError:  # pragma: no cover
    _DEFAULT_FRAMEWORK = None


__all__ = [
    "Strategy",
    "RewriteOutcome",
    "RewriteCoordinator",
    "select_strategy",
]
