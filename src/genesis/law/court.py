"""Distributed planetary court implementing deterministic PBFT consensus."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping, Optional

from genesis.metrics import genesis_law_cases_total
from genesis.metanet.models import CourtCase as CourtCaseModel


@dataclass(slots=True)
class CourtCase:
    treaty_id: Optional[str]
    plaintiff: str
    defendant: str
    claim: str


@dataclass(slots=True)
class CourtVerdict:
    case: CourtCase
    verdict: str
    enforceable: bool
    decided_at: datetime


class PBFTConsensus:
    """Deterministic stand-in for PBFT style consensus."""

    def __init__(self, replicas: Iterable[str]) -> None:
        self.replicas = tuple(replicas)

    async def decide(self, payload: Mapping[str, str]) -> str:
        await asyncio.sleep(0)
        digest = sum(ord(ch) for ch in "|".join(payload.values()))
        return "approve" if digest % 2 == 0 else "reject"


class PlanetaryCourt:
    """Adjudicates disputes using deterministic consensus among federations."""

    def __init__(self, jurors: Iterable[str]) -> None:
        self._jurors = tuple(jurors)
        self._consensus = PBFTConsensus(self._jurors)
        self._docket: MutableMapping[str, CourtCase] = {}

    async def adjudicate(self, case: CourtCase) -> CourtVerdict:
        case_id = self._case_id(case)
        self._docket[case_id] = case
        verdict_value = await self._consensus.decide({
            "plaintiff": case.plaintiff,
            "defendant": case.defendant,
            "claim": case.claim,
        })
        enforceable = verdict_value == "approve"
        verdict = CourtVerdict(case=case, verdict=verdict_value, enforceable=enforceable, decided_at=datetime.utcnow())
        genesis_law_cases_total.inc()
        return verdict

    def _case_id(self, case: CourtCase) -> str:
        treaty_id = case.treaty_id or "none"
        return f"case::{treaty_id}::{case.plaintiff}::{case.defendant}"

    def docket(self) -> Mapping[str, CourtCase]:
        return dict(self._docket)

    def to_model(self, case: CourtCase, verdict: CourtVerdict) -> CourtCaseModel:
        return CourtCaseModel(
            id=None,
            treaty_id=None,
            plaintiff=case.plaintiff,
            defendant=case.defendant,
            verdict=verdict.verdict,
        )


__all__ = ["PlanetaryCourt", "CourtCase", "CourtVerdict"]
