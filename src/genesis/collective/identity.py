"""Decentralised identity primitives for federation nodes."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Mapping


@dataclass(slots=True)
class PeerIdentity:
    """Identity material tracked per federation agent."""

    node_id: str
    public_key: str
    secret_key: bytes = field(repr=False)
    created_at: datetime = field(default_factory=datetime.utcnow)
    revoked: bool = False

    def sign(self, message: bytes) -> str:
        """Return a deterministic signature for ``message``."""

        digest = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        return digest


class IdentityRegistry:
    """In-memory DID-style registry used by the federation mesh."""

    def __init__(self) -> None:
        self._identities: Dict[str, PeerIdentity] = {}

    def create(self, node_id: str) -> PeerIdentity:
        """Create a new peer identity entry."""

        secret_key = secrets.token_bytes(32)
        public_key = hashlib.sha256(secret_key).hexdigest()
        identity = PeerIdentity(node_id=node_id, public_key=public_key, secret_key=secret_key)
        self._identities[node_id] = identity
        return identity

    def get(self, node_id: str) -> PeerIdentity:
        try:
            return self._identities[node_id]
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise KeyError(f"Unknown node identity '{node_id}'") from exc

    def revoke(self, node_id: str) -> None:
        identity = self.get(node_id)
        identity.revoked = True

    def verify(self, node_id: str, message: bytes, signature: str) -> bool:
        identity = self.get(node_id)
        if identity.revoked:
            return False
        expected = identity.sign(message)
        return hmac.compare_digest(expected, signature)

    def identities(self) -> Mapping[str, PeerIdentity]:
        return dict(self._identities)


__all__ = ["IdentityRegistry", "PeerIdentity"]
