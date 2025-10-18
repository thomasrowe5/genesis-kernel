"""Replication helpers for reconnecting Genesis seeds across light-years."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict

from genesis.metrics import genesis_reconciliation_cycles_total


@dataclass(slots=True)
class PropagationRecord:
    """State update propagated between distant seeds."""

    seed_id: str
    vector_clock: int
    payload: dict[str, Any]
    updated_at: datetime
    proof: str


@dataclass(slots=True)
class CRDTState:
    """Observed-remove dictionary tracking replicated state."""

    entries: Dict[str, PropagationRecord] = field(default_factory=dict)

    def merge(self, other: "CRDTState") -> "CRDTState":
        merged = CRDTState(entries=dict(self.entries))
        for seed_id, record in other.entries.items():
            current = merged.entries.get(seed_id)
            if current is None or record.vector_clock > current.vector_clock:
                merged.entries[seed_id] = record
        return merged


class PropagationNetwork:
    """Coordinate state replication between long-disconnected Genesis seeds."""

    def __init__(self) -> None:
        self._state = CRDTState()

    async def apply(self, seed_id: str, payload: dict[str, Any]) -> PropagationRecord:
        """Record an update emitted by a remote seed."""

        current = self._state.entries.get(seed_id)
        vector_clock = 1 if current is None else current.vector_clock + 1
        updated_at = datetime.now(timezone.utc)
        proof = self._calculate_proof(seed_id, vector_clock, payload, updated_at)
        record = PropagationRecord(
            seed_id=seed_id,
            vector_clock=vector_clock,
            payload=payload,
            updated_at=updated_at,
            proof=proof,
        )
        self._state.entries[seed_id] = record
        genesis_reconciliation_cycles_total.inc()
        await asyncio.sleep(0)
        return record

    def merge(self, remote_state: CRDTState) -> None:
        self._state = self._state.merge(remote_state)

    def snapshot(self) -> CRDTState:
        return CRDTState(entries=dict(self._state.entries))

    @staticmethod
    def _calculate_proof(
        seed_id: str, vector_clock: int, payload: dict[str, Any], updated_at: datetime
    ) -> str:
        digest = blake2b(digest_size=16)
        digest.update(seed_id.encode())
        digest.update(vector_clock.to_bytes(4, "big", signed=False))
        digest.update(updated_at.isoformat().encode())
        digest.update(jsonish(payload))
        return digest.hexdigest()


def jsonish(payload: dict[str, Any]) -> bytes:
    """Deterministically encode payload dictionaries for hashing."""

    items = sorted(payload.items())
    encoded = []
    for key, value in items:
        encoded.append(key.encode())
        encoded.append(repr(value).encode())
    return b"|".join(encoded)


__all__ = ["PropagationNetwork", "CRDTState", "PropagationRecord"]
