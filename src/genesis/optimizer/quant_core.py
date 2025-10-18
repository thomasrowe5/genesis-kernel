"""Deterministic mock of the Quant Systems RL core."""
from __future__ import annotations

from typing import Dict


class QuantCoreStub:
    """Simple gradient-free optimizer adjusting scalar params."""

    def __init__(self, step_size: float = 0.1, decay: float = 0.99) -> None:
        self._step_size = step_size
        self._decay = decay

    def step(self, params: Dict[str, float], reward: float) -> Dict[str, float]:
        updated = dict(params)
        for key, value in params.items():
            direction = 1.0 if reward >= 0 else -1.0
            updated[key] = value + self._step_size * direction
        self._step_size *= self._decay
        return updated


__all__ = ["QuantCoreStub"]
