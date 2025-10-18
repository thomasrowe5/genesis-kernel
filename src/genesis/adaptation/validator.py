"""Validation routines enforcing safety prior to rollout."""
from __future__ import annotations

from dataclasses import dataclass
from genesis.metacog.introspector import IntrospectionReport
from genesis.reflexion.simulator import SimulationResult


@dataclass(slots=True)
class ValidationOutcome:
    accepted: bool
    reasons: list[str]


@dataclass(slots=True)
class ChangeValidator:
    """Apply safety and ethics policies to simulated changes."""

    min_confidence: float = 0.5

    def validate(self, report: IntrospectionReport, simulation: SimulationResult) -> ValidationOutcome:
        reasons: list[str] = []
        if report.confidence < self.min_confidence:
            reasons.append(f"confidence-below-threshold:{report.confidence:.2f}")
        if report.anomalies:
            reasons.extend(report.anomalies)
        accepted = not reasons
        return ValidationOutcome(accepted=accepted, reasons=reasons)
