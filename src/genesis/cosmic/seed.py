"""Seed packaging logic for propagating Genesis across the cosmos."""
from __future__ import annotations

import asyncio
import gzip
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from pathlib import Path
from typing import Any, Iterable

from genesis.metrics import genesis_seeds_total
from genesis.utils.json_utils import canonical_dumps_bytes


@dataclass(slots=True)
class SeedPackage:
    """A compressed archive that can bootstrap a Genesis seed instance."""

    seed_id: str
    origin: str
    target: str
    archive_path: Path
    hash_hex: str
    launched_at: datetime
    manifest: dict[str, Any]


class SeedBuilder:
    """Create deterministic seed archives bundling ethics and knowledge payloads."""

    def __init__(self, origin: str, prime_ethic: Iterable[str], workdir: Path | None = None) -> None:
        self.origin = origin
        self.prime_ethic = list(prime_ethic)
        self.workdir = workdir or Path.cwd() / "_cosmic_seeds"
        self.workdir.mkdir(parents=True, exist_ok=True)

    async def build(self, target: str, knowledge: dict[str, Any]) -> SeedPackage:
        """Package a new seed archive for deployment."""

        seed_id = secrets.token_hex(8)
        launched_at = datetime.now(timezone.utc)
        manifest = {
            "seed_id": seed_id,
            "origin": self.origin,
            "target": target,
            "launched_at": launched_at.isoformat(),
            "ethic": self.prime_ethic,
            "knowledge": knowledge,
        }
        archive_path = self.workdir / f"seed-{seed_id}.json.gz"
        payload = canonical_dumps_bytes(manifest)
        await asyncio.to_thread(self._write_archive, archive_path, payload)
        hash_hex = blake2b(payload, digest_size=32).hexdigest()
        genesis_seeds_total.inc()
        return SeedPackage(
            seed_id=seed_id,
            origin=self.origin,
            target=target,
            archive_path=archive_path,
            hash_hex=hash_hex,
            launched_at=launched_at,
            manifest=manifest,
        )

    @staticmethod
    def _write_archive(path: Path, payload: bytes) -> None:
        with gzip.open(path, "wb") as fh:
            fh.write(payload)


__all__ = ["SeedBuilder", "SeedPackage"]
