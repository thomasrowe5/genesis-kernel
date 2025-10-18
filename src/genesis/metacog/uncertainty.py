"""Uncertainty tracking utilities for reflexive meta-cognition."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Dict, Iterable, Iterator, Tuple

from genesis.metrics import genesis_uncertainty_metrics_total

from genesis.reflexion.models import UncertaintyMetric


@dataclass(slots=True)
class _Stats:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)

    @property
    def stddev(self) -> float:
        return sqrt(self.variance)


class UncertaintyTracker:
    """Maintains running statistics for critical Genesis metrics."""

    def __init__(self) -> None:
        self._stats: Dict[str, _Stats] = {}
        self._last_updated: Dict[str, datetime] = {}

    def update(self, key: str, value: float) -> UncertaintyMetric:
        stats = self._stats.setdefault(key, _Stats())
        stats.update(value)
        record = UncertaintyMetric(
            id=None,
            key=key,
            mean=stats.mean,
            stddev=stats.stddev,
            last_updated=datetime.utcnow(),
        )
        self._last_updated[key] = record.last_updated
        genesis_uncertainty_metrics_total.set(len(self._stats))
        return record

    def bulk_update(self, metrics: Iterable[Tuple[str, float]]) -> Dict[str, UncertaintyMetric]:
        return {key: self.update(key, value) for key, value in metrics}

    def describe(self, key: str) -> UncertaintyMetric | None:
        stats = self._stats.get(key)
        if stats is None:
            return None
        return UncertaintyMetric(
            id=None,
            key=key,
            mean=stats.mean,
            stddev=stats.stddev,
            last_updated=self._last_updated.get(key, datetime.utcnow()),
        )

    def confidence(self, key: str) -> float:
        stats = self._stats.get(key)
        if stats is None or stats.stddev == 0.0:
            return 1.0
        return 1.0 / (1.0 + stats.stddev)

    def global_confidence(self) -> float:
        if not self._stats:
            return 1.0
        confidences = [self.confidence(key) for key in self._stats]
        return sum(confidences) / len(confidences)

    def export(self) -> Iterator[UncertaintyMetric]:
        for key in sorted(self._stats.keys()):
            record = self.describe(key)
            if record is not None:
                yield record
