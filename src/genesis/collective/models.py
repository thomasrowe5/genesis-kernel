"""Data models backing the collective coordination subsystems."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional SQLModel dependency path
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
        default_factory: Any | None = None,
        sa_column: Any | None = None,
    ) -> Any:
        if default_factory is not None:
            return field(default_factory=default_factory)
        return field(default=default)


if SQLMODEL_AVAILABLE:

    class PeerNode(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        host: str = Field(index=True)
        pubkey: str
        last_seen_at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(
                DateTime(timezone=False),
                default=datetime.utcnow,
                nullable=False,
            ),
        )
        stake: float = Field(default=0.0)
        status: str = Field(default="unknown")

    class Proposal(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        type: str = Field(index=True)
        payload_json: Dict[str, Any] = Field(
            default_factory=dict,
            sa_column=Column(JSON, nullable=False, default=dict),
        )
        proposer: str = Field(index=True)
        state: str = Field(default="pending")
        votes_for: int = Field(default=0)
        votes_against: int = Field(default=0)
        committed_at: Optional[datetime] = Field(
            default=None,
            sa_column=Column(DateTime(timezone=False), nullable=True),
        )

    class EconomyTx(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        from_id: Optional[int] = Field(default=None, index=True)
        to_id: Optional[int] = Field(default=None, index=True)
        amount: float
        reason: str = Field(index=True)
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class EthicsEvent(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        principle: str = Field(index=True)
        level: str
        description: str
        at: datetime = Field(
            default_factory=datetime.utcnow,
            sa_column=Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False),
        )

    class Replica(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        origin_node: str = Field(index=True)
        hash_hex: str = Field(index=True)
        verified: bool = Field(default=False, index=True)
        deployed_at: Optional[datetime] = Field(
            default=None,
            sa_column=Column(DateTime(timezone=False), nullable=True),
        )

else:

    @dataclass(slots=True)
    class PeerNode:
        id: Optional[int]
        host: str
        pubkey: str
        last_seen_at: datetime = field(default_factory=datetime.utcnow)
        stake: float = 0.0
        status: str = "unknown"

    @dataclass(slots=True)
    class Proposal:
        id: Optional[int]
        type: str
        payload_json: Dict[str, Any] = field(default_factory=dict)
        proposer: str = ""
        state: str = "pending"
        votes_for: int = 0
        votes_against: int = 0
        committed_at: Optional[datetime] = None

    @dataclass(slots=True)
    class EconomyTx:
        id: Optional[int]
        from_id: Optional[int]
        to_id: Optional[int]
        amount: float
        reason: str
        at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class EthicsEvent:
        id: Optional[int]
        principle: str
        level: str
        description: str
        at: datetime = field(default_factory=datetime.utcnow)

    @dataclass(slots=True)
    class Replica:
        id: Optional[int]
        origin_node: str
        hash_hex: str
        verified: bool = False
        deployed_at: Optional[datetime] = None


__all__ = [
    "EconomyTx",
    "EthicsEvent",
    "PeerNode",
    "Proposal",
    "Replica",
    "SQLMODEL_AVAILABLE",
]
