"""SQLModel data definitions for retrocausal records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

try:  # pragma: no cover - optional SQLModel dependency path
    from sqlmodel import Field, SQLModel
except Exception:  # pragma: no cover - SQLModel unavailable
    SQLModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]


SQLMODEL_AVAILABLE = Field is not None


if SQLMODEL_AVAILABLE:

    class RetroRun(SQLModel, table=True):  # type: ignore[misc, valid-type]
        id: int | None = Field(default=None, primary_key=True)
        from_commit: str
        to_commit: str
        reward_delta: float
        entropy_delta: float
        verified: bool = False


    class RetroProof(SQLModel, table=True):  # type: ignore[misc, valid-type]
        id: int | None = Field(default=None, primary_key=True)
        run_id: int = Field(foreign_key="retrorun.id")
        hash: str
        valid: bool
        created_at: datetime = Field(default_factory=datetime.utcnow)


    class MultiverseState(SQLModel, table=True):  # type: ignore[misc, valid-type]
        id: int | None = Field(default=None, primary_key=True)
        branches_json: Dict[str, Any]
        coherence_score: float
        at: datetime = Field(default_factory=datetime.utcnow)


    class DivergenceEvent(SQLModel, table=True):  # type: ignore[misc, valid-type]
        id: int | None = Field(default=None, primary_key=True)
        branch_a: str
        branch_b: str
        delta: float
        resolved: bool = False

else:

    @dataclass(slots=True)
    class RetroRun:  # type: ignore[override]
        id: int | None
        from_commit: str
        to_commit: str
        reward_delta: float
        entropy_delta: float
        verified: bool


    @dataclass(slots=True)
    class RetroProof:  # type: ignore[override]
        id: int | None
        run_id: int
        hash: str
        valid: bool
        created_at: datetime


    @dataclass(slots=True)
    class MultiverseState:  # type: ignore[override]
        id: int | None
        branches_json: Dict[str, Any]
        coherence_score: float
        at: datetime


    @dataclass(slots=True)
    class DivergenceEvent:  # type: ignore[override]
        id: int | None
        branch_a: str
        branch_b: str
        delta: float
        resolved: bool


__all__ = [
    "RetroRun",
    "RetroProof",
    "MultiverseState",
    "DivergenceEvent",
    "SQLMODEL_AVAILABLE",
]
