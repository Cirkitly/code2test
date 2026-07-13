"""AcceptanceReport — the four-number benchmark result.

Schema is closed at v1. v1.1 adds a fifth number to disambiguate
"the rewrite itself succeeded" from "the post-rewrite run is better."

The five numbers tell a consistent story:

  initial_acceptance_rate:
      Of all components considered, what fraction had an intent above
      the confidence threshold? This is the "intent extraction quality"
      head-line.

  diagnosis_trigger_rate:
      Of all failed tests, what fraction triggered the diagnosis agent?
      (i.e. the agent was invoked at all.) High is good; tells us the
      repair loop is engaging.

  rewrite_attempt_rate:
      Of all diagnosed failures, what fraction led to a rewrite attempt?
      (Diagnose but don't rewrite = no repair; that's a leak in the
      loop.) Stretch goal ≥50%.

  rewrite_success_rate:
      Of all rewrites attempted, what fraction produced a passing
      test? This is the per-event metric; it answers "did the
      rewrite itself work?" and is independent of how the post-rewrite
      suite shakes out.

  final_acceptance_rate:
      After repair, what fraction of components passed verification?
      This is the user-facing "does it work" number.

  generation_success_rate:
      Of all LLM calls in phase 2, what fraction produced a
      non-empty test list? Per-call metric, distinct from
      final_acceptance_rate. Low numbers here mean the LLM is
      being asked to generate tests but is not producing any --
      the bottleneck the rewrite loop exposes. The metric
      separates "model is wrong" from "model is silent."

  net_improvement = final - initial.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AcceptanceReport:
    """Closed-schema benchmark result.

    All six rates are floating-point fractions in [0.0, 1.0]. NaN is
    permitted when denominators are zero; it signals "no data" rather
    than zero.
    """
    initial_acceptance_rate: float
    diagnosis_trigger_rate: float
    rewrite_attempt_rate: float
    rewrite_success_rate: float
    final_acceptance_rate: float
    generation_success_rate: float

    def net_improvement(self) -> float:
        """final - initial; positive means the repair loop improved the result."""
        return self.final_acceptance_rate - self.initial_acceptance_rate

    @classmethod
    def from_dict(cls, payload: dict) -> "AcceptanceReport":
        """Hydrate from JSON; rejects unknown keys.

        Stored shape is e.g.:
            {"initial_acceptance_rate": 0.48,
             "diagnosis_trigger_rate": 0.30,
             "rewrite_attempt_rate": 0.20,
             "rewrite_success_rate": 0.50,
             "final_acceptance_rate": 0.71}
        """
        expected = {"initial_acceptance_rate", "diagnosis_trigger_rate",
                    "rewrite_attempt_rate", "rewrite_success_rate",
                    "final_acceptance_rate", "generation_success_rate"}
        unknown = set(payload) - expected
        if unknown:
            raise ValueError(f"Unknown fields in AcceptanceReport payload: {sorted(unknown)}")
        return cls(
            initial_acceptance_rate=float(payload["initial_acceptance_rate"]),
            diagnosis_trigger_rate=float(payload["diagnosis_trigger_rate"]),
            rewrite_attempt_rate=float(payload["rewrite_attempt_rate"]),
            rewrite_success_rate=float(payload["rewrite_success_rate"]),
            final_acceptance_rate=float(payload["final_acceptance_rate"]),
            generation_success_rate=float(payload["generation_success_rate"]),
        )

    def to_dict(self) -> dict:
        return {
            "initial_acceptance_rate": self.initial_acceptance_rate,
            "diagnosis_trigger_rate": self.diagnosis_trigger_rate,
            "rewrite_attempt_rate": self.rewrite_attempt_rate,
            "rewrite_success_rate": self.rewrite_success_rate,
            "final_acceptance_rate": self.final_acceptance_rate,
            "generation_success_rate": self.generation_success_rate,
            "net_improvement": self.net_improvement(),
        }


__all__ = ["AcceptanceReport"]
