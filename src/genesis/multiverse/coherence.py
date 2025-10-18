"""Cross-branch coherence computation for the Genesis multiverse."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Mapping

from genesis.metrics import genesis_multiverse_coherence_score

from .manifold import BranchState, MultiverseManifold


@dataclass(slots=True)
class MultiverseMergeReport:
    """Summary of a multiverse merge operation."""

    coherence_score: float
    merged_branch: BranchState


class MultiverseCoherenceEngine:
    """Computes divergence across branches and performs entropy-aware merges."""

    def __init__(self, manifold: MultiverseManifold, epsilon: float = 0.05) -> None:
        self._manifold = manifold
        self._epsilon = epsilon

    def set_epsilon(self, epsilon: float) -> None:
        self._epsilon = epsilon

    def coherence_score(self) -> float:
        matrix = self._manifold.divergence_matrix()
        if not matrix:
            return 1.0
        mean_divergence = mean(matrix.values())
        score = 1.0 / (1.0 + mean_divergence)
        genesis_multiverse_coherence_score.set(score)
        return score

    def _project(self) -> BranchState:
        branches = self._manifold.branches()
        if not branches:
            return BranchState(branch_id="origin", metrics={})
        keys: set[str] = set()
        for branch in branches:
            keys.update(branch.metrics)
        merged_metrics: dict[str, float] = {}
        for key in keys:
            merged_metrics[key] = mean(branch.metrics.get(key, 0.0) for branch in branches)
        return BranchState(branch_id="merged", metrics=merged_metrics)

    async def merge(self) -> MultiverseMergeReport:
        merged = self._project()
        for branch in self._manifold.branches():
            adjusted = {}
            for key, value in merged.metrics.items():
                original = branch.metrics.get(key, value)
                adjusted[key] = original + (value - original) * self._epsilon
            self._manifold.upsert(BranchState(branch.branch_id, adjusted))
        score = self.coherence_score()
        return MultiverseMergeReport(coherence_score=score, merged_branch=merged)

    def summary(self) -> Mapping[str, Mapping[str, float]]:
        return self._manifold.summary()


__all__ = ["MultiverseCoherenceEngine", "MultiverseMergeReport"]
