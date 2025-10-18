"""Bidirectional inference engine coordinating reverse gradients."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from genesis.metrics import genesis_retro_runs_total

from .reverse_sim import ReverseSimulationRequest, ReverseSimulator


@dataclass(slots=True)
class RetroPolicyUpdate:
    """Represents a reversible policy update suggestion."""

    gradients: Mapping[str, float]
    reward_delta: float
    entropy_delta: float


class RetrocausalInferenceEngine:
    """Computes reverse-time gradients to inform current optimisation."""

    def __init__(self, simulator: ReverseSimulator, learning_rate: float = 0.1) -> None:
        self._simulator = simulator
        self._learning_rate = learning_rate
        self._parameters: Dict[str, float] = {}

    def parameters(self) -> Mapping[str, float]:
        return dict(self._parameters)

    async def optimise(self, request: ReverseSimulationRequest) -> RetroPolicyUpdate:
        result = await self._simulator.run(request)
        gradients: Dict[str, float] = {}
        for index, intervention in enumerate(result.interventions):
            sensitivity = 1.0 / (index + 1)
            gradients[intervention.commit_id] = (
                intervention.reward_adjustment - intervention.entropy_adjustment
            ) * sensitivity
        for key, value in gradients.items():
            current = self._parameters.get(key, 0.0)
            self._parameters[key] = current + self._learning_rate * value
        genesis_retro_runs_total.labels(status="optimised").inc()
        return RetroPolicyUpdate(
            gradients=gradients,
            reward_delta=result.reward_delta,
            entropy_delta=result.entropy_delta,
        )


__all__ = ["RetrocausalInferenceEngine", "RetroPolicyUpdate"]
