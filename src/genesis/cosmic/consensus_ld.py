"""Long-delay consensus primitives based on CRDTs and signed state vectors."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, Tuple

from genesis.metrics import genesis_cosmic_latency_seconds


@dataclass(slots=True)
class ConsensusEntry:
    seed_id: str
    version: int
    payload: dict[str, Any]
    timestamp: datetime
    signature: str


@dataclass(slots=True)
class ConsensusState:
    entries: Dict[str, ConsensusEntry] = field(default_factory=dict)

    def clone(self) -> "ConsensusState":
        return ConsensusState(entries=dict(self.entries))


class LongDelayConsensus:
    """Hybrid CRDT consensus tolerant to years of communication gaps."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._state = ConsensusState()
        self._latency_samples: list[float] = []

    async def update(self, seed_id: str, payload: dict[str, Any]) -> ConsensusEntry:
        """Update the local state for a seed, incrementing the version counter."""

        current = self._state.entries.get(seed_id)
        version = 1 if current is None else current.version + 1
        timestamp = datetime.now(timezone.utc)
        signature = self._sign(seed_id, version, payload, timestamp)
        entry = ConsensusEntry(
            seed_id=seed_id,
            version=version,
            payload=payload,
            timestamp=timestamp,
            signature=signature,
        )
        self._state.entries[seed_id] = entry
        await asyncio.sleep(0)
        return entry

    def merge(self, other: "LongDelayConsensus") -> None:
        """Merge a remote state using last-writer-wins semantics."""

        merged = self._state.clone()
        for seed_id, entry in other._state.entries.items():
            current = merged.entries.get(seed_id)
            if current is None or _wins(entry, current):
                merged.entries[seed_id] = entry
                latency = abs((entry.timestamp - datetime.now(timezone.utc)).total_seconds())
                self._latency_samples.append(latency)
                genesis_cosmic_latency_seconds.observe(latency)
        self._state = merged

    def export_state(self) -> ConsensusState:
        return self._state.clone()

    def merkle_root(self) -> str:
        """Return a Merkle-style digest summarizing the current state."""

        digest = blake2b(digest_size=32)
        for seed_id in sorted(self._state.entries):
            entry = self._state.entries[seed_id]
            digest.update(seed_id.encode())
            digest.update(entry.version.to_bytes(4, "big", signed=False))
            digest.update(entry.signature.encode())
        return digest.hexdigest()

    @property
    def latency_samples(self) -> Tuple[float, ...]:
        return tuple(self._latency_samples)

    def _sign(
        self, seed_id: str, version: int, payload: dict[str, Any], timestamp: datetime
    ) -> str:
        digest = blake2b(digest_size=16)
        digest.update(self.node_id.encode())
        digest.update(seed_id.encode())
        digest.update(version.to_bytes(4, "big", signed=False))
        digest.update(timestamp.isoformat().encode())
        digest.update(repr(sorted(payload.items())).encode())
        return digest.hexdigest()


def _wins(candidate: ConsensusEntry, incumbent: ConsensusEntry) -> bool:
    if candidate.version != incumbent.version:
        return candidate.version > incumbent.version
    return candidate.timestamp >= incumbent.timestamp


__all__ = ["ConsensusEntry", "ConsensusState", "LongDelayConsensus"]
