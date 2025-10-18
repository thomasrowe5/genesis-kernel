"""Sandbox execution environment for proposed adaptations."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from genesis.reflexion.mirror import TwinMirror
from genesis.reflexion.simulator import SimulationChange
from genesis.reflexion.twin import DigitalTwinBuilder, TwinState


class SandboxResult(TwinState):
    """Alias for clarity when sandbox returns a twin state."""


class AdaptationSandbox:
    """Manage sandboxed executions using digital twin mirrors."""

    def __init__(self, twin_builder: DigitalTwinBuilder) -> None:
        self._builder = twin_builder

    @asynccontextmanager
    async def run(
        self,
        change: SimulationChange,
        *,
        base_state: Optional[TwinState] = None,
    ) -> AsyncIterator[TwinState]:
        snapshot = base_state or await self._builder.build_snapshot()
        mirror = TwinMirror(snapshot)
        async with mirror.sandbox(change.dict()) as state:
            yield state
