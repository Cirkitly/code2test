"""Generator event types.

Pure value types emitted by code2test.core.generator.TestGenerator. Consumed
only by the code2testbench package — code2test itself ships a NullSink and
remains unaware of any benchmark collector.

Five event shapes today; the union is closed and small:

    IntentExtracted
    TestsGenerated
    VerificationCompleted
    DiagnosisTriggered
    RewriteAttempted

Each event has run_id and component_id so a sink can correlate them across
phases. Run-id is a UUID4 generated once per TestGenerator.run() invocation.

The plan document is /home/utkarsh/Work/cirkitly/code2test/.hermes/plans/
2026-07-11_225800-code2test-v1.0.md, milestone M1B.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional


def new_run_id() -> str:
    """Single source of run-ids. Re-exported so the generator depends only
    on this module, not on uuid directly."""
    return uuid.uuid4().hex


# --- base ---------------------------------------------------------------

@dataclass(frozen=True)
class GeneratorEvent:
    """Base type for every emission from TestGenerator.

    ``run_id`` groups all events produced by a single TestGenerator.run()
    call. ``component_id`` names the source-code component the event is about
    (function/method/class id from AST analysis).

    Immutable; events are facts, not state.
    """
    run_id: str
    component_id: str


# --- intent extraction --------------------------------------------------

@dataclass(frozen=True)
class IntentExtracted(GeneratorEvent):
    """Static or LLM intent extraction completed for one component.

    Emitted once per component (whether or not it triggers downstream phases).
    ``accepted=True`` means the intent was above the configured confidence
    threshold (and so a test will be generated for it).
    """
    confidence: float
    accepted: bool


# --- test generation ----------------------------------------------------

@dataclass(frozen=True)
class TestsGenerated(GeneratorEvent):
    """TestAgent produced a TestFile for the component.

    ``test_file_path`` is the (relative) destination where the agent intends
    to write the file. The verifier may not actually invoke a write until
    --accept is given; this event indicates intent-to-write.
    """
    test_file_path: str
    test_count: int


# --- verification -------------------------------------------------------

@dataclass(frozen=True)
class VerificationCompleted(GeneratorEvent):
    """The test file has been executed against the source under test.

    ``passed + failed`` equals the total test count from TestsGenerated minus
    any skipped. ``failure_ids`` lists the names of failing tests in case
    the diagnosis agent needs them.

    ``rerun`` is True when this event comes from the phase-4 full-suite
    re-run (after a successful rewrite). The collector counts rerun
    events separately to drive ``verification_pass_rate_after_rewrite``.
    """
    passed: int
    failed: int
    failure_ids: tuple[str, ...] = ()
    rerun: bool = False


# --- diagnosis ----------------------------------------------------------

@dataclass(frozen=True)
class DiagnosisTriggered(GeneratorEvent):
    """The diagnosis agent has classified a failure.

    One DiagnosisTriggered per failing test that the diagnosis agent sees.
    ``cause`` is one of the DiagnosisCause enum members; the strict string
    values are required by downstream code2testbench reporting.
    """
    failure_id: str
    cause: str
    diagnosis_confidence: float


# --- repair -------------------------------------------------------------

@dataclass(frozen=True)
class RewriteAttempted(GeneratorEvent):
    """A test or intent was rewritten in response to a diagnosis.

    ``success`` records whether the rewritten version passes verification.
    Multiple rewrites can occur for one failure; the v1.1 generator's
    per-component invariant caps the count at one per component per run.

    ``failure_classification`` carries the diagnosis agent's
    ``DiagnosisCause`` value (TEST_WRONG, CODE_BUG, INTENT_WRONG). This
    is what lets us explain *why* a benchmark improved or didn't:
    strategy=='skip' with cause=='CODE_BUG' means a source bug the
    test side couldn't fix; strategy=='test_rewrite' with
    success==False means the rewrite failed to produce a passing test.

    ``elapsed_seconds`` is wall-clock time of the rewrite attempt.
    Combined with ``strategy`` and ``success`` it answers "did this
    rewrite burn budget without payoff?"
    """
    failure_id: str
    success: bool
    strategy: str = "test_rewrite"   # "test_rewrite" | "intent_rewrite" | "skip"
    failure_classification: str = "UNKNOWN"
    elapsed_seconds: float = 0.0


# --- observability -------------------------------------------------------

@dataclass(frozen=True)
class GenerationRecorded(GeneratorEvent):
    """One LLM call inside a phase-2 (test generation) invocation.

    Emitted exactly once per ``predict()`` call from the test_agent.
    Carries the diagnostic data the benchmark needs to answer
    "why did generation succeed or fail."

    Fields:
      component_id: who triggered the call. Set by the test_agent;
        the provider doesn't know it.
      model: model name passed to the openai SDK.
      prompt_hash: sha256 of the composed system+user prompt. Stable
        across runs of the same input; varies when input changes.
      raw_response: the model's full reply string, including any
         `` ... `` blocks and prose. Not truncated.
      parsed_response: the JSON extracted by the provider's tolerant
         extractor. None if extraction failed.
      validation_errors: None on success; exception class and
         message on schema-validation failure.
      generated_test_count: the count of items in the schema's
         list-typed field (e.g. ``tests``). 0 for non-list schemas
         or when validation failed before we could count.
    """
    component_id: str
    model: str
    prompt_hash: str
    raw_response: Optional[str] = None
    parsed_response: Optional[str] = None
    validation_errors: Optional[str] = None
    generated_test_count: int = 0


# --- rewrite outcome -----------------------------------------------------

@dataclass(frozen=True)
class RewriteCommitted(GeneratorEvent):
    """Outcome of the per-component rewrite transaction.

    Emitted by the generator after the coordinator returns, regardless
    of strategy. Captures the data the variance experiment needs to
    partition the failure space:

      isolated_passed / isolated_failed: the candidate's verifier
        result (what the coordinator saw).
      replaced: whether the generator committed the candidate to the
        production path on disk. False on success implies a
        transactional_replacement_failure even when isolated_passed
        was True.
      strategy / failure_classification: what was attempted and why.
        A strategy that doesn't match the failure_classification
        (e.g. test_rewrite on CODE_BUG) is a strategy_mismatch.

    The benchmark uses this event to classify every unsuccessful
    rewrite into one of: no_tests_generated,
    invalid_generated_tests, verifier_failure,
    transactional_replacement_failure, strategy_mismatch, other.
    """
    component_id: str
    strategy: str
    failure_classification: str
    isolated_passed: int
    isolated_failed: int
    replaced: bool
    success: bool


# --- sink contract ------------------------------------------------------

class _NullSink:
    """Default sink used when no collector is wired.

    Exists inside code2test because the generator's public surface calls
    ``self._sink.emit(event)``. The sink itself contains no benchmark logic;
    the collector lives in code2testbench/ and is injected by callers.
    """
    def emit(self, event: GeneratorEvent) -> None:  # noqa: D401
        return None


def null_sink() -> _NullSink:
    """Return the no-op sink used as the production default."""
    return _NullSink()


__all__ = [
    "GeneratorEvent",
    "IntentExtracted",
    "TestsGenerated",
    "VerificationCompleted",
    "DiagnosisTriggered",
    "RewriteAttempted",
    "GenerationRecorded",
    "RewriteCommitted",
    "new_run_id",
    "null_sink",
]
