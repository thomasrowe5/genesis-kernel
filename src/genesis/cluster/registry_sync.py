"""Gossip-based registry synchronization utilities."""
from __future__ import annotations
"""Gossip-based registry synchronization utilities."""

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping

import httpx

LOGGER = logging.getLogger(__name__)


@dataclass
class ModuleVersionPayload:
    module: str
    version: str
    metadata: Mapping[str, Any]


class RegistrySyncClient:
    """Pushes registry updates and metrics to peer nodes."""

    def __init__(self, peers: Iterable[str], timeout: float = 5.0) -> None:
        self._peers = list(peers)
        self._timeout = timeout

    async def broadcast_version(self, payload: ModuleVersionPayload) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await asyncio.gather(
                *[
                    self._post_json(client, peer, "module", asdict(payload))
                    for peer in self._peers
                ]
            )

    async def broadcast_metrics(self, metrics: Mapping[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await asyncio.gather(
                *[
                    self._post_json(client, peer, "metrics", metrics)
                    for peer in self._peers
                ]
            )

    async def _post_json(
        self, client: httpx.AsyncClient, peer: str, topic: str, payload: Any
    ) -> None:
        try:
            await client.post(f"{peer}/cluster/sync", json={"topic": topic, "payload": payload})
        except httpx.RequestError as exc:
            LOGGER.warning("Failed to push %s update to %s: %s", topic, peer, exc)

    def update_peers(self, peers: Iterable[str]) -> None:
        self._peers = list(peers)


class RegistrySnapshot:
    """Simple in-memory registry mirror used during sync operations."""

    def __init__(self) -> None:
        self._versions: Dict[str, Dict[str, Mapping[str, Any]]] = {}
        self._metrics: Dict[str, Any] = {}

    def apply_version(self, payload: ModuleVersionPayload) -> None:
        module_versions = self._versions.setdefault(payload.module, {})
        module_versions[payload.version] = payload.metadata

    def apply_metrics(self, metrics: Mapping[str, Any]) -> None:
        self._metrics.update(metrics)

    def versions(self, module: str) -> Mapping[str, Mapping[str, Any]]:
        return self._versions.get(module, {})

    def all_versions(self) -> Dict[str, Dict[str, Mapping[str, Any]]]:
        return self._versions

    def metrics(self) -> Mapping[str, Any]:
        return self._metrics

    def summary(self) -> Dict[str, Any]:
        return {"versions": self._versions, "metrics": self._metrics}


async def periodic_sync(
    client: RegistrySyncClient, payload_supplier: callable, interval: float
) -> None:
    """Background coroutine periodically broadcasting registry deltas."""

    while True:
        payloads: List[ModuleVersionPayload] = payload_supplier()
        for payload in payloads:
            await client.broadcast_version(payload)
        await asyncio.sleep(interval)
