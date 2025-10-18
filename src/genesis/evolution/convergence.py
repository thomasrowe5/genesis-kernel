"""Convergence logic for reconciling diverged Genesis branches."""
from __future__ import annotations

from typing import Dict, Iterable, List

from .speciation import BranchGenome


class ConvergenceEngine:
    """Merge branch parameter sets using fitness and ethics weighting."""

    def converge(
        self,
        branches: Iterable[BranchGenome],
        fitness: Dict[str, float],
        ethics_weight: float,
    ) -> List[float]:
        branch_list = list(branches)
        if not branch_list:
            return []
        weight_sum = 0.0
        accumulator: List[float] = [0.0 for _ in branch_list[0].parameters]
        for branch in branch_list:
            branch_fitness = fitness.get(branch.identifier, 0.0)
            ethics_bonus = max(0.0, 1.0 - branch.divergence_score) * ethics_weight
            weight = max(0.01, branch_fitness + ethics_bonus)
            weight_sum += weight
            for index, value in enumerate(branch.parameters):
                accumulator[index] += value * weight
        return [value / weight_sum for value in accumulator]


__all__ = ["ConvergenceEngine"]
