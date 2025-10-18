"""Canary rollout controller enforcing guardrails."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from genesis.registry.manager import ModuleRegistryManager
from genesis.registry.models import ModuleVersion


@dataclass(slots=True)
class SLOThresholds:
    error_multiplier: float = 1.5
    latency_multiplier: float = 1.2
    reward_floor_delta: float = 0.05


class CanaryController:
    """Evaluates canary deployments and adjusts traffic shares."""

    STAGES = [0.01, 0.05, 0.2, 0.5, 1.0]

    def __init__(self, registry: ModuleRegistryManager, thresholds: SLOThresholds | None = None) -> None:
        self._registry = registry
        self._thresholds = thresholds or SLOThresholds()

    def step(self, module: str) -> Optional[str]:
        candidate = self._current_canary(module)
        baseline = self._registry.get_active_version(module)
        if candidate is None or baseline is None:
            return None
        if not self._passes_slo(candidate, baseline):
            self._registry.rollback(module, candidate.version, reason="slo_breach")
            return "rollback"
        stage_index = int(candidate.metadata_json.get("canary_stage", 0))
        if stage_index >= len(self.STAGES) - 1:
            self._registry.finalize_promotion(module, candidate.version)
            return "promoted"
        next_index = stage_index + 1
        next_share = self.STAGES[next_index]
        candidate.metadata_json["canary_stage"] = next_index
        baseline_share = max(0.0, 1.0 - next_share)
        self._registry.set_traffic_splits(
            module,
            {
                baseline.version: baseline_share,
                candidate.version: next_share,
            },
        )
        if next_share >= 1.0:
            self._registry.finalize_promotion(module, candidate.version)
            return "promoted"
        return "progressed"

    def _current_canary(self, module: str) -> Optional[ModuleVersion]:
        candidates = self._registry.select_active_versions(module)
        for candidate in candidates:
            if candidate.canary:
                return candidate
        return None

    def _passes_slo(self, candidate: ModuleVersion, baseline: ModuleVersion) -> bool:
        threshold = self._thresholds
        baseline_error = max(baseline.error_rate, 1e-6)
        baseline_latency = max(baseline.p95_ms, 1e-3)
        baseline_reward = baseline.reward_ma

        if candidate.error_rate > baseline_error * threshold.error_multiplier:
            return False
        if candidate.p95_ms > baseline_latency * threshold.latency_multiplier:
            return False
        if candidate.reward_ma + threshold.reward_floor_delta < baseline_reward:
            return False
        return True


__all__ = ["SLOThresholds", "CanaryController"]
