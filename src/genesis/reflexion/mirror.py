"""Sandbox mirroring helpers for reflexive experimentation."""
from __future__ import annotations

from contextlib import asynccontextmanager
from copy import deepcopy
from typing import Any, AsyncIterator, Mapping

from .twin import TwinState


class TwinMirror:
    """Create isolated mirrors of the digital twin for experimentation."""

    def __init__(self, state: TwinState) -> None:
        self._state = state

    def snapshot(self) -> TwinState:
        """Return a deep-copied snapshot of the mirrored state."""

        return TwinState(
            at=self._state.at,
            topology=deepcopy(self._state.topology),
            metrics=deepcopy(self._state.metrics),
            config=deepcopy(self._state.config),
        )

    def apply_change(self, change: Mapping[str, Any]) -> TwinState:
        """Produce a modified state reflecting the proposed change."""

        mirrored = self.snapshot()
        pending = deepcopy(mirrored.config.get("pending_changes", {}))
        pending_key = change.get("module", "unknown")
        pending[pending_key] = dict(change)
        mirrored.config["pending_changes"] = pending
        return mirrored

    @asynccontextmanager
    async def sandbox(self, change: Mapping[str, Any] | None = None) -> AsyncIterator[TwinState]:
        """Async context manager yielding an isolated sandbox state."""

        state = self.snapshot() if change is None else self.apply_change(change)
        yield state
