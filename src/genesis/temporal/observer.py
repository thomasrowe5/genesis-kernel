"""Causality observer safeguarding the temporal recursion engine."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable, ContextManager, List, Optional

from genesis.chronos import compute_entropy_delta
from genesis.metrics import genesis_entropy_delta, genesis_temporal_violations_total
from genesis.utils.json_utils import canonical_dumps

from .models import SQLMODEL_AVAILABLE, StatePayload, TemporalAlert

if SQLMODEL_AVAILABLE:
    from sqlmodel import Session  # pragma: no cover - optional path
else:  # pragma: no cover - type checker helper
    Session = object  # type: ignore[assignment]

SessionFactory = Callable[[], ContextManager[Session]]


class TemporalViolation(RuntimeError):
    """Raised when a temporal safety invariant is violated."""

    def __init__(self, alert: TemporalAlert, delta: float) -> None:
        super().__init__(alert.description)
        self.alert = alert
        self.delta = delta


class TemporalObserver:
    """Monitors entropy deltas and loop detection across simulations."""

    def __init__(
        self,
        entropy_limit: float = 1.0,
        *,
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._entropy_limit = entropy_limit
        self._session_factory = session_factory
        self._alerts: List[TemporalAlert] = []
        self._seen_hashes: set[str] = set()

    def _canonical_hash(self, payload: StatePayload) -> str:
        serialized = canonical_dumps(payload, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _numeric_view(self, payload: StatePayload) -> dict[str, float]:
        numeric: dict[str, float] = {}
        for key, value in payload.items():
            if isinstance(value, (int, float)):
                numeric[key] = float(value)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        numeric[f"{key}.{sub_key}"] = float(sub_value)
        return numeric

    def _persist_alert(self, alert: TemporalAlert) -> None:
        if not SQLMODEL_AVAILABLE or self._session_factory is None:
            return
        with self._session_factory() as session:  # type: ignore[attr-defined]
            session.add(alert)
            session.commit()

    def record_alert(self, alert: TemporalAlert) -> None:
        self._alerts.append(alert)
        genesis_temporal_violations_total.inc()
        self._persist_alert(alert)

    def _check_loop(self, payload: StatePayload) -> bool:
        state_hash = self._canonical_hash(payload)
        if state_hash in self._seen_hashes:
            return True
        self._seen_hashes.add(state_hash)
        return False

    def observe(self, predicted: StatePayload, actual: StatePayload, *, context: str | None = None) -> float:
        predicted_metrics = self._numeric_view(predicted)
        actual_metrics = self._numeric_view(actual)
        delta = compute_entropy_delta(predicted_metrics, actual_metrics)
        genesis_entropy_delta.set(delta)
        if delta > self._entropy_limit:
            alert = TemporalAlert(
                type="entropy-breach",
                severity="critical",
                description=(
                    f"Entropy delta {delta:.4f} exceeded limit {self._entropy_limit:.4f}" + (f" during {context}" if context else "")
                ),
                at=datetime.utcnow(),
            )
            raise TemporalViolation(alert, delta)
        if self._check_loop(predicted):
            alert = TemporalAlert(
                type="temporal-loop",
                severity="error",
                description="Temporal loop detected via repeated prediction hash",
                at=datetime.utcnow(),
            )
            raise TemporalViolation(alert, delta)
        return delta

    @property
    def alerts(self) -> List[TemporalAlert]:
        return list(self._alerts)


__all__ = ["TemporalObserver", "TemporalViolation"]
