"""Integration tests for the Genesis cosmic expansion stack."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from genesis.archivum.retrieval import VaultRetrieval
from genesis.archivum.vault import VaultStore
from genesis.cosmic.consensus_ld import LongDelayConsensus
from genesis.cosmic.relativity import CausalEvent, causal_order, to_proper_time
from genesis.cosmic.service import CosmicNetworkService
from genesis.evolution.convergence import ConvergenceEngine
from genesis.evolution.mutation import MutationOperator
from genesis.evolution.speciation import SpeciationEngine


def test_seed_deploy_and_resync(tmp_path) -> None:
    service = CosmicNetworkService(origin="Sol", prime_ethic=["do-no-harm"], storage_dir=tmp_path)

    async def _scenario() -> None:
        package = await service.deploy_seed("sector-alpha", {"knowledge": ["stellar-cartography"]})
        assert package.target == "sector-alpha"
        await service.propagate_state(package.seed_id, {"status": "stable"})
        remote = LongDelayConsensus("remote")
        for seed_id, entry in service.consensus.export_state().entries.items():
            await remote.update(seed_id, entry.payload)
        merkle = await service.cosmic_sync(remote)
        assert len(merkle) == 64
        status = service.seed_status(package.seed_id)
        assert status is not None and status.hash_hex == package.hash_hex
        assert service.chronicle_events()

    asyncio.run(_scenario())


def test_long_delay_consensus_stability() -> None:
    async def _scenario() -> None:
        local = LongDelayConsensus("local")
        remote = LongDelayConsensus("remote")
        await local.update("seed-x", {"status": "launched"})
        remote.merge(local)
        await remote.update("seed-x", {"status": "settled"})
        local.merge(remote)
        state = local.export_state()
        assert state.entries["seed-x"].version == 2

    asyncio.run(_scenario())


def test_speciation_and_convergence() -> None:
    mutation = MutationOperator(rate=1.0, scale=0.05, seed=42)
    speciation = SpeciationEngine(mutation, delta=0.1)
    branches = speciation.speciate("prime", [1.0, 1.0, 1.0], 2)
    fitness = {branch.identifier: 1.0 + index for index, branch in enumerate(branches)}
    convergence = ConvergenceEngine()
    merged = convergence.converge(branches, fitness, ethics_weight=0.5)
    assert len(merged) == 3
    for branch in branches:
        deviation = sum(abs(p - m) for p, m in zip(branch.parameters, merged))
        assert deviation < 0.5


def test_vault_snapshot_and_retrieval(tmp_path) -> None:
    async def _scenario() -> None:
        vault = VaultStore(tmp_path)
        record = await vault.snapshot("galactic-archive", b"payload", redundancy_level=3)
        retrieval = VaultRetrieval(vault)
        restored = await retrieval.retrieve(record.id)
        assert restored == b"payload"

    asyncio.run(_scenario())


def test_chronicle_relativistic_ordering() -> None:
    reference = datetime(3123, 1, 1, tzinfo=timezone.utc)
    events = [
        CausalEvent("fast", reference + timedelta(hours=1), 0.8),
        CausalEvent("slow", reference + timedelta(hours=1), 0.0),
        CausalEvent("late", reference + timedelta(hours=2), 0.2),
    ]
    order = causal_order(events)
    assert order == ["fast", "slow", "late"]
    proper_fast = to_proper_time(events[0].timestamp, reference, events[0].velocity_fraction)
    proper_slow = to_proper_time(events[1].timestamp, reference, events[1].velocity_fraction)
    assert proper_fast < proper_slow
