"""Introspection utilities reasoning about Genesis' internal state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional

from genesis.metrics import genesis_meta_anomalies_total
from genesis.utils.pydantic_compat import BaseModel

from genesis.reflexion.simulator import SimulationResult
from genesis.reflexion.twin import TwinState

from .uncertainty import UncertaintyTracker


class IntrospectionReport(BaseModel):
    """Summary of reflexive analysis."""

    confidence: float
    anomalies: list[str]
    halt: bool


@dataclass(slots=True)
class Introspector:
    """Assess consistency between predicted and observed behavior."""

    tracker: UncertaintyTracker
    drift_threshold: float = 0.1
    min_confidence: float = 0.3

    def evaluate(
        self,
        snapshot: TwinState,
        *,
        simulation: Optional[SimulationResult] = None,
        observed_metrics: Optional[Mapping[str, float]] = None,
    ) -> IntrospectionReport:
        observed = observed_metrics or snapshot.metrics
        anomalies: List[str] = []

        for key, value in observed.items():
            record = self.tracker.update(key, float(value))
            if simulation is not None and key in simulation.predicted_delta:
                expected = snapshot.metrics.get(key, 0.0) + simulation.predicted_delta[key]
                drift = abs(expected - float(value))
                if drift > self.drift_threshold + record.stddev:
                    anomalies.append(f"drift:{key}:{drift:.4f}")

        if anomalies:
            genesis_meta_anomalies_total.inc(len(anomalies))

        confidence = self.tracker.global_confidence()
        halt = confidence < self.min_confidence or bool(anomalies)
        return IntrospectionReport(confidence=confidence, anomalies=anomalies, halt=halt)
