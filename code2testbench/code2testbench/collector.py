"""EventCollector — accumulates AcceptanceReport from code2test's event stream.

The collector implements the same `emit(event)` contract as NullSink, so
it can be passed directly to TestGenerator(sink=collector).

It walks every event and updates four counters:

  initial_total, initial_accept  -> IntentExtracted.accepted counts
  diagnostics_total             -> VerificationCompleted.failed counts
  diagnosis_triggered           -> DiagnosisTriggered counts
  rewrites_total                 -> VerificationCompleted.failed (shared denominator)
  rewrite_attempted              -> RewriteAttempted counts
  final_total, final_accept      -> RewriteAttempted.success counts

When `report()` is called, these counters are normalized into the four
rates that AcceptanceReport exposes.

The collector is *strict* — it raises on events it doesn't understand, so
a code2test version drift that adds a new event will surface immediately.

This module imports `code2test.events` (an allowed coupling) but does NOT
import `code2test.core.generator` (forbidden by M1D.2 architecture).
"""

from __future__ import annotations

from typing import Iterable, List

from code2test.events import (
    DiagnosisTriggered,
    IntentExtracted,
    RewriteAttempted,
    TestsGenerated,
    VerificationCompleted,
)

from code2testbench.report import AcceptanceReport


class EventCollector:
    """Subscribes to a code2test event stream and produces AcceptanceReport."""

    def __init__(self) -> None:
        # Initial acceptance: from IntentExtracted.accepted / total.
        self._initial_total = 0
        self._initial_accept = 0

        # Diagnosis triggered: a diagnosis agent was invoked on a failure.
        self._diagnostics_total = 0
        self._diagnosis_triggered = 0

        # Rewrite attempted: a repair was actually attempted.
        self._rewrites_total = 0
        self._rewrite_attempted = 0

        # Final acceptance: rewrites that succeeded.
        self._final_total = 0
        self._final_accept = 0

        # Sanity check: duplicate component_ids in InitialAcceptance? Track raw events.
        self._events: List = []

    # --- sink contract -----------------------------------------------------

    def emit(self, event) -> None:
        """Sink entry point called by TestGenerator."""
        self._events.append(event)

        if isinstance(event, IntentExtracted):
            self._initial_total += 1
            if event.accepted:
                self._initial_accept += 1

        elif isinstance(event, VerificationCompleted):
            # Each failed test is a candidate for diagnosis and rewrite.
            self._diagnostics_total += event.failed
            self._rewrites_total += event.failed

        elif isinstance(event, DiagnosisTriggered):
            self._diagnosis_triggered += 1

        elif isinstance(event, RewriteAttempted):
            self._rewrite_attempted += 1
            self._final_total += 1
            if event.success:
                self._final_accept += 1

        elif isinstance(event, TestsGenerated):
            # Informational; not a counter contributor.
            pass

        else:
            # Unknown event type: fail loudly so the catalog can be updated.
            raise TypeError(
                f"EventCollector does not understand event type: {type(event).__name__}"
            )

    # --- report ------------------------------------------------------------

    def report(self) -> AcceptanceReport:
        """Compute AcceptanceReport from accumulated counters.

        Empty run -> NaN; this is intentional and signals "no signal" to
        the caller (the harness prints these and they stand out).
        """
        return AcceptanceReport(
            initial_acceptance_rate=_safe_ratio(self._initial_accept, self._initial_total),
            diagnosis_trigger_rate=_safe_ratio(self._diagnosis_triggered, self._diagnostics_total),
            rewrite_attempt_rate=_safe_ratio(self._rewrite_attempted, self._rewrites_total),
            final_acceptance_rate=_safe_ratio(self._final_accept, self._final_total),
        )

    # --- introspection -----------------------------------------------------

    @property
    def events(self) -> List:
        """Raw captured events; used by tests."""
        return list(self._events)


def _safe_ratio(num: int, den: int) -> float:
    """Return num/den, or float('nan') when denominator is zero.

    NaN is more honest than 0.0 — a 0 means "tried and failed", NaN means
    "never tried". A benchmark report with all-NaN rows is a clear signal
    to the engineer that the run didn't engage.
    """
    if den == 0:
        return float("nan")
    return num / den


__all__ = ["EventCollector"]
