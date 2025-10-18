"""Lifecycle coordination for replica clusters."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, MutableMapping

from genesis.metrics import genesis_self_repair_events_total


@dataclass(slots=True)
class ReplicaState:
    replica_id: int
    state: str
    updated_at: datetime
    note: str | None = None


class LifecycleCoordinator:
    """Tracks replica lifecycle events and emits repair metrics."""

    def __init__(self) -> None:
        self._states: MutableMapping[int, ReplicaState] = {}

    async def set_state(self, replica_id: int, state: str, *, note: str | None = None) -> ReplicaState:
        def _update() -> ReplicaState:
            record = ReplicaState(replica_id=replica_id, state=state, updated_at=datetime.utcnow(), note=note)
            self._states[replica_id] = record
            if state in {"repair", "retired"}:
                genesis_self_repair_events_total.inc()
            return record

        return await asyncio.to_thread(_update)

    def state(self, replica_id: int) -> ReplicaState | None:
        return self._states.get(replica_id)

    def snapshot(self) -> Mapping[int, ReplicaState]:
        return dict(self._states)


__all__ = ["LifecycleCoordinator", "ReplicaState"]
