"""Continuous ethics monitoring for the Genesis federation."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, List

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Session = Any  # type: ignore[assignment]

from genesis.metrics import genesis_ethics_violations_total

from .principles import DEFAULT_PRINCIPLES, EthicsPrinciple
from ..collective.models import EthicsEvent


@dataclass(slots=True)
class EthicsFinding:
    """Violation emitted by the auditor."""

    principle: str
    level: str
    description: str
    severity: float
    at: datetime


class EthicsAuditor:
    """Applies ethics policies against provenance events."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        *,
        principles: Iterable[EthicsPrinciple] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._principles = {principle.name: principle for principle in principles or DEFAULT_PRINCIPLES}

    async def evaluate(self, *, principle: str, severity: float, description: str) -> List[EthicsFinding]:
        """Evaluate an event and persist violations."""

        def _eval() -> List[EthicsFinding]:
            policy = self._principles.get(principle)
            if policy is None:
                return []
            if severity < policy.severity_threshold:
                return []
            finding = EthicsFinding(
                principle=principle,
                level="violation",
                description=description,
                severity=severity,
                at=datetime.utcnow(),
            )
            with self._session_factory() as session:
                event = EthicsEvent(
                    principle=finding.principle,
                    level=finding.level,
                    description=finding.description,
                    at=finding.at,
                )
                session.add(event)
                session.commit()
                genesis_ethics_violations_total.labels(principle=principle).inc()
            return [finding]

        return await asyncio.to_thread(_eval)

    def principles(self) -> List[EthicsPrinciple]:
        return list(self._principles.values())


__all__ = ["EthicsAuditor", "EthicsFinding"]
