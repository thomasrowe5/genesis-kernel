"""Reflection scheduler and journal for reflexive intelligence."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, List, Optional

from genesis.metrics import genesis_reflection_confidence_mean

from genesis.reflexion.models import ReflectionLog, SQLMODEL_AVAILABLE


@dataclass(slots=True)
class ReflectionJournal:
    """Persist and retrieve reflection logs."""

    session_factory: Optional[Callable[[], Any]] = None
    _logs: List[ReflectionLog] = field(default_factory=list)

    def record(
        self,
        *,
        reason: str,
        prediction: dict[str, float],
        result: dict[str, float],
        delta: dict[str, float],
        confidence: float,
    ) -> ReflectionLog:
        entry = ReflectionLog(
            id=None,
            reason=reason,
            prediction=prediction,
            result=result,
            delta=delta,
            confidence=confidence,
            created_at=datetime.utcnow(),
        )
        self._store(entry)
        self._update_confidence_metric()
        return entry

    def query(self, since: datetime | None = None, limit: int | None = None) -> List[ReflectionLog]:
        entries = self._fetch()
        if since is not None:
            entries = [entry for entry in entries if entry.created_at >= since]
        if limit is not None:
            entries = entries[-limit:]
        return entries

    def _store(self, entry: ReflectionLog) -> None:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                session.add(entry)
                session.commit()
                session.refresh(entry)
        else:
            self._logs.append(entry)

    def _fetch(self) -> List[ReflectionLog]:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session, select  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                statement = select(ReflectionLog).order_by(ReflectionLog.created_at.asc())
                return list(session.exec(statement))
        return list(self._logs)

    def _update_confidence_metric(self) -> None:
        entries = self._fetch()
        if not entries:
            return
        mean_confidence = sum(entry.confidence for entry in entries) / len(entries)
        genesis_reflection_confidence_mean.set(mean_confidence)


@dataclass(slots=True)
class ReflectionScheduler:
    """Coordinates periodic introspective reflections."""

    journal: ReflectionJournal
    cadence_seconds: int = 3600

    def should_reflect(self, last_run: datetime | None, now: datetime | None = None) -> bool:
        moment = now or datetime.utcnow()
        if last_run is None:
            return True
        return (moment - last_run).total_seconds() >= self.cadence_seconds
