"""Federation overlay network primitives."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any, Callable, List

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, select
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Session = Any  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

from genesis.metrics import genesis_federation_peers_total
from genesis.utils.json_utils import canonical_dumps_bytes

from .consensus import ConsensusEngine, ProposalDecision
from .economy import EconomyLedger, LedgerSnapshot
from .identity import IdentityRegistry
from .models import PeerNode


class FederationMesh:
    """Coordinates peer discovery, consensus and ledger state."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        *,
        consensus: ConsensusEngine | None = None,
        ledger: EconomyLedger | None = None,
        identity_registry: IdentityRegistry | None = None,
    ) -> None:
        self._session_factory = session_factory
        self.identity = identity_registry or IdentityRegistry()
        self.consensus = consensus or ConsensusEngine(session_factory)
        self.ledger = ledger or EconomyLedger(session_factory)
        self._federation_identity = self.identity.create("federation-root")

    async def register_peer(self, host: str, pubkey: str, stake: float = 0.0) -> PeerNode:
        """Persist a new peer node record."""

        def _op() -> PeerNode:
            with self._session_factory() as session:
                if select is not None:
                    existing = session.exec(select(PeerNode).where(PeerNode.host == host)).first()
                    if existing is not None:
                        existing.last_seen_at = datetime.utcnow()
                        existing.pubkey = pubkey
                        existing.stake = stake
                        session.add(existing)
                        session.commit()
                        session.refresh(existing)
                        return existing

                peer = PeerNode(host=host, pubkey=pubkey, stake=stake, status="active")
                session.add(peer)
                session.commit()
                session.refresh(peer)
                total = 1
                if select is not None:
                    total = len(session.exec(select(PeerNode)).all())
                genesis_federation_peers_total.set(total)
                return peer

        return await asyncio.to_thread(_op)

    async def peers(self) -> List[PeerNode]:
        def _fetch() -> List[PeerNode]:
            with self._session_factory() as session:
                if select is None:
                    return []
                results = list(session.exec(select(PeerNode).order_by(PeerNode.last_seen_at.desc())))
                genesis_federation_peers_total.set(len(results))
                return results

        return await asyncio.to_thread(_fetch)

    async def touch_peer(self, peer_id: int) -> None:
        """Update the heartbeat timestamp for a peer."""

        def _touch() -> None:
            with self._session_factory() as session:
                peer = session.get(PeerNode, peer_id)
                if peer is None:
                    raise ValueError(f"Unknown peer {peer_id}")
                peer.last_seen_at = datetime.utcnow()
                session.add(peer)
                session.commit()

        await asyncio.to_thread(_touch)

    async def submit_proposal(self, *, proposal_type: str, payload: dict[str, Any], proposer: str) -> int:
        proposal = await self.consensus.submit_proposal(
            proposal_type=proposal_type, payload=payload, proposer=proposer
        )
        return int(proposal.id or 0)

    async def vote(self, proposal_id: int, *, approve: bool, voter: str) -> ProposalDecision:
        result = await self.consensus.cast_vote(proposal_id, approve=approve, voter=voter)
        return result.decision

    async def ledger_snapshot(self) -> LedgerSnapshot:
        return await self.ledger.snapshot()

    async def credit_peer(self, peer_id: int, amount: float, reason: str) -> None:
        await self.ledger.record_transaction(from_id=None, to_id=peer_id, amount=amount, reason=reason)

    async def debit_peer(self, peer_id: int, amount: float, reason: str) -> None:
        await self.ledger.record_transaction(from_id=peer_id, to_id=None, amount=amount, reason=reason)

    async def signed_state(self) -> dict[str, Any]:
        """Return a signed summary of the federation and economy state."""

        peers = await self.peers()
        ledger = await self.ledger_snapshot()
        payload = {
            "peers": [peer.host for peer in peers],
            "ledger": [
                {
                    "from": tx.from_id,
                    "to": tx.to_id,
                    "amount": tx.amount,
                    "reason": tx.reason,
                    "at": tx.at.isoformat(),
                }
                for tx in ledger.transactions
            ],
        }
        message = canonical_dumps_bytes(payload)
        signature = self._federation_identity.sign(message)
        return {"payload": payload, "signature": signature, "signer": self._federation_identity.public_key}


__all__ = ["FederationMesh"]
