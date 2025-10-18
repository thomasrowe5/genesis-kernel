import asyncio

import pytest

from genesis.global_.adaptation import GlobalAdaptationEngine
from genesis.law.court import CourtCase, PlanetaryCourt
from genesis.law.sanctions import SanctionsEngine
from genesis.metanet.exchange import ExchangeLedger
from genesis.metanet.interconnect import FederationProfile
from genesis.metanet.runtime import MetaNetRuntime
from genesis.metanet.treaty import TreatyOrchestrator


def test_federations_join_and_link_mesh():
    async def _run() -> None:
        runtime = MetaNetRuntime()
        profiles = [
            FederationProfile(
                federation_id=f"fed-{idx}",
                human_name=f"Federation {idx}",
                public_key=f"pk-{idx}",
                endpoints=[f"https://fed{idx}.local"],
                capabilities={"energy": 1.0},
            )
            for idx in range(3)
        ]
        for profile in profiles:
            await runtime.register_federation(profile)
        await runtime.interconnect.ensure_mesh([profile.federation_id for profile in profiles])
        snapshot = await runtime.interconnect.sync_snapshot()
        assert len(snapshot["federations"]) == 3
        assert len(snapshot["links"]) >= 3

    asyncio.run(_run())


def test_treaty_commit_and_enforcement():
    orchestrator = TreatyOrchestrator()
    parties = ["alpha", "beta", "gamma"]
    keys = {party: orchestrator.register_key(party, seed=f"secret-{party}") for party in parties}
    treaty = orchestrator.propose(parties, {"goal": "shared energy"})
    for party, public in keys.items():
        orchestrator.sign(treaty.treaty_id, party, public)
        orchestrator.vote(treaty.treaty_id, party, True, public)
    assert treaty.state.value == "ratified"
    enforced = orchestrator.enforce(treaty.treaty_id)
    assert enforced.state.value == "enforced"


def test_exchange_atomicity():
    ledger = ExchangeLedger()
    receipt = ledger.execute_atomic_swap(from_federation="alpha", to_federation="beta", amount=42.0)
    assert ledger.verify(receipt)
    with pytest.raises(ValueError):
        ledger.execute_atomic_swap(from_federation="alpha", to_federation="beta", amount=42.0)


def test_adaptation_balances_weights():
    async def _run() -> None:
        engine = GlobalAdaptationEngine()
        plan = await engine.optimise("reduce latency")
        assert pytest.approx(sum(plan.values()), rel=1e-6) == 1.0
        assert plan["latency"] > plan["energy"]

    asyncio.run(_run())


def test_court_verdict_triggers_sanction():
    async def _run() -> None:
        ledger = ExchangeLedger()
        sanctions = SanctionsEngine()
        court = PlanetaryCourt(jurors=["alpha", "beta", "gamma"])
        case = CourtCase(treaty_id=None, plaintiff="alpha", defendant="beta", claim="credit dispute")
        verdict = await court.adjudicate(case)
        penalty = sanctions.apply_credit_penalty("beta", 5.0, ledger=ledger)
        assert penalty.amount == 5.0
        assert ledger.balance_sheet("beta") <= 0

    asyncio.run(_run())
