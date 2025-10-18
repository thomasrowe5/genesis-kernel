"""Optional SQLModel data structures backing the planetary meta-network."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency path
    from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
    from sqlmodel import Field, SQLModel

    SQLMODEL_AVAILABLE = True
except Exception:  # pragma: no cover - SQLModel not installed in runtime
    Column = DateTime = Float = Integer = JSON = String = None  # type: ignore[assignment]
    SQLModel = object  # type: ignore[assignment]
    SQLMODEL_AVAILABLE = False

    def Field(  # type: ignore[misc]
        default: Any | None = None,
        *,
        primary_key: bool | None = None,
        index: bool | None = None,
        sa_column: Any | None = None,
        default_factory: Any | None = None,
    ) -> Any:
        if default_factory is not None:
            return field(default_factory=default_factory)
        return field(default=default)


if SQLMODEL_AVAILABLE:

    class FederationLink(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        origin_id: str = Field(index=True)
        partner_id: str = Field(index=True)
        status: str = Field(default="pending", index=True)
        latency_ms: float = Field(default=0.0)
        last_sync: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class Treaty(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        parties_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        payload_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        state: str = Field(default="proposed", index=True)
        created_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )
        ratified_at: Optional[datetime] = Field(
            default=None,
            sa_column=Column(DateTime(timezone=False), nullable=True),
        )

    class ExchangeTx(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        from_fed: str = Field(index=True)
        to_fed: str = Field(index=True)
        amount: float = Field(default=0.0)
        asset_type: str = Field(default="credit", index=True)
        proof_hash: str = Field(default="", index=True)
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class GlobalMetric(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        key: str = Field(index=True)
        value: float = Field(default=0.0)
        unit: str = Field(default="")
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class LawArticle(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        title: str = Field(index=True)
        text: str = Field(default="")
        version: int = Field(default=1, index=True)
        active: bool = Field(default=True, index=True)

    class CourtCase(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        treaty_id: Optional[int] = Field(default=None, index=True)
        plaintiff: str = Field(index=True)
        defendant: str = Field(index=True)
        verdict: str = Field(default="pending")
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

else:

    @dataclass(slots=True)
    class FederationLink:
        id: Optional[int]
        origin_id: str
        partner_id: str
        status: str = "pending"
        latency_ms: float = 0.0
        last_sync: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class Treaty:
        id: Optional[int]
        parties_json: Dict[str, Any] = field(default_factory=dict)
        payload_json: Dict[str, Any] = field(default_factory=dict)
        state: str = "proposed"
        created_at: datetime = field(default_factory=datetime.utcnow)
        ratified_at: Optional[datetime] = None

    @dataclass(slots=True)
    class ExchangeTx:
        id: Optional[int]
        from_fed: str
        to_fed: str
        amount: float
        asset_type: str = "credit"
        proof_hash: str = ""
        at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class GlobalMetric:
        id: Optional[int]
        key: str
        value: float
        unit: str
        at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class LawArticle:
        id: Optional[int]
        title: str
        text: str
        version: int = 1
        active: bool = True

    @dataclass(slots=True)
    class CourtCase:
        id: Optional[int]
        treaty_id: Optional[int]
        plaintiff: str
        defendant: str
        verdict: str
        at: datetime = field(default_factory=datetime.utcnow)


__all__ = [
    "FederationLink",
    "Treaty",
    "ExchangeTx",
    "GlobalMetric",
    "LawArticle",
    "CourtCase",
    "SQLMODEL_AVAILABLE",
]
