"""Reconciliation utilities comparing predicted and actual Genesis states."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, ContextManager, Dict, List, Mapping, Optional

from genesis.metrics import genesis_continuity_score
from genesis.chronos import ContinuityEnforcer, ContinuityStatus

from .models import SQLMODEL_AVAILABLE, ContinuityMetric, StatePayload

if SQLMODEL_AVAILABLE:
    from sqlmodel import Session  # pragma: no cover - optional path
else:  # pragma: no cover - type checker helper
    Session = object  # type: ignore[assignment]

SessionFactory = Callable[[], ContextManager[Session]]


@dataclass(slots=True)
class ReconciliationReport:
    delta: float
    score: float
    metrics: Dict[str, float]
    status: ContinuityStatus


class TemporalReconciler:
    """Computes the divergence between predicted and actual states."""

    def __init__(
        self,
        enforcer: ContinuityEnforcer,
        *,
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._enforcer = enforcer
        self._session_factory = session_factory
        self._metrics: List[ContinuityMetric] = []

    def _numeric_subset(self, payload: Mapping[str, object]) -> Dict[str, float]:
        numeric: Dict[str, float] = {}
        for key, value in payload.items():
            if isinstance(value, (int, float)):
                numeric[key] = float(value)
            elif isinstance(value, Mapping):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        numeric[f"{key}.{sub_key}"] = float(sub_value)
        return numeric

    def _persist_metric(self, metric: ContinuityMetric) -> None:
        if not SQLMODEL_AVAILABLE or self._session_factory is None:
            return
        with self._session_factory() as session:  # type: ignore[attr-defined]
            session.add(metric)
            session.commit()
            session.refresh(metric)

    def reconcile(self, predicted: StatePayload, actual: StatePayload) -> ReconciliationReport:
        actual_numeric = self._numeric_subset(actual)
        predicted_numeric = self._numeric_subset(predicted)
        keys = set(actual_numeric) | set(predicted_numeric)
        metric_deltas = {
            key: abs(predicted_numeric.get(key, 0.0) - actual_numeric.get(key, 0.0))
            for key in keys
        }
        delta = sum(metric_deltas.values())
        base_score = 1.0 if delta == 0 else max(0.0, 1.0 - min(delta, 1.0))
        continuity_status = self._enforcer.evaluate(actual_numeric, predicted_numeric)
        score = min(base_score, continuity_status.score)
        genesis_continuity_score.set(score)
        metric = ContinuityMetric(key="temporal", value=score, delta=delta, at=datetime.utcnow())
        self._metrics.append(metric)
        self._persist_metric(metric)
        return ReconciliationReport(delta=delta, score=score, metrics=metric_deltas, status=continuity_status)

    @property
    def metrics(self) -> List[ContinuityMetric]:
        return list(self._metrics)


__all__ = ["TemporalReconciler", "ReconciliationReport"]
