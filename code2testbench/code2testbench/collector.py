"""EventCollector — accumulates AcceptanceReport from code2test's event stream.

The collector implements the same `emit(event)` contract as NullSink, so
it can be passed directly to TestGenerator(sink=collector).

It walks every event and updates six counters plus a raw events list:

  initial_total, initial_accept        -> IntentExtracted.accepted counts
  diagnostics_total                   -> VerificationCompleted.failed counts
  diagnosis_triggered                 -> DiagnosisTriggered counts
  rewrites_total                      -> VerificationCompleted.failed (shared denominator)
  rewrite_attempted, rewrite_success  -> RewriteAttempted counts
  final_total, final_accept           -> RewriteAttempted.success counts
  events                              -> raw event list, for per-event replay

When `report()` is called, these counters are normalized into the five
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
    GenerationRecorded,
    IntentExtracted,
    RewriteAttempted,
    RewriteCommitted,
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
        # Per-component counter for failed-components. Set on each
        # VerificationCompleted with failed > 0. Used as the
        # rewrite_attempt_rate denominator so the ratio is per-
        # component, not per-failed-test.
        self._failed_components = 0
        # Rewrite success: of rewrites attempted, what fraction produced
        # a passing test. Per-event metric, distinct from final_acceptance_rate.
        self._rewrite_success = 0

        # Final acceptance: rewrites that succeeded AND a re-run of the
        # suite passed more tests than before the rewrite.
        self._final_total = 0
        self._final_accept = 0

        # Generation success tracking. Each GenerationRecorded event
        # increments _generation_requested; _generation_succeeded is
        # incremented when the event's generated_test_count > 0.
        # generation_success_rate = succeeded / requested; it answers
        # "of all phase-2 LLM calls, what fraction produced tests?"
        # A non-trivial low number here is the bottleneck signal the
        # benchmark exists to surface.
        self._generation_requested = 0
        self._generation_succeeded = 0

        # Phase-4 re-run tracking. VerificationCompleted events with
        # rerun=True feed verification_pass_rate_after_rewrite. The
        # numerator is the count of components passing on the re-run;
        # the denominator is the count of components that had a rerun
        # event (i.e. components the loop chose to re-verify).
        # verification_pass_rate_before_rewrite is derived: it's
        # (_initial_total - _failed_components) / _initial_total.
        self._rerun_components_total = 0
        self._rerun_components_passed = 0

        # Per-event raw list for the variance experiment. The variance
        # script walks these to classify failures into the categories
        # defined in docs/benchmark_findings_v1.1_instrumentation.md.
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
            # Per-test counter for diagnosis_trigger_rate. The
            # metric denominator is the count of failed tests, not
            # the count of failed components, so the diagnostic
            # path's reasoning ("every failure triggered diagnosis")
            # is exposed directly.
            self._diagnostics_total += event.failed
            self._rewrites_total += event.failed
            # Per-component counter for failed-components. The
            # rewrite_attempt_rate denominator is components-with-
            # failures, not failed tests; this keeps the ratio
            # well-defined when one component has many failing tests.
            if event.failed > 0 and not getattr(event, "rerun", False):
                self._failed_components += 1
            # Phase-4 re-run events feed the post-rewrite pass rate.
            # A re-run event on a component that passed (failed=0)
            # is a successful re-run, which is what we count toward
            # verification_pass_rate_after_rewrite.
            if getattr(event, "rerun", False):
                self._rerun_components_total += 1
                if event.failed == 0:
                    self._rerun_components_passed += 1

        elif isinstance(event, DiagnosisTriggered):
            self._diagnosis_triggered += 1

        elif isinstance(event, RewriteAttempted):
            self._rewrite_attempted += 1
            self._final_total += 1
            if event.success:
                self._rewrite_success += 1
                self._final_accept += 1

        elif isinstance(event, TestsGenerated):
            # Informational; not a counter contributor.
            pass

        elif isinstance(event, GenerationRecorded):
            self._generation_requested += 1
            if event.generated_test_count > 0 and not event.validation_errors:
                self._generation_succeeded += 1

        elif isinstance(event, RewriteCommitted):
            # RewriteCommitted is observational; its data lives in
            # self._events for the variance experiment to walk. We
            # do not increment any counters here because the same
            # logical event already incremented them via
            # RewriteAttempted; the only new data is the verifier
            # counts and the replaced flag.
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
            # rewrite_attempt_rate is per-component: the denominator is
            # the count of components that had at least one failed
            # test, not the count of failed tests. With per-test
            # denominator the metric dilutes as a single failing
            # component generates many failed tests.
            rewrite_attempt_rate=_safe_ratio(self._rewrite_attempted, self._failed_components),
            rewrite_success_rate=_safe_ratio(self._rewrite_success, self._rewrite_attempted),
            final_acceptance_rate=_safe_ratio(self._final_accept, self._final_total),
            generation_success_rate=_safe_ratio(
                self._generation_succeeded, self._generation_requested
            ),
            # verification_pass_rate_before_rewrite: fraction of all
            # components that passed verification in phase 3, before
            # the rewrite loop ran. This is the user-facing "did your
            # tests pass before we tried to repair?" number.
            verification_pass_rate_before_rewrite=_safe_ratio(
                self._initial_total - self._failed_components,
                self._initial_total,
            ),
            # verification_pass_rate_after_rewrite: fraction of all
            # components that passed verification in phase 4, after
            # the rewrite loop ran. The denominator is the count of
            # components that had a re-run event (i.e. components
            # the loop chose to re-verify). NaN when no re-runs
            # occurred because the loop had nothing to repair.
            verification_pass_rate_after_rewrite=_safe_ratio(
                self._rerun_components_passed,
                self._rerun_components_total,
            ),
        )

    # --- introspection -----------------------------------------------------

    @property
    def events(self) -> List:
        """Raw captured events; used by tests."""
        return list(self._events)

    def rewrite_events(self) -> List[RewriteAttempted]:
        """All RewriteAttempted events, in order; for the recorded JSON."""
        return [e for e in self._events if isinstance(e, RewriteAttempted)]

    def rewrite_committed_events(self) -> List[RewriteCommitted]:
        """All RewriteCommitted events, in order; the variance
        experiment walks this list to classify failures.
        """
        return [e for e in self._events if isinstance(e, RewriteCommitted)]

    def verification_rerun_events(self) -> List[VerificationCompleted]:
        """All phase-4 re-run VerificationCompleted events."""
        return [
            e for e in self._events
            if isinstance(e, VerificationCompleted) and getattr(e, "rerun", False)
        ]


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
