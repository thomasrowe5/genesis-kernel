"""FastAPI routes exposing the cosmic coordination service."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from genesis.cosmic.service import CosmicNetworkService
from genesis.cosmic.consensus_ld import LongDelayConsensus

router = APIRouter(prefix="/cosmic", tags=["cosmic"])


def get_cosmic_service() -> CosmicNetworkService:  # pragma: no cover - runtime wiring
    raise RuntimeError("CosmicNetworkService dependency not configured")


def get_consensus() -> LongDelayConsensus:  # pragma: no cover - runtime wiring
    raise RuntimeError("Consensus dependency not configured")


class SeedDeployRequest(BaseModel):
    target: str
    knowledge: Dict[str, Any]


class SeedDeployResponse(BaseModel):
    seed_id: str
    hash_hex: str


class SeedStatusResponse(BaseModel):
    seed_id: str
    target: str
    launched_at: str
    hash_hex: str
    status: str


class CosmicSyncRequest(BaseModel):
    state: Dict[str, Dict[str, Any]]


class CosmicSyncResponse(BaseModel):
    merkle: str


@router.post("/seed/deploy", response_model=SeedDeployResponse)
async def deploy_seed(
    request: SeedDeployRequest,
    service: CosmicNetworkService = Depends(get_cosmic_service),
) -> SeedDeployResponse:
    package = await service.deploy_seed(request.target, request.knowledge)
    return SeedDeployResponse(seed_id=package.seed_id, hash_hex=package.hash_hex)


@router.get("/seed/status/{seed_id}", response_model=SeedStatusResponse)
async def seed_status(
    seed_id: str,
    service: CosmicNetworkService = Depends(get_cosmic_service),
) -> SeedStatusResponse:
    status = service.seed_status(seed_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown seed {seed_id}")
    return SeedStatusResponse(
        seed_id=status.seed_id,
        target=status.target,
        launched_at=status.launched_at.isoformat(),
        hash_hex=status.hash_hex,
        status=status.status,
    )


@router.get("/metrics")
async def cosmic_metrics(
    service: CosmicNetworkService = Depends(get_cosmic_service),
) -> Dict[str, Any]:
    return {
        "chronicle_events": [record.event.type for record in service.chronicle_events()],
    }


@router.post("/sync", response_model=CosmicSyncResponse)
async def cosmic_sync(
    request: CosmicSyncRequest,
    service: CosmicNetworkService = Depends(get_cosmic_service),
    consensus: LongDelayConsensus = Depends(get_consensus),
) -> CosmicSyncResponse:
    for seed_id, payload in request.state.items():
        await consensus.update(seed_id, payload)
    merkle = await service.cosmic_sync(consensus)
    return CosmicSyncResponse(merkle=merkle)


__all__ = [
    "router",
    "get_cosmic_service",
    "get_consensus",
    "SeedDeployRequest",
    "SeedDeployResponse",
    "CosmicSyncRequest",
    "CosmicSyncResponse",
]
