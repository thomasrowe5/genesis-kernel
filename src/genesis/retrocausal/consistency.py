"""Retrocausal consistency validation utilities."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Sequence

from genesis.metrics import genesis_paradox_preventions_total, genesis_retro_consistency_score

from .inference import RetroPolicyUpdate
from .reverse_sim import ReverseSimulationResult


@dataclass(slots=True)
class RetroProofArtifact:
    """Hash-chain proof guaranteeing reversible tolerance."""

    run_hash: str
    valid: bool


class RetroConsistencyVerifier:
    """Validates that retrocausal updates maintain causal closure."""

    def __init__(self, tolerance: float = 1e-3) -> None:
        self._tolerance = tolerance
        self._last_hash: str | None = None

    @staticmethod
    def _hash_payload(payload: Sequence[float]) -> str:
        digest = hashlib.sha256()
        digest.update(json.dumps(list(payload), sort_keys=True).encode("utf-8"))
        return digest.hexdigest()

    def verify(self, result: ReverseSimulationResult, update: RetroPolicyUpdate) -> RetroProofArtifact:
        adjustments = [intervention.reward_adjustment - intervention.entropy_adjustment for intervention in result.interventions]
        magnitude = sum(abs(value) for value in update.gradients.values())
        valid = magnitude <= (abs(result.reward_delta) + self._tolerance)
        if not valid:
            genesis_paradox_preventions_total.inc()
        payload = adjustments + [update.reward_delta, update.entropy_delta, float(valid)]
        if self._last_hash is not None:
            payload.append(float(int(self._last_hash[:8], 16)))
        run_hash = self._hash_payload(payload)
        self._last_hash = run_hash
        genesis_retro_consistency_score.set(1.0 if valid else 0.0)
        return RetroProofArtifact(run_hash=run_hash, valid=valid)

    def chain(self) -> str | None:
        return self._last_hash


__all__ = ["RetroConsistencyVerifier", "RetroProofArtifact"]
