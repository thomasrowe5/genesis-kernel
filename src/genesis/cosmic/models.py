"""SQLModel-compatible data models for cosmic coordination."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:  # pragma: no cover - optional dependency
    from sqlmodel import Field, SQLModel
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    SQLModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]


SQLMODEL_AVAILABLE = Field is not None


if SQLMODEL_AVAILABLE:

    class Seed(SQLModel, table=True):
        id: str = Field(default=None, primary_key=True)
        origin: str
        target: str
        hash_hex: str
        launched_at: datetime
        status: str

    class Branch(SQLModel, table=True):
        id: str = Field(default=None, primary_key=True)
        ancestor_id: Optional[str]
        mutation_vector: str
        divergence_score: float

    class VaultRecord(SQLModel, table=True):
        id: str = Field(default=None, primary_key=True)
        hash_hex: str
        payload_ref: str
        redundancy_level: int

    class ChronicleEvent(SQLModel, table=True):
        id: str = Field(default=None, primary_key=True)
        branch_id: Optional[str]
        type: str
        at: datetime
        data_json: str

else:

    @dataclass(slots=True)
    class Seed:  # type: ignore[override]
        id: str
        origin: str
        target: str
        hash_hex: str
        launched_at: datetime
        status: str

    @dataclass(slots=True)
    class Branch:  # type: ignore[override]
        id: str
        ancestor_id: Optional[str]
        mutation_vector: str
        divergence_score: float

    @dataclass(slots=True)
    class VaultRecord:  # type: ignore[override]
        id: str
        hash_hex: str
        payload_ref: str
        redundancy_level: int

    @dataclass(slots=True)
    class ChronicleEvent:  # type: ignore[override]
        id: str
        branch_id: Optional[str]
        type: str
        at: datetime
        data_json: str


__all__ = ["Seed", "Branch", "VaultRecord", "ChronicleEvent", "SQLMODEL_AVAILABLE"]
