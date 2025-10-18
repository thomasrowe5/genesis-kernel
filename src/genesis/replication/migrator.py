"""Replica migration orchestration."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Session = Any  # type: ignore[assignment]

from ..collective.models import Replica
from .verifier import ReplicaVerifier


@dataclass(slots=True)
class ReplicaDeployment:
    record: Replica
    target: str
    approved: bool


class ReplicaMigrator:
    """Coordinates replica bootstrapping and registry updates."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        verifier: ReplicaVerifier | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._verifier = verifier or ReplicaVerifier()

    async def deploy(
        self,
        *,
        artifact,
        origin_node: str,
        target: str,
    ) -> ReplicaDeployment:
        if not await self._verifier.verify(artifact):
            raise ValueError("Replica verification failed")

        def _persist() -> Replica:
            with self._session_factory() as session:
                record = Replica(
                    origin_node=origin_node,
                    hash_hex=artifact.hash_hex,
                    verified=True,
                    deployed_at=datetime.utcnow(),
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record

        record = await asyncio.to_thread(_persist)
        approved = record.verified
        return ReplicaDeployment(record=record, target=target, approved=approved)


__all__ = ["ReplicaMigrator", "ReplicaDeployment"]
