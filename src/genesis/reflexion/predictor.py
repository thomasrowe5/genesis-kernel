"""Predictive models derived from simulation history."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .simulator import SimulationChange, SimulationResult


@dataclass(slots=True)
class PredictorRecord:
    change_key: str
    confidences: List[float] = field(default_factory=list)
    deltas: List[Dict[str, float]] = field(default_factory=list)

    def add(self, confidence: float, delta: Dict[str, float]) -> None:
        self.confidences.append(confidence)
        self.deltas.append(delta)

    def reliability(self) -> float:
        if not self.confidences:
            return 0.0
        return sum(self.confidences) / len(self.confidences)

    def aggregate_delta(self) -> Dict[str, float]:
        totals: Dict[str, float] = defaultdict(float)
        for delta in self.deltas:
            for key, value in delta.items():
                totals[key] += value
        if not self.deltas:
            return {}
        return {key: value / len(self.deltas) for key, value in totals.items()}


class ReflexivePredictor:
    """Lightweight predictor estimating stability of proposed changes."""

    def __init__(self) -> None:
        self._history: Dict[str, PredictorRecord] = {}

    def _key(self, change: SimulationChange) -> str:
        return f"{change.module}:{change.param}"

    def observe(self, result: SimulationResult) -> None:
        key = self._key(result.change)
        record = self._history.setdefault(key, PredictorRecord(change_key=key))
        record.add(result.confidence, result.predicted_delta)

    def reliability(self, change: SimulationChange) -> float:
        return self._history.get(self._key(change), PredictorRecord(self._key(change))).reliability()

    def expected_delta(self, change: SimulationChange) -> Dict[str, float]:
        return self._history.get(self._key(change), PredictorRecord(self._key(change))).aggregate_delta()

    def summary(self) -> Dict[str, Tuple[float, Dict[str, float]]]:
        return {key: (record.reliability(), record.aggregate_delta()) for key, record in self._history.items()}
