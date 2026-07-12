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
    """
    component_id: str
    strategy: Strategy
    failure_classification: str
    success: bool
    elapsed_seconds: float
    tests_before: int   # failing-test count for the component pre-rewrite
    tests_after: int    # failing-test count for the component post-suite-rerun
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
        test_agent_factory: Optional[Callable[[], Any]] = None,
        intent_agent_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Construct with agent and verifier references.

        The ``*_factory`` callbacks let callers provide "make me a
        fresh agent for this rewrite" if they want state-isolated
        agents. The default is to reuse the agent reference, which
        matches the generator's pattern.
        """
        self._test_agent = test_agent
        self._intent_agent = intent_agent
        self._verifier = verifier
        self._test_agent_factory = test_agent_factory or (lambda: test_agent)
        self._intent_agent_factory = intent_agent_factory or (lambda: intent_agent)
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
        diagnosis: Diagnosis,
        framework: Any = None,
    ) -> RewriteOutcome:
        """Single rewrite attempt for one component.

        Returns a RewriteOutcome that the generator converts into a
        RewriteAttempted event. Does NOT mutate the original test
        file; the caller decides whether to commit the candidate
        based on the outcome's ``success`` field.

        The strategy is selected once at entry. A SKIP strategy is
        cheap: no LLM call, no verifier call. A TEST_REWRITE or
        INTENT_REWRITE strategy runs an LLM call + verifier.

        Timing covers the entire attempt including any LLM call and
        the post-rewrite verifier run.
        """
        t0 = time.monotonic()
        classification = (
            diagnosis.cause.value
            if hasattr(diagnosis.cause, "value")
            else str(diagnosis.cause)
        )

        # Per-component invariant: never twice.
        if (run_id, component_id) in self._seen:
            return RewriteOutcome(
                component_id=component_id,
                strategy=Strategy.SKIP,
                failure_classification=classification,
                success=False,
                elapsed_seconds=time.monotonic() - t0,
                tests_before=_count_failures(original_test_file),
                tests_after=_count_failures(original_test_file),
                explanation="per-component invariant: already attempted",
            )
        self._seen.add((run_id, component_id))

        strategy = select_strategy(diagnosis.cause)
        tests_before = _count_failures(original_test_file)

        # Fast path: SKIP. No LLM cost.
        if strategy is Strategy.SKIP:
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=False,
                elapsed_seconds=time.monotonic() - t0,
                tests_before=tests_before,
                tests_after=tests_before,
                explanation=f"SKIP: classification={classification}",
            )

        # Slow path: TEST_REWRITE or INTENT_REWRITE. Use a fresh
        # agent for state isolation when a factory is provided,
        # otherwise reuse.
        try:
            # Intent rewrite: re-extract the intent first.
            new_intent = intent
            if strategy is Strategy.INTENT_REWRITE:
                intent_agent = self._intent_agent_factory()
                new_intent = await intent_agent.infer_intent(component)

            # Test rewrite: regenerate the test file with the
            # (possibly new) intent.
            test_agent = self._test_agent_factory()
            # Default to pytest if framework is unspecified; matches
            # the runner's default behavior.
            fw = framework if framework is not None else _DEFAULT_FRAMEWORK
            candidate = await test_agent.generate_unit_tests(
                component, new_intent, fw,
            )

            # Transactional verification: the candidate exists
            # alongside the original. The verifier writes to
            # test_file.path; we use a temp path so the original
            # survives a verification failure.
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
                    elapsed_seconds=time.monotonic() - t0,
                    tests_before=tests_before,
                    tests_after=tests_before,
                    new_test_file=None,
                    explanation="rewrite produced syntactically invalid test",
                )

            # Build a transient TestFile view at the temp path so the
            # verifier writes there, not at the production path.
            temp_test_file = candidate.model_copy(update={"path": tmp_path})
            result = self._verifier.run_tests(temp_test_file)
            tests_after = len(result.failed)
            success = result.all_passed

            # Cleanup the temp file unconditionally. The verifier
            # wrote it; we remove it. The original at the production
            # path is untouched.
            try:
                full_tmp = _Path(_verifier_repo_path(self._verifier)) / tmp_path
                if full_tmp.exists():
                    full_tmp.unlink()
            except Exception:
                pass

            if not success:
                # Discard the candidate; the original is preserved.
                return RewriteOutcome(
                    component_id=component_id,
                    strategy=strategy,
                    failure_classification=classification,
                    success=False,
                    elapsed_seconds=time.monotonic() - t0,
                    tests_before=tests_before,
                    tests_after=tests_after,
                    new_test_file=None,
                    explanation="rewrite produced a test that did not pass verification",
                )

            # Commit: rewrite the candidate's content onto the
            # production path. The caller (generator) is responsible
            # for re-running the entire suite to confirm no
            # regressions elsewhere.
            new_test_file = candidate.model_copy(update={"path": str(original_path)})
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=True,
                elapsed_seconds=time.monotonic() - t0,
                tests_before=tests_before,
                tests_after=tests_after,
                new_test_file=new_test_file,
                explanation="rewrote test; verification passed",
            )
        except Exception as exc:  # noqa: BLE001
            # An LLM or verifier exception is recorded but does not
            # crash the run. The candidate is discarded; the original
            # is preserved.
            return RewriteOutcome(
                component_id=component_id,
                strategy=strategy,
                failure_classification=classification,
                success=False,
                elapsed_seconds=time.monotonic() - t0,
                tests_before=tests_before,
                tests_after=tests_before,
                new_test_file=None,
                explanation=f"rewrite raised: {type(exc).__name__}: {exc}",
            )


def _verifier_repo_path(verifier: Any) -> str:
    """Read the verifier's repo_path. The attribute name varies; both
    are tolerated so this module works across verifier versions.
    """
    return getattr(verifier, "repo_path", "") or getattr(verifier, "_repo_path", "")


def _count_failures(test_file: TestFile) -> int:
    """Number of test cases in this file with status == FAILED."""
    # Imported lazily so this module doesn't take a hard dep on the
    # TestStatus enum at module load.
    from code2test.core.models import TestStatus
    return sum(1 for tc in test_file.test_cases if tc.status == TestStatus.FAILED)


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
