"""Local persistence helpers for cognition CLI workflows."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Mapping

from genesis.research import ExperimentPlan, ExperimentResult


class CognitionState:
    """Persist plans and results to a JSON document for the CLI."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._plans: Dict[str, ExperimentPlan] = {}
        self._results: Dict[str, ExperimentResult] = {}
        self._insights: list[str] = []
        if path.exists():
            self._load()

    def _load(self) -> None:
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        for plan_data in payload.get("plans", []):
            plan = ExperimentPlan(
                goal=plan_data["goal"],
                hypothesis=plan_data["hypothesis"],
                controls=plan_data["controls"],
                metrics=plan_data["metrics"],
                seed=plan_data["seed"],
                id=plan_data["id"],
                metadata=plan_data.get("metadata", {}),
            )
            self._plans[plan.id] = plan
        for result_data in payload.get("results", []):
            result = ExperimentResult(
                plan_id=result_data["plan_id"],
                started_at=result_data["started_at"],
                finished_at=result_data["finished_at"],
                metrics=result_data["metrics"],
                conclusion=result_data["conclusion"],
                success=result_data["success"],
            )
            self._results[result.plan_id] = result
        self._insights = list(payload.get("insights", []))

    def _save(self) -> None:
        payload = {
            "plans": [self._plan_to_dict(plan) for plan in self._plans.values()],
            "results": [self._result_to_dict(result) for result in self._results.values()],
            "insights": list(self._insights),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_plan(self, plan: ExperimentPlan) -> None:
        self._plans[plan.id] = plan
        self._save()

    def add_result(self, result: ExperimentResult) -> None:
        self._results[result.plan_id] = result
        self._save()

    def add_insight(self, insight: str) -> None:
        self._insights.append(insight)
        self._save()

    def get_plan(self, plan_id: str) -> ExperimentPlan | None:
        return self._plans.get(plan_id)

    def get_result(self, plan_id: str) -> ExperimentResult | None:
        return self._results.get(plan_id)

    def plans(self) -> Iterable[ExperimentPlan]:
        return list(self._plans.values())

    def results(self) -> Iterable[ExperimentResult]:
        return list(self._results.values())

    def insights(self) -> Iterable[str]:
        return list(self._insights)

    @staticmethod
    def _plan_to_dict(plan: ExperimentPlan) -> Mapping[str, object]:
        return {
            "goal": plan.goal,
            "hypothesis": plan.hypothesis,
            "controls": dict(plan.controls),
            "metrics": dict(plan.metrics),
            "seed": plan.seed,
            "id": plan.id,
            "metadata": dict(plan.metadata),
        }

    @staticmethod
    def _result_to_dict(result: ExperimentResult) -> Mapping[str, object]:
        return {
            "plan_id": result.plan_id,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "metrics": dict(result.metrics),
            "conclusion": result.conclusion,
            "success": result.success,
        }


__all__ = ["CognitionState"]
