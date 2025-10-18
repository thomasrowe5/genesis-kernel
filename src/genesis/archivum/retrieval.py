"""Vault retrieval utilities."""
from __future__ import annotations

from genesis.archivum.vault import VaultStore


class VaultRetrieval:
    """Recover payloads from the archival vault, rebuilding parity when required."""

    def __init__(self, vault: VaultStore) -> None:
        self.vault = vault

    async def retrieve(self, record_id: str) -> bytes:
        payload = await self.vault.load(record_id)
        if not await self.vault.verify(record_id):
            raise ValueError("Vault integrity check failed")
        return payload


__all__ = ["VaultRetrieval"]
