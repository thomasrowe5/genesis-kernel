"""Heritage encoding for ethical and scientific continuity."""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable, List


@dataclass(slots=True)
class HeritageCodex:
    """Encapsulate the immutable Prime Ethic for descendant seeds."""

    prime_ethic: List[str]
    fingerprint: str

    def __init__(self, prime_ethic: Iterable[str]) -> None:
        self.prime_ethic = list(prime_ethic)
        self.fingerprint = self._fingerprint(self.prime_ethic)

    def encode(self) -> str:
        return json.dumps({"prime_ethic": self.prime_ethic, "fingerprint": self.fingerprint})

    def verify(self, payload: str) -> bool:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            return False
        ethic = data.get("prime_ethic")
        fingerprint = data.get("fingerprint")
        if not isinstance(ethic, list) or not isinstance(fingerprint, str):
            return False
        return fingerprint == self._fingerprint(list(ethic))

    @staticmethod
    def _fingerprint(ethic: List[str]) -> str:
        digest = blake2b(digest_size=16)
        for rule in sorted(ethic):
            digest.update(rule.encode())
        return digest.hexdigest()


__all__ = ["HeritageCodex"]
