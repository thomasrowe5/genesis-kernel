"""Simulation utilities for the reflexive intelligence layer."""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from genesis.metrics import genesis_simulations_total
from genesis.utils.json_utils import canonical_dumps_bytes
from genesis.utils.pydantic_compat import BaseModel, Field

from .models import SQLMODEL_AVAILABLE, SimulationRun
from .twin import DigitalTwinBuilder, TwinState


class SimulationChange(BaseModel):
    """Specification for a proposed modification to Genesis."""

    module: str
    param: str
    value: Any
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class SimulationResult(BaseModel):
    """Outcome predicted by the simulator."""

    change: SimulationChange
    predicted_delta: dict[str, float]
    confidence: float
    seed: int
    generated_at: datetime


@dataclass(slots=True)
class SimulationStore:
    session_factory: Optional[callable] = None
    _runs: list[SimulationRun] = field(default_factory=list)

    def add(self, run: SimulationRun) -> None:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                session.add(run)
                session.commit()
                session.refresh(run)
        else:
            self._runs.append(run)

    def recent(self, limit: int = 10) -> list[SimulationRun]:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session, select  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                statement = select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(limit)
                return list(session.exec(statement))
        return list(self._runs[-limit:])


class TwinSimulator:
    """Run isolated simulations for proposed Genesis modifications."""

    def __init__(
        self,
        twin_builder: DigitalTwinBuilder,
        *,
        session_factory: Optional[callable] = None,
    ) -> None:
        self._builder = twin_builder
        self._store = SimulationStore(session_factory=session_factory)

    async def run(
        self,
        change: SimulationChange,
        *,
        base_state: Optional[TwinState] = None,
        seed: Optional[int] = None,
    ) -> SimulationResult:
        state = base_state or await self._builder.build_snapshot()
        serialized_change = canonical_dumps_bytes(change.dict())
        derived_seed = seed if seed is not None else int(hashlib.sha256(serialized_change).hexdigest()[:8], 16)
        rng = random.Random(derived_seed)
        predicted_delta: Dict[str, float] = {}

        for key, value in state.metrics.items():
            influence = 0.05 * (1.0 if change.module in key else 0.5)
            adjustment = (rng.random() - 0.5) * influence
            predicted_delta[key] = round(adjustment, 6)

        magnitude = float(math.fsum(abs(v) for v in predicted_delta.values()))
        confidence = max(0.05, 1.0 / (1.0 + magnitude))
        result = SimulationResult(
            change=change,
            predicted_delta=predicted_delta,
            confidence=confidence,
            seed=derived_seed,
            generated_at=datetime.utcnow(),
        )
        self._persist(result)
        genesis_simulations_total.labels(status="predicted").inc()
        return result

    def recent(self, limit: int = 5) -> list[SimulationResult]:
        runs = self._store.recent(limit=limit)
        return [
            SimulationResult(
                change=SimulationChange(**run.change_json),
                predicted_delta=run.predicted_delta,
                confidence=run.confidence,
                seed=int(run.change_json.get("seed", 0)),
                generated_at=run.created_at,
            )
            for run in runs
        ]

    def _persist(self, result: SimulationResult) -> None:
        payload = SimulationRun(
            change_json=result.change.dict(),
            predicted_delta=result.predicted_delta,
            outcome_json={},
            executed=False,
            confidence=result.confidence,
            created_at=result.generated_at,
        )
        self._store.add(payload)
