"""Treaty negotiation and enforcement primitives for the planetary meta-network."""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Iterable, Mapping, MutableMapping, Optional

from genesis.metrics import genesis_treaties_active_total


class TreatyPhase(str, Enum):
    PROPOSED = "proposed"
    RATIFYING = "ratifying"
    RATIFIED = "ratified"
    ENFORCED = "enforced"
    REJECTED = "rejected"


def _canonical_payload(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class GenesisTreaty:
    """Captures the lifecycle of an inter-federation treaty."""

    treaty_id: str
    parties: Iterable[str]
    payload: Mapping[str, object]
    state: TreatyPhase = TreatyPhase.PROPOSED
    signatures: MutableMapping[str, str] = field(default_factory=dict)
    votes: MutableMapping[str, bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    ratified_at: Optional[datetime] = None

    def record_signature(self, federation_id: str, signature: str) -> None:
        self.signatures[federation_id] = signature

    def record_vote(self, federation_id: str, approve: bool) -> None:
        self.votes[federation_id] = approve

    def all_parties(self) -> tuple[str, ...]:
        return tuple(sorted(self.parties))


class SignatureLedger:
    """Small deterministic stand-in for persistent ed25519 signatures."""

    def __init__(self) -> None:
        self._private: MutableMapping[str, str] = {}

    def register_key(self, federation_id: str, seed: str | None = None) -> str:
        secret = seed or secrets.token_hex(16)
        public_key = hashlib.blake2b(secret.encode("utf-8"), digest_size=32).hexdigest()
        self._private[public_key] = secret
        return public_key

    def sign(self, public_key: str, message: str) -> str:
        secret = self._private.get(public_key)
        if secret is None:
            raise ValueError("Unknown public key")
        digest = hashlib.blake2b((message + secret).encode("utf-8"), digest_size=32)
        return digest.hexdigest()

    def verify(self, public_key: str, message: str, signature: str) -> bool:
        secret = self._private.get(public_key)
        if secret is None:
            return False
        expected = hashlib.blake2b((message + secret).encode("utf-8"), digest_size=32).hexdigest()
        return secrets.compare_digest(expected, signature)


class TreatyOrchestrator:
    """Coordinates three-phase treaty negotiation for federations."""

    def __init__(self, ledger: Optional[SignatureLedger] = None) -> None:
        self._ledger = ledger or SignatureLedger()
        self._treaties: MutableMapping[str, GenesisTreaty] = {}
        self._counter = 0
        genesis_treaties_active_total.set(0)

    def _next_id(self) -> str:
        self._counter += 1
        return f"treaty-{self._counter:04d}"

    def propose(self, parties: Iterable[str], payload: Mapping[str, object]) -> GenesisTreaty:
        treaty_id = self._next_id()
        treaty = GenesisTreaty(treaty_id=treaty_id, parties=tuple(parties), payload=dict(payload))
        self._treaties[treaty_id] = treaty
        genesis_treaties_active_total.set(self.active_treaty_count())
        return treaty

    def sign(self, treaty_id: str, federation_id: str, public_key: str) -> str:
        treaty = self._treaties[treaty_id]
        message = _canonical_payload({"treaty": treaty.treaty_id, "payload": treaty.payload})
        signature = self._ledger.sign(public_key, message)
        treaty.record_signature(federation_id, signature)
        return signature

    def register_key(self, federation_id: str, seed: str | None = None) -> str:
        return self._ledger.register_key(federation_id, seed=seed)

    def vote(self, treaty_id: str, federation_id: str, approve: bool, public_key: str) -> None:
        treaty = self._treaties[treaty_id]
        message = _canonical_payload({"treaty": treaty.treaty_id, "payload": treaty.payload})
        signature = treaty.signatures.get(federation_id)
        if signature is None or not self._ledger.verify(public_key, message, signature):
            raise ValueError("Invalid or missing signature for vote")
        if treaty.state == TreatyPhase.PROPOSED:
            treaty.state = TreatyPhase.RATIFYING
        if approve:
            treaty.record_vote(federation_id, True)
            if all(treaty.votes.get(party) for party in treaty.all_parties()):
                treaty.state = TreatyPhase.RATIFIED
                treaty.ratified_at = datetime.utcnow()
        else:
            treaty.record_vote(federation_id, False)
            treaty.state = TreatyPhase.REJECTED
        genesis_treaties_active_total.set(self.active_treaty_count())

    def enforce(self, treaty_id: str) -> GenesisTreaty:
        treaty = self._treaties[treaty_id]
        if treaty.state != TreatyPhase.RATIFIED:
            raise ValueError("Treaty must be ratified before enforcement")
        treaty.state = TreatyPhase.ENFORCED
        genesis_treaties_active_total.set(self.active_treaty_count())
        return treaty

    def treaty(self, treaty_id: str) -> GenesisTreaty:
        return self._treaties[treaty_id]

    def list_treaties(self) -> Iterable[GenesisTreaty]:
        return tuple(self._treaties.values())

    def active_treaty_count(self) -> int:
        return sum(1 for treaty in self._treaties.values() if treaty.state != TreatyPhase.REJECTED)


__all__ = [
    "GenesisTreaty",
    "TreatyOrchestrator",
    "TreatyPhase",
    "SignatureLedger",
]
