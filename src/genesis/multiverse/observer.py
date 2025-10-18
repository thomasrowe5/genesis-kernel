"""Observability helpers for the multiversal manifold."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from genesis.metrics import genesis_paradox_preventions_total

from .manifold import MultiverseManifold


@dataclass(slots=True)
class DivergenceAlert:
    """Alert describing a divergence between two branches."""

    branch_a: str
    branch_b: str
    delta: float


class MultiverseObserver:
    """Monitors manifold stability and emits divergence alerts."""

    def __init__(self, manifold: MultiverseManifold, threshold: float = 0.2) -> None:
        self._manifold = manifold
        self._threshold = threshold

    def scan(self) -> List[DivergenceAlert]:
        alerts: List[DivergenceAlert] = []
        for (branch_a, branch_b), delta in self._manifold.divergence_matrix().items():
            if delta > self._threshold:
                alerts.append(DivergenceAlert(branch_a=branch_a, branch_b=branch_b, delta=delta))
                genesis_paradox_preventions_total.inc()
        return alerts

    def resolved(self, alerts: Iterable[DivergenceAlert]) -> None:
        for alert in alerts:
            if alert.delta <= self._threshold:
                continue
            self._manifold.remove(alert.branch_b)


__all__ = ["DivergenceAlert", "MultiverseObserver"]
