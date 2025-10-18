"""API surface for orchestration operations."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from genesis.registry.manager import ModuleRegistryManager

from ...router.router import PromptRouter

router = APIRouter(prefix="/orchestrate", tags=["orchestration"])


def get_registry_manager() -> ModuleRegistryManager:  # pragma: no cover - runtime wiring
    raise RuntimeError("ModuleRegistryManager dependency not configured")


def get_prompt_router() -> PromptRouter:  # pragma: no cover - runtime wiring
    raise RuntimeError("PromptRouter dependency not configured")


class RouteRequest(BaseModel):
    task_type: str
    args: list[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] | None = None


@router.post("/route")
def route_request(
    payload: RouteRequest,
    router_dep: PromptRouter = Depends(get_prompt_router),
) -> Dict[str, str]:
    decision = router_dep.route(payload.task_type, context=payload.context or {})
    return {"module": decision.module, "version": decision.version}


class CanaryRequest(BaseModel):
    module: str
    candidate_version: str
    initial_share: float = Field(default=0.01, ge=0.0, le=1.0)


@router.post("/canary")
def start_canary(
    payload: CanaryRequest,
    registry: ModuleRegistryManager = Depends(get_registry_manager),
) -> Dict[str, Any]:
    try:
        candidate = registry.start_canary(payload.module, payload.candidate_version, payload.initial_share)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"module": candidate.name, "version": candidate.version, "share": candidate.traffic_share}


class TrafficRequest(BaseModel):
    module: str
    splits: Dict[str, float]


@router.post("/traffic")
def set_traffic(
    payload: TrafficRequest,
    registry: ModuleRegistryManager = Depends(get_registry_manager),
) -> Dict[str, Any]:
    try:
        updates = registry.set_traffic_splits(payload.module, payload.splits)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "module": payload.module,
        "splits": {module.version: module.traffic_share for module in updates},
    }


@router.get("/status")
def status(
    module: str = Query(..., description="Module name to inspect"),
    registry: ModuleRegistryManager = Depends(get_registry_manager),
) -> Dict[str, Any]:
    versions = registry.versions(module)
    if not versions:
        raise HTTPException(status_code=404, detail=f"Unknown module {module}")
    data = [
        {
            "version": mv.version,
            "active": mv.active,
            "canary": mv.canary,
            "traffic_share": mv.traffic_share,
            "reward_ma": mv.reward_ma,
            "p95_ms": mv.p95_ms,
            "error_rate": mv.error_rate,
        }
        for mv in versions
    ]
    return {"module": module, "versions": data}


class RollbackRequest(BaseModel):
    module: str
    version: str
    reason: str


@router.post("/rollback")
def rollback(
    payload: RollbackRequest,
    registry: ModuleRegistryManager = Depends(get_registry_manager),
) -> Dict[str, Any]:
    try:
        variant = registry.rollback(payload.module, payload.version, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"module": variant.name, "version": variant.version, "rolled_back": True}


__all__ = [
    "router",
    "get_registry_manager",
    "get_prompt_router",
]
