"""Prompt routing across module variants."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, List, Optional

from genesis.metrics import (
    genesis_orch_decision_duration_seconds,
    genesis_router_selection_total,
)
from genesis.registry.manager import ModuleRegistryManager
from genesis.registry.models import ModuleVersion

from .policies import PolicyCandidate, build_policy

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RouterDecision:
    """Result of a routing decision."""

    module: str
    version: str
    policy: str
    reason: str


class PromptRouter:
    """Routes tasks to module variants using bandit policies."""

    def __init__(
        self,
        registry: ModuleRegistryManager,
        *,
        policy: str = "ucb1",
        rng_seed: int = 0,
        policy_kwargs: Optional[dict[str, Any]] = None,
    ) -> None:
        self._registry = registry
        self._policy_name = policy
        self._policy = build_policy(policy, rng_seed=rng_seed, **(policy_kwargs or {}))

    @property
    def policy(self) -> str:
        return self._policy_name

    def route(self, task_type: str, *, context: Optional[dict[str, Any]] = None) -> RouterDecision:
        """Return the module/version that should handle the task."""

        start = time.perf_counter()
        try:
            candidate = self._select_candidate(task_type)
            decision = RouterDecision(
                module=candidate.module,
                version=candidate.version,
                policy=self._policy_name,
                reason="policy",
            )
            genesis_router_selection_total.labels(self._policy_name, decision.module, decision.version).inc()
            logger.info(
                "router_decision",
                extra={
                    "module": decision.module,
                    "version": decision.version,
                    "policy": self._policy_name,
                    "context": context or {},
                },
            )
            return decision
        finally:
            duration = time.perf_counter() - start
            genesis_orch_decision_duration_seconds.observe(duration)

    def _select_candidate(self, task_type: str) -> PolicyCandidate:
        candidates = self._build_candidates(task_type)
        if not candidates:
            raise ValueError(f"No registered module versions for task {task_type}")
        if len(candidates) == 1:
            return candidates[0]
        return self._policy.select(task_type, candidates)

    def _build_candidates(self, module: str) -> List[PolicyCandidate]:
        active = self._registry.select_active_versions(module)
        if not active:
            active = self._registry.select_best(module, limit=1)
        return [self._convert(module_version) for module_version in active]

    @staticmethod
    def _convert(module_version: ModuleVersion) -> PolicyCandidate:
        return PolicyCandidate(
            module=module_version.name,
            version=module_version.version,
            score=module_version.score,
            reward_ma=module_version.reward_ma,
            p95_ms=module_version.p95_ms,
            error_rate=module_version.error_rate,
            traffic_share=module_version.traffic_share,
        )

    def observe_outcome(
        self,
        module: str,
        version: str,
        *,
        reward: float,
        success: bool,
    ) -> None:
        """Update the underlying bandit policy with an outcome."""

        self._policy.update(module, version, reward, success=success)


__all__ = ["PromptRouter", "RouterDecision"]
