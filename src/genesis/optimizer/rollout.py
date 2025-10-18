"""Rollout promotion management."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Tuple

from genesis.registry.manager import ModuleRegistryManager


@dataclass(slots=True)
class RewardWindow:
    values: Deque[float] = field(default_factory=lambda: deque(maxlen=10))

    def add(self, value: float) -> None:
        self.values.append(value)

    def ready(self, window: int) -> bool:
        return len(self.values) >= window

    def average(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)


class RolloutManager:
    """Compares reward windows to promote or rollback variants."""

    def __init__(
        self,
        registry: ModuleRegistryManager,
        *,
        window: int = 5,
        delta: float = 0.05,
    ) -> None:
        self._registry = registry
        self._window = window
        self._delta = delta
        self._history: Dict[Tuple[str, str], RewardWindow] = {}

    def record(self, module: str, version: str, reward: float) -> None:
        window = self._history.setdefault((module, version), RewardWindow())
        window.add(reward)

    def maybe_promote(self, module: str, version: str) -> bool:
        candidate = self._registry.get_version(module, version)
        active = self._registry.get_active_version(module)
        if candidate is None or active is None:
            return False
        if candidate.version == active.version:
            return False
        cand_window = self._history.get((module, candidate.version))
        active_window = self._history.get((module, active.version))
        if cand_window is None or active_window is None:
            return False
        if not cand_window.ready(self._window) or not active_window.ready(self._window):
            return False
        if cand_window.average() > active_window.average() + self._delta:
            self._registry.finalize_promotion(module, candidate.version)
            return True
        return False


__all__ = ["RolloutManager"]
