"""Federation governance API surface."""
from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from genesis.collective import FederationMesh

router = APIRouter(prefix="/federation", tags=["federation"])


class PeerPayload(BaseModel):
    url: str = Field(..., alias="host")
    pubkey: str
    stake: float = 0.0


class ProposalPayload(BaseModel):
    type: str = Field(..., alias="proposal_type")
    payload: dict[str, Any]
    proposer: str


class VotePayload(BaseModel):
    proposal_id: int
    decision: str
    voter: str


class LedgerEntry(BaseModel):
    from_id: int | None = None
    to_id: int | None = None
    amount: float
    reason: str
    at: str


class LedgerResponse(BaseModel):
    balances: dict[int, float]
    transactions: List[LedgerEntry]


def get_federation_mesh() -> FederationMesh:  # pragma: no cover - runtime wiring
    raise RuntimeError("FederationMesh dependency not configured")


@router.post("/peer")
async def register_peer(payload: PeerPayload, mesh: FederationMesh = Depends(get_federation_mesh)) -> dict[str, Any]:
    peer = await mesh.register_peer(host=payload.url, pubkey=payload.pubkey, stake=payload.stake)
    return {"id": peer.id, "host": peer.host, "status": peer.status}


@router.get("/peers")
async def list_peers(mesh: FederationMesh = Depends(get_federation_mesh)) -> list[dict[str, Any]]:
    peers = await mesh.peers()
    return [
        {
            "id": peer.id,
            "host": peer.host,
            "stake": peer.stake,
            "status": peer.status,
            "last_seen_at": peer.last_seen_at.isoformat(),
        }
        for peer in peers
    ]


@router.post("/proposal")
async def create_proposal(payload: ProposalPayload, mesh: FederationMesh = Depends(get_federation_mesh)) -> dict[str, Any]:
    proposal_id = await mesh.submit_proposal(
        proposal_type=payload.type, payload=payload.payload, proposer=payload.proposer
    )
    return {"proposal_id": proposal_id}


@router.post("/vote")
async def vote(payload: VotePayload, mesh: FederationMesh = Depends(get_federation_mesh)) -> dict[str, Any]:
    if payload.decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Decision must be approve or reject")
    approve = payload.decision == "approve"
    decision = await mesh.vote(payload.proposal_id, approve=approve, voter=payload.voter)
    return {"decision": decision.value}


@router.get("/ledger", response_model=LedgerResponse)
async def ledger(mesh: FederationMesh = Depends(get_federation_mesh)) -> LedgerResponse:
    snapshot = await mesh.ledger_snapshot()
    return LedgerResponse(
        balances=snapshot.balances,
        transactions=[
            LedgerEntry(
                from_id=tx.from_id,
                to_id=tx.to_id,
                amount=tx.amount,
                reason=tx.reason,
                at=tx.at.isoformat(),
            )
            for tx in snapshot.transactions
        ],
    )


__all__ = ["router", "get_federation_mesh"]
