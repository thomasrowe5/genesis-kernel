"""Experiment reporting utilities."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping

from genesis.metrics import (
    genesis_insights_total,
    genesis_publications_total,
)

from .experiment import ExperimentResult


@dataclass(slots=True)
class Insight:
    """Structured representation of a discovered rule."""

    statement: str
    confidence: float
    evidence: Mapping[str, float]
    created_at: datetime


class ExperimentReporter:
    """Collect experiment results and surface insights."""

    def __init__(self) -> None:
        self._results: list[ExperimentResult] = []
        self._insights: list[Insight] = []

    def add_result(self, result: ExperimentResult) -> None:
        self._results.append(result)

    def record_insight(self, statement: str, evidence: Mapping[str, float]) -> Insight:
        confidence = self._estimate_confidence(evidence.values())
        insight = Insight(
            statement=statement,
            confidence=confidence,
            evidence=dict(evidence),
            created_at=datetime.utcnow(),
        )
        self._insights.append(insight)
        genesis_insights_total.inc()
        return insight

    def seed_insight(self, insight: Insight) -> None:
        """Insert an existing insight without mutating counters."""

        self._insights.append(insight)

    def summary(self) -> Mapping[str, float]:
        if not self._results:
            return {"runs": 0, "success_rate": 0.0}
        success_rate = sum(result.success for result in self._results) / len(self._results)
        durations = [result.finished_at - result.started_at for result in self._results]
        return {
            "runs": float(len(self._results)),
            "success_rate": success_rate,
            "mean_duration": statistics.mean(durations),
        }

    def publish(self) -> Mapping[str, object]:
        genesis_publications_total.inc()
        return {
            "results": [result.metrics for result in self._results],
            "insights": [insight.statement for insight in self._insights],
        }

    def list_insights(self) -> Iterable[Insight]:
        return list(self._insights)

    @staticmethod
    def _estimate_confidence(values: Iterable[float]) -> float:
        data = list(values)
        if not data:
            return 0.0
        maximum = max(abs(value) for value in data)
        return min(0.99, 0.5 + 0.5 * maximum)


class InsightStore:
    """Mutable store for insights keyed by identifier."""

    def __init__(self) -> None:
        self._items: MutableMapping[str, Insight] = {}

    def add(self, insight_id: str, insight: Insight) -> None:
        self._items[insight_id] = insight

    def get(self, insight_id: str) -> Insight:
        return self._items[insight_id]

    def list(self) -> list[Insight]:
        return list(self._items.values())


__all__ = ["ExperimentReporter", "Insight", "InsightStore"]
