"""Immutable cosmic chronicle for Genesis branches."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from pathlib import Path
from typing import Any, Dict, List, Optional

from genesis.cosmic.models import ChronicleEvent
from genesis.utils.json_utils import canonical_dumps


@dataclass(slots=True)
class ChronicleRecord:
    event: ChronicleEvent
    hash_hex: str


class ChronicleLedger:
    """Append-only ledger capturing milestones across branches."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._history: List[ChronicleRecord] = []
        if self.path.exists():
            self._load()

    def append(self, branch_id: Optional[str], event_type: str, data: Dict[str, Any]) -> ChronicleRecord:
        at = datetime.now(timezone.utc)
        payload = canonical_dumps(data)
        event = ChronicleEvent(id=f"evt-{len(self._history)+1}", branch_id=branch_id, type=event_type, at=at, data_json=payload)
        hash_hex = self._hash(event, self._history[-1].hash_hex if self._history else "0" * 64)
        record = ChronicleRecord(event=event, hash_hex=hash_hex)
        self._history.append(record)
        self._persist(record)
        return record

    def history(self) -> List[ChronicleRecord]:
        return list(self._history)

    def _persist(self, record: ChronicleRecord) -> None:
        line = canonical_dumps(
            {
                "id": record.event.id,
                "branch_id": record.event.branch_id,
                "type": record.event.type,
                "at": record.event.at.isoformat(),
                "data": record.event.data_json,
                "hash": record.hash_hex,
            }
        )
        self._write_line(line)

    def _load(self) -> None:
        for line in self.path.read_text().splitlines():
            if not line:
                continue
            payload = json.loads(line)
            event = ChronicleEvent(
                id=payload["id"],
                branch_id=payload.get("branch_id"),
                type=payload["type"],
                at=datetime.fromisoformat(payload["at"]),
                data_json=payload["data"],
            )
            self._history.append(ChronicleRecord(event=event, hash_hex=payload["hash"]))

    def _write_line(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    @staticmethod
    def _hash(event: ChronicleEvent, previous_hash: str) -> str:
        digest = blake2b(digest_size=32)
        digest.update(previous_hash.encode())
        digest.update(event.id.encode())
        digest.update(event.type.encode())
        digest.update(event.data_json.encode())
        digest.update(event.at.isoformat().encode())
        return digest.hexdigest()


__all__ = ["ChronicleLedger", "ChronicleRecord"]
