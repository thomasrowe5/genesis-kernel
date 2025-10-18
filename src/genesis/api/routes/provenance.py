"""Provenance API endpoints."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query

from genesis.cluster.node import _default_service
from genesis.provenance.graph import ProvenanceGraph
from genesis.provenance.lineage import GraphExporter
from genesis.provenance.replay import ReplayRequest

router = APIRouter(prefix="/provenance", tags=["provenance"])
_graph = ProvenanceGraph()


@router.get("/graph")
def get_graph(job_id: str = Query(..., description="Job identifier to materialize")) -> Dict[str, Any]:
    subgraph = _graph.subgraph("Job", job_id)
    return subgraph.to_jsonable()


@router.post("/export")
def export_graph(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    path = payload.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Export path missing")
    GraphExporter(Path(path)).export(_graph)
    return {"status": "ok", "path": path}


@router.post("/replay")
async def replay(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    experiment_id = payload.get("experiment_id")
    if not experiment_id:
        raise HTTPException(status_code=400, detail="experiment_id required")
    result = await _default_service.replay_engine.replay(ReplayRequest(experiment_id=experiment_id))
    return {"status": "ok", "result_hash": result.output_hash}
