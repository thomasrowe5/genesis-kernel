"""FastAPI routes exposing temporal recursion controls."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from genesis.temporal import (
    TemporalBranchManager,
    TemporalObserver,
    TemporalRecursionScheduler,
    TemporalReconciler,
    TimelineManager,
)

router = APIRouter(prefix="/temporal", tags=["temporal"])


def get_timeline_manager() -> TimelineManager:  # pragma: no cover - runtime wiring
    raise RuntimeError("TimelineManager dependency not configured")


def get_recursion_scheduler() -> TemporalRecursionScheduler:  # pragma: no cover - runtime wiring
    raise RuntimeError("TemporalRecursionScheduler dependency not configured")


def get_temporal_simulator():  # pragma: no cover - runtime wiring
    raise RuntimeError("Temporal simulator dependency not configured")


def get_branch_manager() -> TemporalBranchManager:  # pragma: no cover - runtime wiring
    raise RuntimeError("TemporalBranchManager dependency not configured")


def get_reconciler() -> TemporalReconciler:  # pragma: no cover - runtime wiring
    raise RuntimeError("TemporalReconciler dependency not configured")


def get_temporal_observer() -> TemporalObserver:  # pragma: no cover - runtime wiring
    raise RuntimeError("TemporalObserver dependency not configured")


class SnapshotRequest(BaseModel):
    state: Dict[str, Any]
    node_id: str | None = None
    timestamp: datetime | None = None


class RecursionRequest(BaseModel):
    commit_id: int
    label: str | None = None


class MergeRequest(BaseModel):
    branch_id: int
    actual_state: Dict[str, Any]


@router.post("/timeline/snapshot")
async def create_snapshot(
    request: SnapshotRequest,
    manager: TimelineManager = Depends(get_timeline_manager),
) -> Dict[str, Any]:
    commit = manager.record_commit(request.state, node_id=request.node_id, timestamp=request.timestamp)
    return {
        "id": commit.id,
        "timestamp": commit.timestamp.isoformat(),
        "vector_clock": commit.vector_clock,
        "hash": commit.hash,
    }


@router.post("/recursion/run")
async def run_recursion(
    request: RecursionRequest,
    scheduler: TemporalRecursionScheduler = Depends(get_recursion_scheduler),
    simulator=Depends(get_temporal_simulator),
) -> Dict[str, Any]:
    try:
        result = await scheduler.run_from_commit(request.commit_id, simulator, label=request.label)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response: Dict[str, Any] = {
        "run_id": result.run.id,
        "from_commit": result.run.from_commit,
        "to_commit": result.run.to_commit,
        "status": result.run.status,
        "delta": result.delta,
        "prediction": result.prediction,
    }
    if result.alert is not None:
        response["alert"] = {
            "type": result.alert.type,
            "severity": result.alert.severity,
            "description": result.alert.description,
            "at": result.alert.at.isoformat(),
        }
    return response


@router.get("/branch/list")
async def list_branches(manager: TemporalBranchManager = Depends(get_branch_manager)) -> List[Dict[str, Any]]:
    branches = manager.list_branches()
    return [
        {
            "id": branch.id,
            "parent_id": branch.parent_id,
            "divergence_score": branch.divergence_score,
            "merged": branch.merged,
            "name": branch.name,
            "created_at": branch.created_at.isoformat(),
        }
        for branch in branches
    ]


@router.post("/branch/merge")
async def merge_branch(
    request: MergeRequest,
    manager: TemporalBranchManager = Depends(get_branch_manager),
    reconciler: TemporalReconciler = Depends(get_reconciler),
) -> Dict[str, Any]:
    try:
        snapshot = manager.snapshot_payload(request.branch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    report = reconciler.reconcile(snapshot, request.actual_state)
    try:
        branch = manager.merge_branch(request.branch_id, report)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "branch_id": branch.id,
        "score": report.score,
        "delta": report.delta,
        "violations": report.status.violations,
    }


@router.get("/continuity/status")
async def continuity_status(
    reconciler: TemporalReconciler = Depends(get_reconciler),
    observer: TemporalObserver = Depends(get_temporal_observer),
) -> Dict[str, Any]:
    metrics = [
        {"value": metric.value, "delta": metric.delta, "at": metric.at.isoformat()}
        for metric in reconciler.metrics
    ]
    alerts = [
        {
            "type": alert.type,
            "severity": alert.severity,
            "description": alert.description,
            "at": alert.at.isoformat(),
        }
        for alert in observer.alerts
    ]
    return {"metrics": metrics, "alerts": alerts}


__all__ = [
    "router",
    "get_timeline_manager",
    "get_recursion_scheduler",
    "get_temporal_simulator",
    "get_branch_manager",
    "get_reconciler",
    "get_temporal_observer",
]
