"""FastAPI routes exposing reflexive intelligence state."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from genesis.metacog.reflection import ReflectionJournal
from genesis.metacog.selfquery import SelfQueryService
from genesis.metacog.uncertainty import UncertaintyTracker
from genesis.reflexion.simulator import SimulationChange, SimulationResult, TwinSimulator
from genesis.reflexion.twin import DigitalTwinBuilder, TwinState

router = APIRouter(prefix="/reflexion", tags=["reflexion"])


def get_twin_builder() -> DigitalTwinBuilder:  # pragma: no cover - runtime wiring
    raise RuntimeError("DigitalTwinBuilder dependency not configured")


def get_simulator() -> TwinSimulator:  # pragma: no cover - runtime wiring
    raise RuntimeError("TwinSimulator dependency not configured")


def get_reflection_journal() -> ReflectionJournal:  # pragma: no cover - runtime wiring
    raise RuntimeError("ReflectionJournal dependency not configured")


def get_uncertainty_tracker() -> UncertaintyTracker:  # pragma: no cover - runtime wiring
    raise RuntimeError("UncertaintyTracker dependency not configured")


def get_self_query_service() -> SelfQueryService:  # pragma: no cover - runtime wiring
    raise RuntimeError("SelfQueryService dependency not configured")


@router.get("/twin/state", response_model=TwinState)
async def twin_state(builder: DigitalTwinBuilder = Depends(get_twin_builder)) -> TwinState:
    return await builder.build_snapshot()


@router.post("/simulate/change", response_model=SimulationResult)
async def simulate_change(
    change: SimulationChange,
    simulator: TwinSimulator = Depends(get_simulator),
    builder: DigitalTwinBuilder = Depends(get_twin_builder),
) -> SimulationResult:
    snapshot = await builder.build_snapshot()
    return await simulator.run(change, base_state=snapshot)


@router.get("/reflection/logs")
async def reflection_logs(
    journal: ReflectionJournal = Depends(get_reflection_journal),
    since: datetime | None = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    entries = journal.query(since=since, limit=limit)
    return [
        {
            "reason": entry.reason,
            "prediction": entry.prediction,
            "result": entry.result,
            "delta": entry.delta,
            "confidence": entry.confidence,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in entries
    ]


@router.get("/uncertainty")
async def uncertainty_report(tracker: UncertaintyTracker = Depends(get_uncertainty_tracker)) -> Dict[str, Any]:
    return {
        "global_confidence": tracker.global_confidence(),
        "metrics": [
            {"key": record.key, "mean": record.mean, "stddev": record.stddev, "updated": record.last_updated.isoformat()}
            for record in tracker.export()
        ],
    ]


__all__ = [
    "router",
    "get_twin_builder",
    "get_simulator",
    "get_reflection_journal",
    "get_uncertainty_tracker",
    "get_self_query_service",
]
