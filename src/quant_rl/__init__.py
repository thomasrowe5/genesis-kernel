"""Minimal stub of the Quant Systems reinforcement learning helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RewardSignal:
    value: float


class RewardEngine:
    """Simplified reward shaping helper used for integration tests."""

    def shape(self, score: float) -> RewardSignal:
        return RewardSignal(value=max(0.0, min(1.0, score)))


__all__ = ["RewardEngine", "RewardSignal"]
