"""Adaptive workload allocator across federations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Mapping, MutableMapping

from genesis.metrics import genesis_adaptation_cycles_total


@dataclass(slots=True)
class AdaptationGoal:
    name: str
    weight_energy: float = 1.0
    weight_latency: float = 1.0
    weight_risk: float = 1.0


class GlobalAdaptationEngine:
    """Computes resource reallocations based on weighted multi-objective cost."""

    def __init__(self) -> None:
        self._allocations: MutableMapping[str, float] = {}

    async def optimise(self, goal: str) -> Mapping[str, float]:
        await asyncio.sleep(0)
        parsed = self._parse_goal(goal)
        plan = self._compute_plan(parsed)
        genesis_adaptation_cycles_total.inc()
        self._allocations = dict(plan)
        return plan

    def allocations(self) -> Mapping[str, float]:
        return dict(self._allocations)

    def _parse_goal(self, goal: str) -> AdaptationGoal:
        lowered = goal.lower()
        if "latency" in lowered:
            return AdaptationGoal(name=goal, weight_latency=2.0)
        if "energy" in lowered:
            return AdaptationGoal(name=goal, weight_energy=2.5)
        if "risk" in lowered:
            return AdaptationGoal(name=goal, weight_risk=2.5)
        if "balance" in lowered:
            return AdaptationGoal(name=goal, weight_energy=1.5, weight_latency=1.5, weight_risk=1.0)
        return AdaptationGoal(name=goal)

    def _compute_plan(self, goal: AdaptationGoal) -> Mapping[str, float]:
        # Simple heuristic: allocate weights normalised to 1.0
        total = goal.weight_energy + goal.weight_latency + goal.weight_risk
        if total == 0:
            return {"energy": 0.0, "latency": 0.0, "risk": 0.0}
        plan = {
            "energy": goal.weight_energy / total,
            "latency": goal.weight_latency / total,
            "risk": goal.weight_risk / total,
        }
        return plan


__all__ = ["GlobalAdaptationEngine", "AdaptationGoal"]
