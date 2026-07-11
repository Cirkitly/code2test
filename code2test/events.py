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
    """
    passed: int
    failed: int
    failure_ids: tuple[str, ...] = ()


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
    Multiple rewrites can occur for one failure.
    """
    failure_id: str
    success: bool
    strategy: str = "test_rewrite"   # "test_rewrite" | "intent_rewrite" | "skip"


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
    "new_run_id",
    "null_sink",
]
