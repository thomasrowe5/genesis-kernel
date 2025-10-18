"""FastAPI routes exposing retrocausal and multiverse controls."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from genesis.multiverse import MultiverseCoherenceEngine
from genesis.retrocausal import (
    RetroConsistencyVerifier,
    RetrocausalBridge,
    ReverseSimulationRequest,
)

router = APIRouter(prefix="/retrocausal", tags=["retrocausal"])


class SimulationPayload(BaseModel):
    from_commit: str
    to_commit: str


class MergePayload(BaseModel):
    epsilon: float | None = None


def get_bridge() -> RetrocausalBridge:  # pragma: no cover - runtime wiring
    raise RuntimeError("RetrocausalBridge dependency not configured")


def get_verifier() -> RetroConsistencyVerifier:  # pragma: no cover - runtime wiring
    raise RuntimeError("RetroConsistencyVerifier dependency not configured")


def get_coherence_engine() -> MultiverseCoherenceEngine:  # pragma: no cover - runtime wiring
    raise RuntimeError("MultiverseCoherenceEngine dependency not configured")


@router.post("/simulate")
async def simulate(
    payload: SimulationPayload,
    bridge: RetrocausalBridge = Depends(get_bridge),
) -> Dict[str, Any]:
    report = await bridge.execute(
        ReverseSimulationRequest(from_commit=payload.from_commit, to_commit=payload.to_commit)
    )
    return {
        "path": list(report.simulation.path),
        "reward_delta": report.simulation.reward_delta,
        "entropy_delta": report.simulation.entropy_delta,
        "gradients": dict(report.update.gradients),
        "proof": {"hash": report.proof.run_hash, "valid": report.proof.valid},
    }


@router.get("/consistency")
async def consistency(verifier: RetroConsistencyVerifier = Depends(get_verifier)) -> Dict[str, Any]:
    chain = verifier.chain()
    if chain is None:
        raise HTTPException(status_code=404, detail="No retrocausal proofs recorded")
    return {"latest_hash": chain}


@router.get("/multiverse/state")
async def multiverse_state(engine: MultiverseCoherenceEngine = Depends(get_coherence_engine)) -> Dict[str, Any]:
    return {"branches": engine.summary(), "coherence": engine.coherence_score()}


@router.post("/multiverse/merge")
async def multiverse_merge(
    payload: MergePayload,
    engine: MultiverseCoherenceEngine = Depends(get_coherence_engine),
) -> Dict[str, Any]:
    if payload.epsilon is not None:
        engine.set_epsilon(payload.epsilon)
    report = await engine.merge()
    return {
        "coherence_score": report.coherence_score,
        "merged_branch": {"branch_id": report.merged_branch.branch_id, "metrics": dict(report.merged_branch.metrics)},
    }


__all__ = [
    "router",
    "get_bridge",
    "get_verifier",
    "get_coherence_engine",
]
