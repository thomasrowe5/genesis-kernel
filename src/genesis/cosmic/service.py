"""High-level orchestration service combining cosmic coordination primitives."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from genesis.archivum.vault import VaultStore
from genesis.archivum.chronicle import ChronicleLedger, ChronicleRecord
from genesis.archivum.retrieval import VaultRetrieval
from genesis.cosmic.consensus_ld import LongDelayConsensus
from genesis.cosmic.propagation import PropagationNetwork
from genesis.cosmic.seed import SeedBuilder, SeedPackage
from genesis.evolution.heritage import HeritageCodex
from genesis.evolution.speciation import BranchGenome, SpeciationEngine
from genesis.evolution.convergence import ConvergenceEngine
from genesis.evolution.mutation import MutationOperator
from genesis.metrics import (
    genesis_branches_total,
    genesis_chronicle_events_total,
    genesis_information_entropy_ratio,
    genesis_vault_records_total,
)


@dataclass(slots=True)
class SeedStatus:
    seed_id: str
    target: str
    launched_at: datetime
    hash_hex: str
    status: str


class CosmicNetworkService:
    """Coordinate seed deployment, evolution, and archival continuity."""

    def __init__(
        self,
        origin: str,
        prime_ethic: Iterable[str],
        storage_dir: Path | None = None,
        mutation_rate: float = 0.05,
    ) -> None:
        storage = storage_dir or Path.cwd() / "_cosmic_vault"
        storage.mkdir(parents=True, exist_ok=True)
        self.seed_builder = SeedBuilder(origin=origin, prime_ethic=prime_ethic)
        self.propagation = PropagationNetwork()
        self.consensus = LongDelayConsensus(node_id=origin)
        self.heritage = HeritageCodex(list(prime_ethic))
        self.vault = VaultStore(storage)
        self.retrieval = VaultRetrieval(self.vault)
        mutation = MutationOperator(rate=mutation_rate, scale=0.1)
        self.speciation = SpeciationEngine(mutation)
        self.convergence = ConvergenceEngine()
        self.chronicle = ChronicleLedger(storage / "chronicle.jsonl")
        self._seeds: Dict[str, SeedStatus] = {}
        self._entropy: float = 1.0

    async def deploy_seed(self, target: str, knowledge: dict[str, Any]) -> SeedPackage:
        package = await self.seed_builder.build(target=target, knowledge=knowledge)
        self._seeds[package.seed_id] = SeedStatus(
            seed_id=package.seed_id,
            target=target,
            launched_at=package.launched_at,
            hash_hex=package.hash_hex,
            status="launched",
        )
        await self.consensus.update(package.seed_id, {"status": "launched", "target": target})
        self.chronicle.append(
            branch_id=None,
            event_type="seed_launched",
            data={"seed_id": package.seed_id, "target": target},
        )
        genesis_chronicle_events_total.inc()
        return package

    def seed_status(self, seed_id: str) -> SeedStatus | None:
        return self._seeds.get(seed_id)

    async def propagate_state(self, seed_id: str, payload: dict[str, Any]) -> None:
        record = await self.propagation.apply(seed_id=seed_id, payload=payload)
        await self.consensus.update(seed_id, payload | {"vector_clock": record.vector_clock})

    async def cosmic_sync(self, remote_state: LongDelayConsensus) -> str:
        self.consensus.merge(remote_state)
        merkle = self.consensus.merkle_root()
        self._entropy = max(0.1, self._entropy * 0.99)
        genesis_information_entropy_ratio.set(self._entropy)
        return merkle

    async def create_branch(self, ancestor_id: str, params: List[float], count: int) -> list[BranchGenome]:
        branches = self.speciation.speciate(ancestor_id, params, count)
        for branch in branches:
            genesis_branches_total.inc()
            self.chronicle.append(
                branch_id=branch.identifier,
                event_type="branch_created",
                data={"ancestor": ancestor_id, "divergence": branch.divergence_score},
            )
            genesis_chronicle_events_total.inc()
        return branches

    async def converge_branches(
        self, branches: list[BranchGenome], fitness: dict[str, float], ethics_weight: float = 0.5
    ) -> list[float]:
        params = self.convergence.converge(branches, fitness, ethics_weight)
        self.chronicle.append(
            branch_id=None,
            event_type="branches_converged",
            data={"branches": [b.identifier for b in branches]},
        )
        genesis_chronicle_events_total.inc()
        return params

    async def snapshot_vault(self, name: str, data: bytes, redundancy: int = 3) -> str:
        record = await self.vault.snapshot(name=name, payload=data, redundancy_level=redundancy)
        genesis_vault_records_total.inc()
        self.chronicle.append(
            branch_id=None,
            event_type="vault_snapshot",
            data={"record_id": record.id, "hash": record.hash_hex},
        )
        genesis_chronicle_events_total.inc()
        return record.id

    async def retrieve_from_vault(self, record_id: str) -> bytes:
        return await self.retrieval.retrieve(record_id)

    def chronicle_events(self) -> list[ChronicleRecord]:
        return self.chronicle.history()


__all__ = ["CosmicNetworkService", "SeedStatus"]
