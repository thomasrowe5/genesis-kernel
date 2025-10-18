"""Mocked long-term vault with parity-based redundancy."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Dict

from genesis.cosmic.models import VaultRecord


@dataclass(slots=True)
class VaultIndexEntry:
    record: VaultRecord
    path: Path
    parity_path: Path


class VaultStore:
    """Persist payloads with redundant parity blocks for millennia-scale retention."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, VaultIndexEntry] = {}

    async def snapshot(self, name: str, payload: bytes, redundancy_level: int) -> VaultRecord:
        payload_path = self.root / f"{name}.bin"
        parity_path = self.root / f"{name}.parity"
        await asyncio.gather(
            asyncio.to_thread(self._write_file, payload_path, payload),
            asyncio.to_thread(self._write_file, parity_path, self._parity(payload, redundancy_level)),
        )
        hash_hex = blake2b(payload, digest_size=32).hexdigest()
        record = VaultRecord(
            id=name,
            hash_hex=hash_hex,
            payload_ref=str(payload_path),
            redundancy_level=redundancy_level,
        )
        self._index[name] = VaultIndexEntry(record=record, path=payload_path, parity_path=parity_path)
        return record

    async def verify(self, record_id: str) -> bool:
        entry = self._index.get(record_id)
        if not entry:
            return False
        payload = await asyncio.to_thread(Path(entry.path).read_bytes)
        hash_hex = blake2b(payload, digest_size=32).hexdigest()
        return hash_hex == entry.record.hash_hex

    async def load(self, record_id: str) -> bytes:
        entry = self._index.get(record_id)
        if not entry:
            raise KeyError(record_id)
        try:
            return await asyncio.to_thread(Path(entry.path).read_bytes)
        except FileNotFoundError:  # pragma: no cover - defensive
            parity = await asyncio.to_thread(Path(entry.parity_path).read_bytes)
            restored = self._restore(parity, entry.record.redundancy_level)
            await asyncio.to_thread(self._write_file, entry.path, restored)
            return restored

    @staticmethod
    def _write_file(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(payload)

    @staticmethod
    def _parity(payload: bytes, redundancy_level: int) -> bytes:
        if redundancy_level <= 0:
            raise ValueError("redundancy_level must be positive")
        parity = bytearray(payload)
        for _ in range(redundancy_level - 1):
            parity = bytearray(b ^ 0xFF for b in parity)
        return bytes(parity)

    @staticmethod
    def _restore(parity: bytes, redundancy_level: int) -> bytes:
        restored = bytearray(parity)
        for _ in range(redundancy_level - 1):
            restored = bytearray(b ^ 0xFF for b in restored)
        return bytes(restored)


__all__ = ["VaultStore"]
