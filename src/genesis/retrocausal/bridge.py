"""Synchronisation bridge between forward and reverse timelines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from genesis.metrics import genesis_retro_runs_total

from .consistency import RetroConsistencyVerifier, RetroProofArtifact
from .inference import RetroPolicyUpdate, RetrocausalInferenceEngine
from .reverse_sim import ReverseSimulationRequest, ReverseSimulationResult, ReverseSimulator


@dataclass(slots=True)
class RetrocausalBridgeReport:
    """Outcome of a retrocausal bridge cycle."""

    simulation: ReverseSimulationResult
    update: RetroPolicyUpdate
    proof: RetroProofArtifact


class RetrocausalBridge:
    """Integrates forward and reverse reasoning into a reversible loop."""

    def __init__(
        self,
        simulator: ReverseSimulator,
        inference: RetrocausalInferenceEngine,
        verifier: RetroConsistencyVerifier,
    ) -> None:
        self._simulator = simulator
        self._inference = inference
        self._verifier = verifier

    async def execute(self, request: ReverseSimulationRequest) -> RetrocausalBridgeReport:
        simulation = await self._simulator.run(request)
        update = await self._inference.optimise(request)
        proof = self._verifier.verify(simulation, update)
        genesis_retro_runs_total.labels(status="bridged").inc()
        return RetrocausalBridgeReport(simulation=simulation, update=update, proof=proof)

    def parameters(self) -> Mapping[str, float]:
        return self._inference.parameters()


__all__ = ["RetrocausalBridge", "RetrocausalBridgeReport"]
