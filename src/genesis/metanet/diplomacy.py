"""Diplomatic coordination agents orchestrating treaties and sanctions."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Mapping

from genesis.global_.intelligence import GlobalIntelligence
from genesis.global_.adaptation import GlobalAdaptationEngine
from genesis.law.charter import GlobalCharter
from genesis.law.court import CourtCase, CourtVerdict, PlanetaryCourt
from genesis.law.sanctions import SanctionsEngine
from genesis.metanet.exchange import ExchangeLedger, ExchangeReceipt
from genesis.metanet.interconnect import MetaNetInterconnect
from genesis.metanet.treaty import GenesisTreaty, TreatyOrchestrator


@dataclass(slots=True)
class DiplomaticOutcome:
    treaty: GenesisTreaty
    receipts: tuple[ExchangeReceipt, ...]


class DiplomaticAgent:
    """High-level agent responsible for inter-federation diplomacy."""

    def __init__(
        self,
        interconnect: MetaNetInterconnect,
        treaties: TreatyOrchestrator,
        ledger: ExchangeLedger,
        charter: GlobalCharter,
        court: PlanetaryCourt,
        sanctions: SanctionsEngine,
        intelligence: GlobalIntelligence,
        adaptation: GlobalAdaptationEngine,
    ) -> None:
        self._interconnect = interconnect
        self._treaties = treaties
        self._ledger = ledger
        self._charter = charter
        self._court = court
        self._sanctions = sanctions
        self._intelligence = intelligence
        self._adaptation = adaptation

    async def negotiate_treaty(
        self,
        *,
        parties: Iterable[str],
        payload: Mapping[str, object],
        public_keys: Mapping[str, str],
    ) -> GenesisTreaty:
        treaty = self._treaties.propose(tuple(parties), payload)
        for party in treaty.all_parties():
            key = public_keys[party]
            signature = self._treaties.sign(treaty.treaty_id, party, key)
        await asyncio.gather(
            *[
                self._async_vote(treaty.treaty_id, party, True, public_keys[party])
                for party in treaty.all_parties()
            ]
        )
        return self._treaties.treaty(treaty.treaty_id)

    async def _async_vote(self, treaty_id: str, federation_id: str, approve: bool, key: str) -> None:
        await asyncio.sleep(0)
        self._treaties.vote(treaty_id, federation_id, approve, key)

    async def execute_exchange(
        self,
        trades: Iterable[tuple[str, str, float]],
        asset_type: str = "credit",
    ) -> tuple[ExchangeReceipt, ...]:
        receipts = []
        for origin, partner, amount in trades:
            receipts.append(
                self._ledger.execute_atomic_swap(
                    from_federation=origin,
                    to_federation=partner,
                    amount=amount,
                    asset_type=asset_type,
                )
            )
            await asyncio.sleep(0)
        return tuple(receipts)

    async def adapt_global_state(self, goal: str) -> Mapping[str, float]:
        plan = await self._adaptation.optimise(goal)
        return plan

    async def resolve_dispute(
        self,
        case: CourtCase,
        *,
        sanction_amount: float = 0.0,
    ) -> CourtVerdict:
        verdict = await self._court.adjudicate(case)
        if verdict.enforceable and sanction_amount:
            self._sanctions.apply_credit_penalty(case.defendant, sanction_amount, ledger=self._ledger)
        return verdict


__all__ = ["DiplomaticAgent", "DiplomaticOutcome"]
