"""Low-bandwidth telemetry channels for interstellar Genesis seeds."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from typing import List


@dataclass(slots=True)
class BeaconMessage:
    seed_id: str
    status: str
    timestamp: datetime
    proof: str


class BeaconChannel:
    """Collect tamper-evident telemetry signals from remote seeds."""

    def __init__(self) -> None:
        self._messages: List[BeaconMessage] = []

    async def emit(self, seed_id: str, status: str) -> BeaconMessage:
        timestamp = datetime.now(timezone.utc)
        proof = self._sign(seed_id, status, timestamp)
        message = BeaconMessage(seed_id=seed_id, status=status, timestamp=timestamp, proof=proof)
        self._messages.append(message)
        await asyncio.sleep(0)
        return message

    def history(self) -> List[BeaconMessage]:
        return list(self._messages)

    @staticmethod
    def _sign(seed_id: str, status: str, timestamp: datetime) -> str:
        digest = blake2b(digest_size=16)
        digest.update(seed_id.encode())
        digest.update(status.encode())
        digest.update(timestamp.isoformat().encode())
        return digest.hexdigest()


__all__ = ["BeaconChannel", "BeaconMessage"]
