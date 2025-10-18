"""Optimization loop driving self-healing behaviour for Genesis modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from quant_rl import RewardEngine

from genesis.promptmesh.router import PromptMeshRouter
from genesis.registry.manager import ModuleRegistryManager
from genesis.registry.models import ModuleVersion

from genesis.evaluator.service import EvaluatorService


@dataclass(slots=True)
class OptimizationOutcome:
    module: str
    version: str
    reward: float
    promoted: bool
    metrics: Dict[str, float]


class OptimizerLoop:
    """Coordinates evaluation, reward shaping, and replacement decisions."""

    def __init__(
        self,
        registry: ModuleRegistryManager,
        evaluator: EvaluatorService,
        router: Optional[PromptMeshRouter] = None,
        reward_engine: Optional[RewardEngine] = None,
        replacement_delta: float = 0.05,
        latency_baseline: float = 1.0,
    ) -> None:
        self._registry = registry
        self._evaluator = evaluator
        self._router = router or PromptMeshRouter()
        self._reward_engine = reward_engine or RewardEngine()
        self._replacement_delta = replacement_delta
        self._latency_baseline = max(latency_baseline, 1e-3)

    async def evaluate_candidate(
        self,
        name: str,
        version: str,
        path: str,
        metadata: Optional[Dict[str, Any]] = None,
        benchmark: Optional[str] = None,
    ) -> OptimizationOutcome:
        module_version = self._registry.register_version(name, version, path, metadata)
        evaluation = await self._evaluator.evaluate_module(name, version, benchmark_name=benchmark)
        reward = self.compute_reward(evaluation.metrics)
        shaped_reward = self._reward_engine.shape(reward).value
        updated = self._registry.record_metrics(module_version, shaped_reward, evaluation.metrics)
        promoted = self._maybe_promote(updated)
        self._router.update_module(name, self._registry.select_best(name, limit=5))
        return OptimizationOutcome(
            module=name,
            version=version,
            reward=shaped_reward,
            promoted=promoted,
            metrics=evaluation.metrics,
        )

    def compute_reward(self, metrics: Dict[str, float]) -> float:
        accuracy = float(metrics.get("accuracy", 0.0))
        stability = float(metrics.get("stability", 0.0))
        latency = float(metrics.get("latency", self._latency_baseline))
        latency_score = min(1.0, self._latency_baseline / max(latency, 1e-6))
        reward = accuracy * stability * latency_score
        return max(0.0, min(1.0, reward))

    def _maybe_promote(self, candidate: ModuleVersion) -> bool:
        active = self._registry.get_active_version(candidate.name)
        if active is None:
            self._registry.activate_version(candidate)
            self._registry.record_replacement(candidate, previous_version=None)
            return True

        if candidate.id == active.id:
            return False

        if candidate.score >= active.score + self._replacement_delta:
            previous = active
            self._registry.activate_version(candidate)
            self._registry.record_replacement(candidate, previous_version=previous)
            return True
        return False
