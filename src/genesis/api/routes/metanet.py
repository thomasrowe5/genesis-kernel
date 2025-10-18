"""FastAPI routes exposing planetary meta-network controls."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from genesis.metanet.runtime import get_runtime

router = APIRouter(prefix="/metanet", tags=["metanet"])


class FederationPayload(BaseModel):
    federation_id: str
    name: str
    public_key: str | None = None
    endpoints: List[str]
    capabilities: Dict[str, float] = Field(default_factory=dict)


class TreatyRequest(BaseModel):
    parties: List[str]
    payload: Dict[str, Any]


class TreatyResponse(BaseModel):
    treaty_id: str
    state: str
    parties: List[str]
    payload: Dict[str, Any]


class ExchangeRequest(BaseModel):
    partner: str
    credits: float
    asset_type: str = "credit"


class ExchangeResponse(BaseModel):
    tx_id: str
    proof_hash: str
    amount: float
    asset_type: str


class AdaptationRequest(BaseModel):
    goal: str


@router.get("/federations", response_model=List[FederationPayload])
async def list_federations() -> List[FederationPayload]:
    runtime = get_runtime()
    federations = []
    for federation in runtime.interconnect.federations().values():
        federations.append(
            FederationPayload(
                federation_id=federation.federation_id,
                name=federation.human_name,
                public_key=runtime.federation_keys.get(federation.federation_id),
                endpoints=federation.endpoints,
                capabilities=dict(federation.capabilities),
            )
        )
    return federations


@router.post("/treaty", response_model=TreatyResponse)
async def negotiate_treaty(request: TreatyRequest = Body(...)) -> TreatyResponse:
    runtime = get_runtime()
    missing = [party for party in request.parties if party not in runtime.federation_keys]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown federations: {', '.join(missing)}")
    public_keys = {party: runtime.public_key(party) for party in request.parties}
    treaty = await runtime.diplomat.negotiate_treaty(parties=request.parties, payload=request.payload, public_keys=public_keys)
    runtime.intelligence.update_peace_index(runtime.treaties.active_treaty_count(), disputes=0)
    return TreatyResponse(
        treaty_id=treaty.treaty_id,
        state=treaty.state.value,
        parties=list(treaty.all_parties()),
        payload=dict(treaty.payload),
    )


@router.post("/exchange", response_model=ExchangeResponse)
async def perform_exchange(request: ExchangeRequest = Body(...)) -> ExchangeResponse:
    runtime = get_runtime()
    if request.partner not in runtime.federation_keys:
        raise HTTPException(status_code=404, detail=f"Unknown federation {request.partner}")
    receipt = runtime.ledger.execute_atomic_swap(
        from_federation="planetary-treasury",
        to_federation=request.partner,
        amount=request.credits,
        asset_type=request.asset_type,
    )
    return ExchangeResponse(
        tx_id=receipt.tx_id,
        proof_hash=receipt.proof_hash,
        amount=receipt.amount,
        asset_type=receipt.asset_type,
    )


@router.get("/global_metrics")
async def global_metrics() -> Mapping[str, Mapping[str, float]]:
    runtime = get_runtime()
    return runtime.intelligence.snapshot()


@router.post("/adapt")
async def adapt(request: AdaptationRequest = Body(...)) -> Mapping[str, float]:
    runtime = get_runtime()
    plan = await runtime.diplomat.adapt_global_state(request.goal)
    return plan


__all__ = ["router"]
