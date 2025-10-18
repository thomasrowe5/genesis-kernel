"""Data models backing the reflexive intelligence layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency path
    from sqlalchemy import Column, DateTime, Float, Integer, JSON
    from sqlmodel import Field, SQLModel

    SQLMODEL_AVAILABLE = True
except Exception:  # pragma: no cover - SQLModel unavailable
    Column = DateTime = Float = Integer = JSON = None  # type: ignore[assignment]
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


if SQLMODEL_AVAILABLE:

    class TwinSnapshot(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )
        topology_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        metrics_json: Dict[str, float] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        config_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )

    class SimulationRun(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        change_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        predicted_delta: Dict[str, float] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        executed: bool = Field(default=False)
        outcome_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        confidence: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class ReflectionLog(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        reason: str = Field(default="", index=True)
        prediction: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        result: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        delta: Dict[str, float] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        confidence: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class UncertaintyMetric(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        key: str = Field(default="", index=True)
        mean: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        stddev: float = Field(default=0.0, sa_column=Column(Float, default=0.0, nullable=False))
        last_updated: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

else:

    @dataclass(slots=True)
    class TwinSnapshot:
        id: Optional[int] = None
        at: datetime = field(default_factory=datetime.utcnow)
        topology_json: Dict[str, Any] = field(default_factory=dict)
        metrics_json: Dict[str, float] = field(default_factory=dict)
        config_json: Dict[str, Any] = field(default_factory=dict)

    @dataclass(slots=True)
    class SimulationRun:
        id: Optional[int] = None
        change_json: Dict[str, Any] = field(default_factory=dict)
        predicted_delta: Dict[str, float] = field(default_factory=dict)
        executed: bool = False
        outcome_json: Dict[str, Any] = field(default_factory=dict)
        confidence: float = 0.0
        created_at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class ReflectionLog:
        id: Optional[int] = None
        reason: str = ""
        prediction: Dict[str, Any] = field(default_factory=dict)
        result: Dict[str, Any] = field(default_factory=dict)
        delta: Dict[str, float] = field(default_factory=dict)
        confidence: float = 0.0
        created_at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class UncertaintyMetric:
        id: Optional[int] = None
        key: str = ""
        mean: float = 0.0
        stddev: float = 0.0
        last_updated: datetime = field(default_factory=datetime.utcnow)


__all__ = [
    "SQLMODEL_AVAILABLE",
    "TwinSnapshot",
    "SimulationRun",
    "ReflectionLog",
    "UncertaintyMetric",
]
