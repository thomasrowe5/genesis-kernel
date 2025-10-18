"""REST endpoints exposing cognition services."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from genesis.cognition import ExperimentPlanner, PlannerContext, ReportSummarizer
from genesis.research import (
    ExperimentPlan,
    ExperimentResult,
    ExperimentRunner,
    ExperimentReporter,
    InMemoryExperimentStore,
)

router = APIRouter(prefix="/cognition", tags=["cognition"])


def get_planner() -> ExperimentPlanner:  # pragma: no cover - runtime wiring
    raise RuntimeError("ExperimentPlanner dependency not configured")


def get_store() -> InMemoryExperimentStore:  # pragma: no cover - runtime wiring
    raise RuntimeError("Experiment store dependency not configured")


def get_runner() -> ExperimentRunner:  # pragma: no cover - runtime wiring
    raise RuntimeError("Experiment runner dependency not configured")


def get_reporter() -> ExperimentReporter:  # pragma: no cover - runtime wiring
    raise RuntimeError("Experiment reporter dependency not configured")


def get_summarizer() -> ReportSummarizer:  # pragma: no cover - runtime wiring
    raise RuntimeError("Report summarizer dependency not configured")


class PlanRequest(BaseModel):
    goal: str
    performance_gaps: dict[str, float] | None = Field(default=None, alias="gaps")
    prior_metrics: dict[str, List[float]] | None = None
    limit: int = 1


class PlanResponse(BaseModel):
    id: str
    goal: str
    hypothesis: str
    controls: dict[str, object]
    metrics: dict[str, float]

    @classmethod
    def from_plan(cls, plan: ExperimentPlan) -> "PlanResponse":
        return cls(
            id=plan.id,
            goal=plan.goal,
            hypothesis=plan.hypothesis,
            controls=dict(plan.controls),
            metrics=dict(plan.metrics),
        )


class RunRequest(BaseModel):
    plan_id: str


class RunResponse(BaseModel):
    plan_id: str
    success: bool
    conclusion: str
    metrics: dict[str, float]

    @classmethod
    def from_result(cls, result: ExperimentResult) -> "RunResponse":
        return cls(
            plan_id=result.plan_id,
            success=result.success,
            conclusion=result.conclusion,
            metrics=dict(result.metrics),
        )


class StatusEntry(BaseModel):
    plan_id: str
    status: str


class InsightResponse(BaseModel):
    statement: str
    confidence: float


class ReportResponse(BaseModel):
    plan_id: str
    content: str


@router.post("/plan", response_model=list[PlanResponse])
def plan(
    request: PlanRequest,
    planner: ExperimentPlanner = Depends(get_planner),
    store: InMemoryExperimentStore = Depends(get_store),
) -> list[PlanResponse]:
    context = PlannerContext(
        goal=request.goal,
        performance_gaps=request.performance_gaps or {},
        prior_metrics=request.prior_metrics or {},
    )
    plans = planner.propose(context, limit=request.limit)
    for plan_item in plans:
        store.add_plan(plan_item)
    return [PlanResponse.from_plan(plan_item) for plan_item in plans]


@router.post("/run", response_model=RunResponse)
async def run_plan(
    request: RunRequest,
    store: InMemoryExperimentStore = Depends(get_store),
    runner: ExperimentRunner = Depends(get_runner),
    reporter: ExperimentReporter = Depends(get_reporter),
) -> RunResponse:
    plan_item = store.get_plan(request.plan_id)
    if plan_item is None:
        raise HTTPException(status_code=404, detail="Unknown plan")
    result = await runner.run(plan_item)
    store.add_result(result)
    reporter.add_result(result)
    return RunResponse.from_result(result)


@router.get("/status", response_model=list[StatusEntry])
def status(store: InMemoryExperimentStore = Depends(get_store)) -> list[StatusEntry]:
    entries: list[StatusEntry] = []
    for plan_item in store.list_plans():
        result = store.get_result(plan_item.id)
        status_value = "completed" if result else "pending"
        entries.append(StatusEntry(plan_id=plan_item.id, status=status_value))
    return entries


@router.get("/insight", response_model=list[InsightResponse])
def insight(reporter: ExperimentReporter = Depends(get_reporter)) -> list[InsightResponse]:
    return [InsightResponse(statement=item.statement, confidence=item.confidence) for item in reporter.list_insights()]


@router.get("/report/{plan_id}", response_model=ReportResponse)
def report(
    plan_id: str,
    store: InMemoryExperimentStore = Depends(get_store),
    reporter: ExperimentReporter = Depends(get_reporter),
    summarizer: ReportSummarizer = Depends(get_summarizer),
) -> ReportResponse:
    plan_item = store.get_plan(plan_id)
    if plan_item is None:
        raise HTTPException(status_code=404, detail="Unknown plan")
    result = store.get_result(plan_id)
    if result is None:
        raise HTTPException(status_code=409, detail="Experiment not completed")
    insights = [insight.statement for insight in reporter.list_insights()]
    summary = summarizer.render(plan_item, result, insights)
    return ReportResponse(plan_id=plan_id, content=summary.content)


__all__ = [
    "router",
    "get_planner",
    "get_store",
    "get_runner",
    "get_reporter",
    "get_summarizer",
]
