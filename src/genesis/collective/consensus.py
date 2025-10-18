"""Simplified PBFT-style consensus orchestrator used in tests."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Iterable

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, select
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Session = Any  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

from genesis.metrics import genesis_consensus_rounds_total

from .models import Proposal


class ProposalDecision(str, Enum):
    """Lifecycle state recorded for consensus proposals."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True)
class ProposalResult:
    """Return value emitted after a consensus round."""

    proposal: Proposal
    decision: ProposalDecision
    committed_at: datetime | None


class ConsensusEngine:
    """Very small PBFT-inspired commit log for the federation layer."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        *,
        quorum_size: int = 1,
    ) -> None:
        self._session_factory = session_factory
        self.quorum_size = max(1, quorum_size)

    async def submit_proposal(
        self,
        *,
        proposal_type: str,
        payload: dict[str, Any],
        proposer: str,
    ) -> Proposal:
        """Persist a new proposal and return the stored record."""

        def _op() -> Proposal:
            with self._session_factory() as session:
                proposal = Proposal(
                    type=proposal_type,
                    payload_json=payload,
                    proposer=proposer,
                    state=ProposalDecision.PENDING.value,
                )
                session.add(proposal)
                session.commit()
                session.refresh(proposal)
                return proposal

        return await asyncio.to_thread(_op)

    async def cast_vote(
        self,
        proposal_id: int,
        *,
        approve: bool,
        voter: str,
    ) -> ProposalResult:
        """Record a vote for a proposal and finalise if quorum reached."""

        def _vote() -> ProposalResult:
            with self._session_factory() as session:
                proposal = session.get(Proposal, proposal_id)
                if proposal is None:
                    raise ValueError(f"Unknown proposal {proposal_id}")

                # PBFT-like behaviour: record votes and decide when quorum reached.
                if approve:
                    proposal.votes_for += 1
                else:
                    proposal.votes_against += 1

                decision = ProposalDecision.PENDING
                committed_at: datetime | None = proposal.committed_at

                if proposal.votes_for >= self.quorum_size:
                    proposal.state = ProposalDecision.APPROVED.value
                    committed_at = datetime.utcnow()
                    proposal.committed_at = committed_at
                    decision = ProposalDecision.APPROVED
                elif proposal.votes_against >= self.quorum_size:
                    proposal.state = ProposalDecision.REJECTED.value
                    committed_at = datetime.utcnow()
                    proposal.committed_at = committed_at
                    decision = ProposalDecision.REJECTED

                session.add(proposal)
                session.commit()
                session.refresh(proposal)

                if decision is ProposalDecision.PENDING:
                    label = "pending"
                else:
                    label = decision.value
                genesis_consensus_rounds_total.labels(state=label).inc()

                return ProposalResult(
                    proposal=proposal,
                    decision=decision,
                    committed_at=committed_at,
                )

        return await asyncio.to_thread(_vote)

    async def pending(self) -> list[Proposal]:
        """Return proposals awaiting quorum."""

        def _pending() -> Iterable[Proposal]:
            with self._session_factory() as session:
                if select is None:
                    return []
                statement = select(Proposal).where(Proposal.state == ProposalDecision.PENDING.value)
                return list(session.exec(statement))

        result = await asyncio.to_thread(_pending)
        return list(result)


__all__ = ["ConsensusEngine", "ProposalDecision", "ProposalResult"]
