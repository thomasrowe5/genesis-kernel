"""Asynchronous overlay network modelling federation connectivity."""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from statistics import mean
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional

from genesis.metrics import genesis_latency_mean_ms, genesis_metanet_federations_total


class LinkStatus(str, Enum):
    """Enumerates the lifecycle of a federation link."""

    PENDING = "pending"
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


@dataclass(slots=True)
class FederationProfile:
    """Identity and transport metadata for a federation."""

    federation_id: str
    human_name: str
    public_key: str
    endpoints: List[str]
    capabilities: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class FederationLinkState:
    """Represents an overlay connection between two federations."""

    origin_id: str
    partner_id: str
    latency_ms: float
    status: LinkStatus = LinkStatus.PENDING

    def activate(self) -> None:
        self.status = LinkStatus.ACTIVE

    def degrade(self) -> None:
        self.status = LinkStatus.DEGRADED

    def disconnect(self) -> None:
        self.status = LinkStatus.DISCONNECTED


class DeterministicLatencyModel:
    """Produces deterministic pseudo-latency for link negotiation."""

    def __init__(self, seed: str = "genesis-mesh") -> None:
        self.seed = seed

    def __call__(self, origin: str, partner: str) -> float:
        key = "::".join(sorted([origin, partner])) + self.seed
        digest = hashlib.blake2b(key.encode("utf-8"), digest_size=4).digest()
        raw = int.from_bytes(digest, "big")
        # Clamp to 10-250ms range for simulation purposes.
        return 10.0 + (raw % 24000) / 100.0


class MetaNetInterconnect:
    """Maintains the peer-to-peer mesh between Genesis federations."""

    def __init__(
        self,
        *,
        latency_model: Optional[DeterministicLatencyModel] = None,
    ) -> None:
        self._latency_model = latency_model or DeterministicLatencyModel()
        self._federations: MutableMapping[str, FederationProfile] = {}
        self._links: MutableMapping[tuple[str, str], FederationLinkState] = {}
        self._lock = asyncio.Lock()
        self._update_federation_metric()

    def _update_federation_metric(self) -> None:
        genesis_metanet_federations_total.set(len(self._federations))

    def _update_latency_metric(self) -> None:
        if self._links:
            latencies = [link.latency_ms for link in self._links.values() if link.status == LinkStatus.ACTIVE]
            if latencies:
                genesis_latency_mean_ms.set(mean(latencies))

    async def register_federation(self, profile: FederationProfile) -> None:
        """Register a federation into the meta-network registry."""

        async with self._lock:
            self._federations[profile.federation_id] = profile
            self._update_federation_metric()

    def federations(self) -> Mapping[str, FederationProfile]:
        return dict(self._federations)

    async def establish_link(self, origin_id: str, partner_id: str) -> FederationLinkState:
        """Negotiate and activate a link between two registered federations."""

        async with self._lock:
            if origin_id not in self._federations or partner_id not in self._federations:
                raise ValueError("Both federations must be registered before linking")
            key = (origin_id, partner_id)
            reverse_key = (partner_id, origin_id)
            state = self._links.get(key) or self._links.get(reverse_key)
            if state is None:
                latency_ms = self._latency_model(origin_id, partner_id)
                state = FederationLinkState(origin_id=origin_id, partner_id=partner_id, latency_ms=latency_ms)
                self._links[key] = state
            state.activate()
            self._links[key] = state
            self._links[reverse_key] = FederationLinkState(
                origin_id=partner_id,
                partner_id=origin_id,
                latency_ms=state.latency_ms,
                status=state.status,
            )
            self._update_latency_metric()
            return state

    async def broadcast(self, origin_id: str, payload: Mapping[str, object]) -> Dict[str, Mapping[str, object]]:
        """Simulate broadcasting a payload across all active links."""

        async with self._lock:
            if origin_id not in self._federations:
                raise ValueError("Origin federation is not registered")
            results: Dict[str, Mapping[str, object]] = {}
            for (src, dst), link in list(self._links.items()):
                if src == origin_id and link.status == LinkStatus.ACTIVE:
                    await asyncio.sleep(0)
                    results[dst] = {"latency_ms": link.latency_ms, "payload": dict(payload)}
            return results

    async def degrade_link(self, origin_id: str, partner_id: str) -> None:
        async with self._lock:
            key = (origin_id, partner_id)
            link = self._links.get(key)
            if link:
                link.degrade()
                self._links[key] = link
                self._update_latency_metric()

    async def disconnect(self, origin_id: str, partner_id: str) -> None:
        async with self._lock:
            key = (origin_id, partner_id)
            reverse_key = (partner_id, origin_id)
            if key in self._links:
                self._links[key].disconnect()
            if reverse_key in self._links:
                self._links[reverse_key].disconnect()
            self._update_latency_metric()

    async def sync_snapshot(self) -> Dict[str, object]:
        async with self._lock:
            return {
                "federations": [asdict(profile) for profile in self._federations.values()],
                "links": [
                    {
                        "origin_id": link.origin_id,
                        "partner_id": link.partner_id,
                        "latency_ms": link.latency_ms,
                        "status": link.status.value,
                    }
                    for link in self._links.values()
                    if link.status == LinkStatus.ACTIVE
                ],
            }

    async def ensure_mesh(self, federation_ids: Iterable[str]) -> List[FederationLinkState]:
        """Convenience helper establishing a fully connected mesh for the provided federations."""

        tasks = []
        ids = list(federation_ids)
        for idx, origin in enumerate(ids):
            for partner in ids[idx + 1 :]:
                tasks.append(self.establish_link(origin, partner))
        return await asyncio.gather(*tasks)


__all__ = [
    "MetaNetInterconnect",
    "FederationProfile",
    "FederationLinkState",
    "LinkStatus",
    "DeterministicLatencyModel",
]
