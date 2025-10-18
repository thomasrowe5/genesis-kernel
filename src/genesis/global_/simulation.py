"""Long-term simulation utilities for planetary policy stress testing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping


@dataclass(slots=True)
class SimulationScenario:
    name: str
    shocks: Mapping[str, float]
    duration_cycles: int


@dataclass(slots=True)
class SimulationResult:
    name: str
    metrics: Mapping[str, float]


class PlanetarySimulation:
    """Executes simplified planetary simulations for planning."""

    def __init__(self) -> None:
        self._history: list[SimulationResult] = []

    def run(self, scenario: SimulationScenario) -> SimulationResult:
        metrics: MutableMapping[str, float] = {}
        for key, magnitude in scenario.shocks.items():
            metrics[f"impact_{key}"] = magnitude * scenario.duration_cycles
        metrics["resilience"] = max(0.0, 100.0 - sum(metrics.values()))
        result = SimulationResult(name=scenario.name, metrics=dict(metrics))
        self._history.append(result)
        return result

    def history(self) -> Iterable[SimulationResult]:
        return tuple(self._history)


__all__ = ["SimulationScenario", "SimulationResult", "PlanetarySimulation"]
