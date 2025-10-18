"""Mutation operators supporting controlled innovation for Genesis branches."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence


@dataclass(slots=True)
class MutationOperator:
    """Apply bounded Gaussian perturbations to parameter vectors."""

    rate: float
    scale: float
    rng: random.Random

    def __init__(self, rate: float, scale: float, seed: int | None = None) -> None:
        if not 0.0 <= rate <= 1.0:
            raise ValueError("rate must be between 0 and 1")
        if scale <= 0:
            raise ValueError("scale must be positive")
        self.rate = rate
        self.scale = scale
        self.rng = random.Random(seed)

    def mutate(self, params: Sequence[float]) -> List[float]:
        mutated: List[float] = []
        for value in params:
            if self.rng.random() <= self.rate:
                delta = self.rng.gauss(0.0, self.scale)
                mutated.append(value + delta)
            else:
                mutated.append(value)
        return mutated

    def bounded_mutate(self, params: Sequence[float], delta_max: float) -> List[float]:
        result = self.mutate(params)
        bounded: List[float] = []
        for original, mutated in zip(params, result):
            bounded.append(_clamp(mutated, original - delta_max, original + delta_max))
        return bounded


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


__all__ = ["MutationOperator"]
