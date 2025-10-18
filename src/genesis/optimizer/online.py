"""Online optimizer updating bandit rewards and parameters."""
from __future__ import annotations

from dataclasses import dataclass

from genesis.registry.manager import ModuleRegistryManager

from ..router.router import PromptRouter
from .quant_core import QuantCoreStub


@dataclass(slots=True)
class Outcome:
    module: str
    version: str
    score: float
    latency_ms: float
    success: bool


class OnlineOptimizer:
    """Combines bandit updates with lightweight parameter tuning."""

    def __init__(
        self,
        registry: ModuleRegistryManager,
        router: PromptRouter,
        *,
        target_latency_ms: float = 500.0,
        quant_core: QuantCoreStub | None = None,
    ) -> None:
        self._registry = registry
        self._router = router
        self._target_latency_ms = target_latency_ms
        self._quant_core = quant_core or QuantCoreStub()

    def update(self, outcome: Outcome) -> float:
        reward = self._compute_reward(outcome)
        self._registry.update_online_metrics(
            outcome.module,
            outcome.version,
            reward=reward,
            latency_ms=outcome.latency_ms,
            ok=outcome.success,
        )
        self._router.observe_outcome(outcome.module, outcome.version, reward=reward, success=outcome.success)
        self._update_params(outcome.module, outcome.version, reward)
        return reward

    def _compute_reward(self, outcome: Outcome) -> float:
        normalized = max(0.0, min(outcome.score, 1.0))
        latency_term = max(
            0.0,
            min(1.0, 1.0 / (1.0 + outcome.latency_ms / max(self._target_latency_ms, 1.0))),
        )
        success_term = 1.0 if outcome.success else 0.0
        return normalized * latency_term * success_term

    def _update_params(self, module: str, version: str, reward: float) -> None:
        module_version = self._registry.get_version(module, version)
        if module_version is None:
            return
        params = {
            key: float(value)
            for key, value in module_version.params_json.items()
            if isinstance(value, (int, float))
        }
        if not params:
            params = {"lr": 0.1}
        new_params = self._quant_core.step(params, reward)
        self._registry.update_params(module, version, new_params)


__all__ = ["Outcome", "OnlineOptimizer"]
