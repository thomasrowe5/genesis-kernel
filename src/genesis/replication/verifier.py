"""Replica verification utilities."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Protocol

from genesis.metrics import genesis_self_repair_events_total

from ..collective.models import Replica


class HashedArtifact(Protocol):
    hash_hex: str
    path: object


class ReplicaVerifier:
    """Validates snapshot integrity before a replica joins the federation."""

    async def verify(self, artifact: HashedArtifact, *, expected_hash: str | None = None) -> bool:
        def _verify() -> bool:
            digest = artifact.hash_hex
            if expected_hash is not None and digest != expected_hash:
                return False
            if hasattr(artifact.path, "read_bytes"):
                data = artifact.path.read_bytes()
                computed = hashlib.sha256(data).hexdigest()
                return computed == digest
            return True

        result = await asyncio.to_thread(_verify)
        if result:
            genesis_self_repair_events_total.inc()
        return result

    async def approve(self, record: Replica) -> Replica:
        record.verified = True
        record.deployed_at = datetime.utcnow()
        return record


__all__ = ["ReplicaVerifier"]
