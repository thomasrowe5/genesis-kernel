"""Experiment planning and execution primitives for cognitive workflows."""
from __future__ import annotations

import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Mapping, MutableMapping, Optional

from genesis.metrics import genesis_experiments_total


@dataclass(slots=True)
class ExperimentPlan:
    """Description of an automatically generated experiment."""

    goal: str
    hypothesis: str
    controls: Mapping[str, Any]
    metrics: Mapping[str, float]
    seed: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExperimentResult:
    """Outcome of a completed experiment."""

    plan_id: str
    started_at: float
    finished_at: float
    metrics: Mapping[str, float]
    conclusion: str
    success: bool


class ExperimentRunner:
    """Execute experiment plans using a pluggable evaluator callback."""

    def __init__(
        self,
        evaluator: Callable[[ExperimentPlan], Awaitable[Mapping[str, float]]],
        *,
    ) -> None:
        self._evaluator = evaluator

    async def run(self, plan: ExperimentPlan) -> ExperimentResult:
        """Execute the plan, recording duration and metrics."""

        start = time.time()
        try:
            metrics = await self._evaluator(plan)
        except Exception as exc:  # pragma: no cover - defensive safety
            genesis_experiments_total.labels(status="failed").inc()
            raise RuntimeError(f"Experiment {plan.id} failed") from exc
        finished = time.time()
        genesis_experiments_total.labels(status="completed").inc()
        return ExperimentResult(
            plan_id=plan.id,
            started_at=start,
            finished_at=finished,
            metrics=dict(metrics),
            conclusion=self._derive_conclusion(plan, metrics),
            success=self._is_success(plan, metrics),
        )

    def _derive_conclusion(self, plan: ExperimentPlan, metrics: Mapping[str, float]) -> str:
        improvements: list[str] = []
        regressions: list[str] = []
        for metric, baseline in plan.metrics.items():
            value = metrics.get(metric, baseline)
            if value >= baseline:
                improvements.append(f"{metric} improved to {value:.3f}")
            else:
                regressions.append(f"{metric} regressed to {value:.3f}")
        if improvements and not regressions:
            return f"Hypothesis validated: {'; '.join(improvements)}"
        if regressions and not improvements:
            return f"Hypothesis rejected: {'; '.join(regressions)}"
        return "Mixed outcome: " + "; ".join(improvements + regressions)

    def _is_success(self, plan: ExperimentPlan, metrics: Mapping[str, float]) -> bool:
        return all(metrics.get(metric, value) >= value for metric, value in plan.metrics.items())


class ExperimentStatistics:
    """Aggregate statistics across experiment runs."""

    def __init__(self) -> None:
        self._durations: list[float] = []
        self._successes: int = 0
        self._count: int = 0

    def observe(self, result: ExperimentResult) -> None:
        self._count += 1
        self._successes += int(result.success)
        self._durations.append(result.finished_at - result.started_at)

    @property
    def total(self) -> int:
        return self._count

    @property
    def success_rate(self) -> float:
        if not self._count:
            return 0.0
        return self._successes / self._count

    @property
    def mean_duration(self) -> float:
        if not self._durations:
            return 0.0
        return statistics.mean(self._durations)


class InMemoryExperimentStore:
    """Simple in-memory persistence for experiments and results."""

    def __init__(self) -> None:
        self._plans: MutableMapping[str, ExperimentPlan] = {}
        self._results: MutableMapping[str, ExperimentResult] = {}

    def add_plan(self, plan: ExperimentPlan) -> None:
        self._plans[plan.id] = plan

    def get_plan(self, plan_id: str) -> Optional[ExperimentPlan]:
        return self._plans.get(plan_id)

    def list_plans(self) -> Iterable[ExperimentPlan]:
        return list(self._plans.values())

    def add_result(self, result: ExperimentResult) -> None:
        self._results[result.plan_id] = result

    def get_result(self, plan_id: str) -> Optional[ExperimentResult]:
        return self._results.get(plan_id)

    def list_results(self) -> Iterable[ExperimentResult]:
        return list(self._results.values())


async def run_experiments(
    plans: Iterable[ExperimentPlan],
    runner: ExperimentRunner,
) -> list[ExperimentResult]:
    """Execute multiple experiments sequentially."""

    results: list[ExperimentResult] = []
    for plan in plans:
        results.append(await runner.run(plan))
    return results


__all__ = [
    "ExperimentPlan",
    "ExperimentResult",
    "ExperimentRunner",
    "ExperimentStatistics",
    "InMemoryExperimentStore",
    "run_experiments",
]
