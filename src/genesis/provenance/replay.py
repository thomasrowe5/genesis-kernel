"""Deterministic replay engine for provenance experiments."""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Mapping, Optional


@dataclass
class ReplayRequest:
    experiment_id: str
    seed: Optional[int] = None


@dataclass
class ReplayResult:
    experiment_id: str
    output_hash: str


class ReplayEngine:
    """Stores deterministic replay handlers for experiments."""

    def __init__(self) -> None:
        self._executors: Dict[str, Callable[[ReplayRequest], Awaitable[Mapping[str, object]]]] = {}

    def register(self, experiment_id: str, executor: Callable[[ReplayRequest], Awaitable[Mapping[str, object]]]) -> None:
        self._executors[experiment_id] = executor

    async def replay(self, request: ReplayRequest) -> ReplayResult:
        if request.experiment_id not in self._executors:
            async def default_executor(_: ReplayRequest) -> Mapping[str, object]:
                return {"status": "noop"}

            self.register(request.experiment_id, default_executor)
        executor = self._executors[request.experiment_id]
        payload = await executor(request)
        digest = hashlib.sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        return ReplayResult(experiment_id=request.experiment_id, output_hash=digest)

    def register_sync(self, experiment_id: str, executor: Callable[[ReplayRequest], Mapping[str, object]]) -> None:
        async def async_executor(request: ReplayRequest) -> Mapping[str, object]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: executor(request))

        self.register(experiment_id, async_executor)
