"""Scheduler utilities coordinating cognitive research tasks."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Awaitable, Callable, Deque, Optional

from genesis.metrics import genesis_hypotheses_generated_total

from .experiment import ExperimentPlan


@dataclass(slots=True)
class ScheduledExperiment:
    """Entry stored in the scheduler queue."""

    plan: ExperimentPlan
    priority: int = 0


class ExperimentScheduler:
    """Minimal async scheduler for experiments."""

    def __init__(self) -> None:
        self._queue: Deque[ScheduledExperiment] = deque()
        self._lock = asyncio.Lock()

    async def schedule(self, plan: ExperimentPlan, *, priority: int = 0) -> None:
        async with self._lock:
            if priority:
                self._queue.appendleft(ScheduledExperiment(plan, priority))
            else:
                self._queue.append(ScheduledExperiment(plan, priority))
            genesis_hypotheses_generated_total.inc()

    async def next(self) -> Optional[ExperimentPlan]:
        async with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft().plan

    async def run(
        self,
        worker: Callable[[ExperimentPlan], Awaitable[None]],
        *,
        poll_interval: float = 0.1,
    ) -> None:
        """Continuously consume experiments using *worker*."""

        while True:
            plan = await self.next()
            if plan is None:
                await asyncio.sleep(poll_interval)
                continue
            await worker(plan)


__all__ = ["ExperimentScheduler", "ScheduledExperiment"]
