"""Temporal job orchestration bridging timeline and recursion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from genesis.temporal import (
        ReconciliationReport,
        StatePayload,
        TemporalBranchManager,
        TemporalObserver,
        TemporalRecursionScheduler,
        TimelineCommit,
    )
    from genesis.temporal.reconciler import TemporalReconciler


@dataclass(slots=True)
class TemporalJobResult:
    commit: TimelineCommit
    prediction: StatePayload
    reconciliation: ReconciliationReport


class TemporalJobScheduler:
    """Coordinates timeline snapshots, simulations, and continuity checks."""

    def __init__(
        self,
        recursion: TemporalRecursionScheduler,
        reconciler: TemporalReconciler,
        branches: TemporalBranchManager,
        observer: TemporalObserver,
    ) -> None:
        self._recursion = recursion
        self._reconciler = reconciler
        self._branches = branches
        self._observer = observer

    async def simulate_and_reconcile(
        self,
        commit_id: int,
        simulator: Callable[[StatePayload], Awaitable[StatePayload]],
        *,
        label: str | None = None,
    ) -> TemporalJobResult:
        result = await self._recursion.run_from_commit(commit_id, simulator, label=label)
        reconciliation = self._reconciler.reconcile(result.prediction, result.base_commit.state_json)
        if result.alert is not None:
            self._observer.record_alert(result.alert)
        return TemporalJobResult(
            commit=result.base_commit,
            prediction=result.prediction,
            reconciliation=reconciliation,
        )

    def ensure_branch_merge(self, branch_id: int, reconciliation: ReconciliationReport) -> None:
        self._branches.merge_branch(branch_id, reconciliation)


__all__ = ["TemporalJobScheduler", "TemporalJobResult"]
