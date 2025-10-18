"""Timeline management with monotonic vector clocks."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, ContextManager, Iterable, List, Mapping, Optional

from genesis.metrics import genesis_timeline_commits_total
from genesis.utils.json_utils import canonical_dumps

from .models import SQLMODEL_AVAILABLE, StatePayload, TimelineCommit, VectorClock

if SQLMODEL_AVAILABLE:
    from sqlmodel import Session  # pragma: no cover - optional path
else:  # pragma: no cover - type checker helper
    Session = object  # type: ignore[assignment]

SessionFactory = Callable[[], ContextManager[Session]]


@dataclass(slots=True)
class VectorClockState:
    """Snapshot of a vector clock at a specific time."""

    clock: VectorClock
    timestamp: datetime


class VectorClockError(RuntimeError):
    """Raised when vector clocks cannot be reconciled."""


class TimelineManager:
    """Maintains a causal timeline of Genesis states."""

    def __init__(
        self,
        node_id: str,
        session_factory: Optional[SessionFactory] = None,
    ) -> None:
        self._node_id = node_id
        self._clock: VectorClock = {}
        self._commits: List[TimelineCommit] = []
        self._session_factory = session_factory
        self._next_id = 1

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def clock(self) -> VectorClock:
        return dict(self._clock)

    def _tick(self, node_id: Optional[str] = None) -> VectorClock:
        node = node_id or self._node_id
        self._clock[node] = self._clock.get(node, 0) + 1
        return dict(self._clock)

    @staticmethod
    def _hash_state(state: StatePayload) -> str:
        canonical = canonical_dumps(state, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _attach_identity(self, commit: TimelineCommit) -> TimelineCommit:
        if commit.id is None:
            commit.id = self._next_id
            self._next_id += 1
        return commit

    def _persist(self, commit: TimelineCommit) -> None:
        if not SQLMODEL_AVAILABLE or self._session_factory is None:
            return
        with self._session_factory() as session:  # type: ignore[attr-defined]
            session.add(commit)
            session.commit()
            session.refresh(commit)

    def record_commit(
        self,
        state: Mapping[str, object],
        *,
        node_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> TimelineCommit:
        """Record a new state transition into the timeline."""

        state_json: StatePayload = dict(state)
        clock_snapshot = self._tick(node_id=node_id)
        commit = TimelineCommit(
            timestamp=timestamp or datetime.utcnow(),
            vector_clock=clock_snapshot,
            hash=self._hash_state(state_json),
            state_json=state_json,
        )
        self._attach_identity(commit)
        self._commits.append(commit)
        self._persist(commit)
        genesis_timeline_commits_total.inc()
        return commit

    def latest(self) -> Optional[TimelineCommit]:
        return self._commits[-1] if self._commits else None

    def vector_state(self) -> Optional[VectorClockState]:
        if not self._commits:
            return None
        commit = self._commits[-1]
        return VectorClockState(clock=dict(commit.vector_clock), timestamp=commit.timestamp)

    def list_commits(self, limit: Optional[int] = None) -> List[TimelineCommit]:
        commits = sorted(
            self._commits,
            key=lambda commit: (
                commit.timestamp,
                sorted(commit.vector_clock.items()),
            ),
        )
        if limit is not None:
            return commits[-limit:]
        return commits

    def get_commit(self, commit_id: int) -> TimelineCommit:
        for commit in self._commits:
            if commit.id == commit_id:
                return commit
        raise KeyError(f"Commit {commit_id} not found")

    def get_commit_by_timestamp(self, ts: datetime) -> TimelineCommit:
        matches = [commit for commit in self._commits if commit.timestamp == ts]
        if not matches:
            raise KeyError(f"Commit with timestamp {ts.isoformat()} not found")
        if len(matches) > 1:
            raise VectorClockError("Ambiguous commit selection for timestamp")
        return matches[0]

    def extend_from_commits(self, commits: Iterable[TimelineCommit]) -> None:
        for commit in commits:
            self._attach_identity(commit)
            self._commits.append(commit)
            self._clock = {
                key: max(commit.vector_clock.get(key, 0), self._clock.get(key, 0))
                for key in set(self._clock) | set(commit.vector_clock)
            }


__all__ = ["TimelineManager", "VectorClockState", "VectorClockError"]
