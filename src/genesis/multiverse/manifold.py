"""Represents the multiversal manifold of Genesis timelines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

from genesis.metrics import genesis_multiverse_branches_total


@dataclass(slots=True)
class BranchState:
    """State vector for a single timeline branch."""

    branch_id: str
    metrics: Mapping[str, float]

    def divergence(self, other: "BranchState") -> float:
        overlap = set(self.metrics) | set(other.metrics)
        delta = 0.0
        for key in overlap:
            a = self.metrics.get(key, 0.0)
            b = other.metrics.get(key, 0.0)
            delta += abs(a - b)
        return delta / max(len(overlap), 1)


class MultiverseManifold:
    """Collection of branch states forming a manifold."""

    def __init__(self, branches: Iterable[BranchState] | None = None) -> None:
        self._branches: Dict[str, BranchState] = {branch.branch_id: branch for branch in branches or []}
        self._update_metrics()

    def _update_metrics(self) -> None:
        genesis_multiverse_branches_total.set(len(self._branches))

    def branches(self) -> List[BranchState]:
        return list(self._branches.values())

    def upsert(self, branch: BranchState) -> None:
        self._branches[branch.branch_id] = branch
        self._update_metrics()

    def remove(self, branch_id: str) -> None:
        self._branches.pop(branch_id, None)
        self._update_metrics()

    def divergence_matrix(self) -> Dict[tuple[str, str], float]:
        keys = list(self._branches)
        matrix: Dict[tuple[str, str], float] = {}
        for idx, first in enumerate(keys):
            for second in keys[idx + 1 :]:
                matrix[(first, second)] = self._branches[first].divergence(self._branches[second])
        return matrix

    def summary(self) -> Mapping[str, Mapping[str, float]]:
        return {branch_id: dict(branch.metrics) for branch_id, branch in self._branches.items()}


__all__ = ["BranchState", "MultiverseManifold"]
