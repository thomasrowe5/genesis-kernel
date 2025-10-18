"""Singleton runtime objects wiring planetary coordination subsystems."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from genesis.global_.adaptation import GlobalAdaptationEngine
from genesis.global_.intelligence import GlobalIntelligence
from genesis.law.charter import CharterArticle, GlobalCharter
from genesis.law.court import PlanetaryCourt
from genesis.law.sanctions import SanctionsEngine
from genesis.metanet.diplomacy import DiplomaticAgent
from genesis.metanet.exchange import ExchangeLedger
from genesis.metanet.interconnect import FederationProfile, MetaNetInterconnect
from genesis.metanet.treaty import TreatyOrchestrator


@dataclass(slots=True)
class MetaNetRuntime:
    interconnect: MetaNetInterconnect = field(default_factory=MetaNetInterconnect)
    treaties: TreatyOrchestrator = field(default_factory=TreatyOrchestrator)
    ledger: ExchangeLedger = field(default_factory=ExchangeLedger)
    intelligence: GlobalIntelligence = field(default_factory=GlobalIntelligence)
    adaptation: GlobalAdaptationEngine = field(default_factory=GlobalAdaptationEngine)
    charter: GlobalCharter = field(default_factory=GlobalCharter)
    court: PlanetaryCourt = field(default_factory=lambda: PlanetaryCourt(jurors=["A", "B", "C"]))
    sanctions: SanctionsEngine = field(default_factory=SanctionsEngine)
    diplomat: DiplomaticAgent | None = None
    federation_keys: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.diplomat is None:
            self.diplomat = DiplomaticAgent(
                self.interconnect,
                self.treaties,
                self.ledger,
                self.charter,
                self.court,
                self.sanctions,
                self.intelligence,
                self.adaptation,
            )
        self._seed_charter()

    def _seed_charter(self) -> None:
        if not list(self.charter.list_articles(include_inactive=True)):
            self.charter.add_article(
                CharterArticle(
                    identifier="art-1",
                    title="Peaceful Coexistence",
                    text="Federations shall resolve disputes through the planetary court.",
                )
            )

    async def register_federation(self, profile: FederationProfile) -> None:
        await self.interconnect.register_federation(profile)
        if profile.federation_id not in self.federation_keys:
            public_key = self.treaties.register_key(profile.federation_id)
            self.federation_keys[profile.federation_id] = public_key

    def public_key(self, federation_id: str) -> str:
        return self.federation_keys[federation_id]


__runtime: MetaNetRuntime | None = None


def get_runtime() -> MetaNetRuntime:
    global __runtime
    if __runtime is None:
        __runtime = MetaNetRuntime()
    return __runtime


__all__ = ["MetaNetRuntime", "get_runtime"]
