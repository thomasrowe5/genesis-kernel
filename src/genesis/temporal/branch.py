"""Temporal branching utilities for alternate futures."""
from __future__ import annotations

from typing import Callable, ContextManager, Dict, List, Optional

from genesis.metrics import genesis_branch_merges_total
from genesis.chronos import ContinuityEnforcer

from .models import SQLMODEL_AVAILABLE, BranchRecord, StatePayload
from .reconciler import ReconciliationReport
from .timeline import TimelineManager

if SQLMODEL_AVAILABLE:
    from sqlmodel import Session  # pragma: no cover - optional path
else:  # pragma: no cover - type checker helper
    Session = object  # type: ignore[assignment]

SessionFactory = Callable[[], ContextManager[Session]]


class TemporalBranchManager:
    """Creates and merges alternate future branches."""

    def __init__(
        self,
        timeline: TimelineManager,
        enforcer: ContinuityEnforcer,
        *,
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._timeline = timeline
        self._enforcer = enforcer
        self._session_factory = session_factory
        self._branches: List[BranchRecord] = []
        self._next_id = 1
        self._snapshots: Dict[int, StatePayload] = {}

    def _attach_identity(self, branch: BranchRecord) -> BranchRecord:
        if branch.id is None:
            branch.id = self._next_id
            self._next_id += 1
        return branch

    def _persist_branch(self, branch: BranchRecord) -> None:
        if not SQLMODEL_AVAILABLE or self._session_factory is None:
            return
        with self._session_factory() as session:  # type: ignore[attr-defined]
            session.add(branch)
            session.commit()
            session.refresh(branch)

    def _divergence(self, parent_state: StatePayload, snapshot: StatePayload) -> float:
        keys = set(key for key, value in parent_state.items() if isinstance(value, (int, float)))
        divergence = 0.0
        for key in keys:
            parent_value = float(parent_state.get(key, 0.0))
            candidate_value = float(snapshot.get(key, parent_value))
            divergence += abs(candidate_value - parent_value)
        return divergence

    def create_branch(
        self,
        parent_commit_id: int,
        snapshot: StatePayload,
        *,
        name: str = "",
    ) -> BranchRecord:
        parent = self._timeline.get_commit(parent_commit_id)
        divergence = self._divergence(parent.state_json, snapshot)
        branch = BranchRecord(parent_id=parent.id, divergence_score=divergence, name=name)
        self._attach_identity(branch)
        self._branches.append(branch)
        self._snapshots[branch.id] = dict(snapshot)
        self._persist_branch(branch)
        return branch

    def list_branches(self) -> List[BranchRecord]:
        return list(self._branches)

    def get_branch(self, branch_id: int) -> BranchRecord:
        for branch in self._branches:
            if branch.id == branch_id:
                return branch
        raise KeyError(f"Branch {branch_id} not found")

    def merge_branch(self, branch_id: int, reconciliation: ReconciliationReport) -> BranchRecord:
        branch = self.get_branch(branch_id)
        if branch.merged:
            raise ValueError("Branch already merged")
        if branch.parent_id is not None and branch_id in self._snapshots:
            parent_state = self._timeline.get_commit(branch.parent_id).state_json
            baseline = {key: float(value) for key, value in parent_state.items() if isinstance(value, (int, float))}
            candidate_snapshot = self._snapshots[branch_id]
            candidate = {key: float(value) for key, value in candidate_snapshot.items() if isinstance(value, (int, float))}
            status = self._enforcer.evaluate(baseline, candidate)
            if not status.is_consistent:
                raise ValueError("Branch violates continuity constraints")
        if not reconciliation.status.is_consistent or reconciliation.score < 1.0:
            raise ValueError("Continuity constraints failed; merge denied")
        branch.merged = True
        self._persist_branch(branch)
        genesis_branch_merges_total.inc()
        return branch

    def snapshot_payload(self, branch_id: int) -> StatePayload:
        return dict(self._snapshots[branch_id])


__all__ = ["TemporalBranchManager"]
