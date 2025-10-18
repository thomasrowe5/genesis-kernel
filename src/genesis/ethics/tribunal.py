"""Distributed arbitration for ethics violations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from genesis.collective.consensus import ConsensusEngine, ProposalDecision

from .auditor import EthicsFinding


@dataclass(slots=True)
class TribunalVerdict:
    decision: ProposalDecision
    proposal_id: int


class EthicsTribunal:
    """Leverages the federation consensus engine to adjudicate violations."""

    def __init__(self, consensus: ConsensusEngine) -> None:
        self._consensus = consensus

    async def adjudicate(
        self,
        finding: EthicsFinding,
        *,
        votes: Mapping[str, bool],
    ) -> TribunalVerdict:
        payload: Dict[str, Any] = {
            "principle": finding.principle,
            "severity": finding.severity,
            "description": finding.description,
        }
        proposal = await self._consensus.submit_proposal(
            proposal_type="ethics_violation",
            payload=payload,
            proposer="ethics-auditor",
        )
        decision = ProposalDecision.PENDING
        for voter, approve in votes.items():
            result = await self._consensus.cast_vote(int(proposal.id or 0), approve=approve, voter=voter)
            decision = result.decision
        return TribunalVerdict(decision=decision, proposal_id=int(proposal.id or 0))


__all__ = ["EthicsTribunal", "TribunalVerdict"]
