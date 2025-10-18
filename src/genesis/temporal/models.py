"""Data models supporting the temporal recursion engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency path
    from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
    from sqlmodel import Field, SQLModel

    SQLMODEL_AVAILABLE = True
except Exception:  # pragma: no cover - SQLModel unavailable
    Column = DateTime = Float = Integer = JSON = String = None  # type: ignore[assignment]
    SQLModel = object  # type: ignore[assignment]
    SQLMODEL_AVAILABLE = False

    def Field(  # type: ignore[misc]
        default: Any | None = None,
        *,
        primary_key: bool | None = None,
        sa_column: Any | None = None,
        default_factory: Any | None = None,
        index: bool | None = None,
    ) -> Any:
        if default_factory is not None:
            return field(default_factory=default_factory)
        return field(default=default)


VectorClock = Dict[str, int]
StatePayload = Dict[str, Any]


if SQLMODEL_AVAILABLE:

    class TimelineCommit(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        timestamp: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
            index=True,
        )
        vector_clock: VectorClock = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        hash: str = Field(default="", sa_column=Column(String(length=128), nullable=False, index=True))
        state_json: StatePayload = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )

    class RecursionRun(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        from_commit: Optional[int] = Field(default=None, foreign_key="timelinecommit.id", index=True)
        to_commit: Optional[int] = Field(default=None, foreign_key="timelinecommit.id")
        duration: float = Field(
            default=0.0,
            sa_column=Column(Float, default=0.0, nullable=False),
        )
        result_json: StatePayload = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        status: str = Field(default="pending", sa_column=Column(String(length=32), nullable=False, index=True))
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class BranchRecord(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        parent_id: Optional[int] = Field(default=None, foreign_key="timelinecommit.id", index=True)
        divergence_score: float = Field(
            default=0.0,
            sa_column=Column(Float, default=0.0, nullable=False),
        )
        merged: bool = Field(default=False, index=True)
        name: str = Field(default="", sa_column=Column(String(length=128), nullable=False, index=True))
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class ContinuityMetric(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        key: str = Field(default="", sa_column=Column(String(length=128), nullable=False, index=True))
        value: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        delta: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class TemporalAlert(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        type: str = Field(default="", sa_column=Column(String(length=64), nullable=False, index=True))
        severity: str = Field(default="info", sa_column=Column(String(length=16), nullable=False))
        description: str = Field(default="", sa_column=Column(String(length=512), nullable=False))
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

else:

    @dataclass(slots=True)
    class TimelineCommit:
        id: Optional[int] = None
        timestamp: datetime = field(default_factory=datetime.utcnow)
        vector_clock: VectorClock = field(default_factory=dict)
        hash: str = ""
        state_json: StatePayload = field(default_factory=dict)

    @dataclass(slots=True)
    class RecursionRun:
        id: Optional[int] = None
        from_commit: Optional[int] = None
        to_commit: Optional[int] = None
        duration: float = 0.0
        result_json: StatePayload = field(default_factory=dict)
        status: str = "pending"
        created_at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class BranchRecord:
        id: Optional[int] = None
        parent_id: Optional[int] = None
        divergence_score: float = 0.0
        merged: bool = False
        name: str = ""
        created_at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class ContinuityMetric:
        id: Optional[int] = None
        key: str = ""
        value: float = 0.0
        delta: float = 0.0
        at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class TemporalAlert:
        id: Optional[int] = None
        type: str = ""
        severity: str = "info"
        description: str = ""
        at: datetime = field(default_factory=datetime.utcnow)


__all__ = [
    "SQLMODEL_AVAILABLE",
    "TimelineCommit",
    "RecursionRun",
    "BranchRecord",
    "ContinuityMetric",
    "TemporalAlert",
    "VectorClock",
    "StatePayload",
]
