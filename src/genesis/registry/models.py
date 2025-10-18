"""Data models for the module registry with optional SQLModel support."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency path
    from sqlalchemy import Column, DateTime, JSON
    from sqlmodel import Field, SQLModel

    SQLMODEL_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Column = DateTime = JSON = None  # type: ignore[assignment]
    SQLModel = object  # type: ignore[assignment]
    SQLMODEL_AVAILABLE = False

    def Field(  # type: ignore[misc]
        default: Any | None = None,
        *,
        primary_key: bool | None = None,
        index: bool | None = None,
        default_factory: Optional[Any] = None,
        sa_column: Any | None = None,
    ) -> Any:
        if default_factory is not None:
            return field(default_factory=default_factory)
        return field(default=default)


if SQLMODEL_AVAILABLE:

    class ModuleVersion(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str = Field(index=True)
        version: str
        path: str
        params_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        score: float = Field(default=0.0, index=True)
        reward_ma: float = Field(default=0.0)
        p95_ms: float = Field(default=0.0)
        error_rate: float = Field(default=0.0)
        active: bool = Field(default=False, index=True)
        canary: bool = Field(default=False, index=True)
        traffic_share: float = Field(default=0.0)
        metadata_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )
        updated_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(
                DateTime(timezone=False),
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
                nullable=False,
            ),
        )


    class Event(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        event_type: str = Field(index=True)
        module_name: str
        payload: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class OrchestrationEvent(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        module: str = Field(index=True)
        version: str
        type: str = Field(index=True)
        data_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

else:

    @dataclass(slots=True)
    class ModuleVersion:
        id: Optional[int]
        name: str
        version: str
        path: str
        params_json: Dict[str, Any] = field(default_factory=dict)
        score: float = 0.0
        reward_ma: float = 0.0
        p95_ms: float = 0.0
        error_rate: float = 0.0
        active: bool = False
        canary: bool = False
        traffic_share: float = 0.0
        metadata_json: Dict[str, Any] = field(default_factory=dict)
        created_at: datetime = field(default_factory=datetime.utcnow)
        updated_at: datetime = field(default_factory=datetime.utcnow)


    @dataclass(slots=True)
    class Event:
        id: Optional[int]
        event_type: str
        module_name: str
        payload: Dict[str, Any] = field(default_factory=dict)
        created_at: datetime = field(default_factory=datetime.utcnow)


    @dataclass(slots=True)
    class OrchestrationEvent:
        id: Optional[int]
        module: str
        version: str
        type: str
        data_json: Dict[str, Any] = field(default_factory=dict)
        at: datetime = field(default_factory=datetime.utcnow)


__all__ = ["ModuleVersion", "Event", "OrchestrationEvent", "SQLMODEL_AVAILABLE"]
