"""Speciation logic for diverging Genesis civilization branches."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .mutation import MutationOperator


@dataclass(slots=True)
class BranchGenome:
    """Representation of a civilization branch genome."""

    identifier: str
    ancestor: str
    parameters: List[float]
    mutation_vector: List[float]
    divergence_score: float


class SpeciationEngine:
    """Create diverging branches from a shared ancestor."""

    def __init__(self, mutation: MutationOperator, delta: float = 0.2) -> None:
        self.mutation = mutation
        self.delta = delta
        self._counter = 0

    def speciate(self, ancestor: str, params: Sequence[float], count: int) -> list[BranchGenome]:
        branches: list[BranchGenome] = []
        for _ in range(count):
            self._counter += 1
            mutation_vector = self.mutation.bounded_mutate(params, self.delta)
            divergence = _divergence(params, mutation_vector)
            branches.append(
                BranchGenome(
                    identifier=f"{ancestor}-branch-{self._counter}",
                    ancestor=ancestor,
                    parameters=list(mutation_vector),
                    mutation_vector=[b - a for a, b in zip(params, mutation_vector)],
                    divergence_score=divergence,
                )
            )
        return branches


def _divergence(baseline: Sequence[float], mutated: Sequence[float]) -> float:
    deltas = [(b - a) ** 2 for a, b in zip(baseline, mutated)]
    return sum(deltas) ** 0.5


__all__ = ["BranchGenome", "SpeciationEngine"]
