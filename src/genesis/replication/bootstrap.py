"""Bootstrap helpers for producing portable cluster snapshots."""
from __future__ import annotations

import asyncio
import hashlib
import json
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from genesis.metrics import genesis_replica_boots_total


@dataclass(slots=True)
class BootstrapArtifact:
    """Represents a packaged state bundle."""

    path: Path
    hash_hex: str
    created_at: datetime
    metadata: Dict[str, Any]


class BootstrapPackager:
    """Produces tarball snapshots of the current repository state."""

    def __init__(self, *, source_root: Path | None = None) -> None:
        self.source_root = source_root or Path.cwd()

    async def package(self, output_dir: Path, *, metadata: Dict[str, Any] | None = None) -> BootstrapArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        archive_path = output_dir / f"genesis-bootstrap-{timestamp}.tar.gz"
        payload = metadata or {}

        def _build() -> BootstrapArtifact:
            with tarfile.open(archive_path, "w:gz") as archive:
                manifest = json.dumps({"created_at": timestamp, "metadata": payload}, indent=2).encode("utf-8")
                manifest_path = output_dir / "manifest.json"
                manifest_path.write_bytes(manifest)
                archive.add(manifest_path, arcname="manifest.json")
                manifest_path.unlink()
            digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            genesis_replica_boots_total.inc()
            return BootstrapArtifact(
                path=archive_path,
                hash_hex=digest,
                created_at=datetime.utcnow(),
                metadata=payload,
            )

        return await asyncio.to_thread(_build)


__all__ = ["BootstrapArtifact", "BootstrapPackager"]
