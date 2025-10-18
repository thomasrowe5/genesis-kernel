"""Temporal recursion scheduler responsible for replay simulations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Awaitable, Callable, ContextManager, List, Optional

from genesis.metrics import genesis_recursion_runs_total

from .models import SQLMODEL_AVAILABLE, RecursionRun, StatePayload, TemporalAlert, TimelineCommit
from .observer import TemporalObserver, TemporalViolation
from .timeline import TimelineManager

if SQLMODEL_AVAILABLE:
    from sqlmodel import Session  # pragma: no cover - optional path
else:  # pragma: no cover - type checker helper
    Session = object  # type: ignore[assignment]

SessionFactory = Callable[[], ContextManager[Session]]


@dataclass(slots=True)
class RecursionResult:
    run: RecursionRun
    prediction: StatePayload
    base_commit: TimelineCommit
    delta: float
    alert: TemporalAlert | None


class TemporalRecursionScheduler:
    """Schedules and records temporal recursion simulations."""

    def __init__(
        self,
        timeline: TimelineManager,
        observer: TemporalObserver,
        *,
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._timeline = timeline
        self._observer = observer
        self._session_factory = session_factory
        self._runs: List[RecursionRun] = []
        self._next_id = 1

    def _attach_identity(self, run: RecursionRun) -> RecursionRun:
        if run.id is None:
            run.id = self._next_id
            self._next_id += 1
        return run

    def _persist_run(self, run: RecursionRun) -> None:
        if not SQLMODEL_AVAILABLE or self._session_factory is None:
            return
        with self._session_factory() as session:  # type: ignore[attr-defined]
            session.add(run)
            session.commit()
            session.refresh(run)

    async def _simulate(
        self,
        simulator: Callable[[StatePayload], Awaitable[StatePayload]],
        base_state: StatePayload,
    ) -> StatePayload:
        result = simulator(base_state)
        if asyncio.iscoroutine(result):  # pragma: no branch - runtime guard
            return await result
        return result  # type: ignore[return-value]

    async def run_from_commit(
        self,
        commit_id: int,
        simulator: Callable[[StatePayload], Awaitable[StatePayload]],
        *,
        label: str | None = None,
    ) -> RecursionResult:
        commit = self._timeline.get_commit(commit_id)
        start = perf_counter()
        prediction = await self._simulate(simulator, commit.state_json)
        duration = perf_counter() - start
        status = "success"
        delta = 0.0
        alert: TemporalAlert | None = None
        try:
            delta = self._observer.observe(prediction, commit.state_json, context=f"commit:{commit_id}")
        except TemporalViolation as violation:
            alert = violation.alert
            delta = violation.delta
            status = "halted"
            self._observer.record_alert(alert)
        run = RecursionRun(
            from_commit=commit.id,
            duration=duration,
            result_json=prediction,
            status=status,
        )
        self._attach_identity(run)
        self._runs.append(run)
        self._persist_run(run)
        genesis_recursion_runs_total.labels(status=status).inc()
        return RecursionResult(
            run=run,
            prediction=prediction,
            base_commit=commit,
            delta=delta,
            alert=alert,
        )

    def materialize_projection(
        self,
        result: RecursionResult,
        *,
        node_id: str | None = None,
    ) -> TimelineCommit:
        commit = self._timeline.record_commit(result.prediction, node_id=node_id)
        result.run.to_commit = commit.id
        self._persist_run(result.run)
        return commit

    @property
    def runs(self) -> List[RecursionRun]:
        return list(self._runs)


__all__ = ["TemporalRecursionScheduler", "RecursionResult"]
