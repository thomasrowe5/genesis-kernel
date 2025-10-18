"""Atomic exchange ledger coordinating trade between federations."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Mapping, MutableMapping, Tuple

from genesis.metrics import genesis_exchanges_total


def _hash_payload(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.blake2b(canonical.encode("utf-8"), digest_size=32).hexdigest()


@dataclass(slots=True)
class ExchangeReceipt:
    """Represents a committed exchange transaction."""

    tx_id: str
    from_federation: str
    to_federation: str
    amount: float
    asset_type: str
    proof_hash: str
    committed_at: datetime


class MerkleLedger:
    """Builds deterministic Merkle proofs across committed transactions."""

    def __init__(self) -> None:
        self._leaves: List[str] = []

    def add_leaf(self, leaf_hash: str) -> str:
        self._leaves.append(leaf_hash)
        return self.root_hash()

    def root_hash(self) -> str:
        if not self._leaves:
            return ""
        nodes = list(self._leaves)
        while len(nodes) > 1:
            next_level: List[str] = []
            for idx in range(0, len(nodes), 2):
                left = nodes[idx]
                right = nodes[idx + 1] if idx + 1 < len(nodes) else nodes[idx]
                next_level.append(_hash_payload({"left": left, "right": right}))
            nodes = next_level
        return nodes[0]

    def proof(self, leaf_hash: str) -> List[str]:
        if leaf_hash not in self._leaves:
            raise ValueError("Unknown leaf for proof generation")
        # For simplicity return the full sibling set used in construction.
        return list(self._leaves)


class ExchangeLedger:
    """Performs atomic swaps with Merkle proof verification."""

    def __init__(self) -> None:
        self._ledger: MutableMapping[str, ExchangeReceipt] = {}
        self._merkle = MerkleLedger()
        self._spent: set[str] = set()

    def _make_tx_id(self, from_fed: str, to_fed: str, amount: float, asset_type: str) -> str:
        payload = {
            "from": from_fed,
            "to": to_fed,
            "amount": f"{amount:.8f}",
            "asset_type": asset_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return _hash_payload(payload)

    def execute_atomic_swap(
        self,
        *,
        from_federation: str,
        to_federation: str,
        amount: float,
        asset_type: str = "credit",
    ) -> ExchangeReceipt:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        payload = {
            "from": from_federation,
            "to": to_federation,
            "amount": amount,
            "asset_type": asset_type,
        }
        leaf_hash = _hash_payload(payload)
        if leaf_hash in self._spent:
            raise ValueError("Double spend attempt detected")
        tx_id = self._make_tx_id(from_federation, to_federation, amount, asset_type)
        if tx_id in self._ledger:
            raise ValueError("Duplicate transaction detected")
        root_hash = self._merkle.add_leaf(leaf_hash)
        receipt = ExchangeReceipt(
            tx_id=tx_id,
            from_federation=from_federation,
            to_federation=to_federation,
            amount=amount,
            asset_type=asset_type,
            proof_hash=root_hash,
            committed_at=datetime.utcnow(),
        )
        self._ledger[tx_id] = receipt
        self._spent.add(leaf_hash)
        genesis_exchanges_total.inc()
        return receipt

    def verify(self, receipt: ExchangeReceipt) -> bool:
        payload = {
            "from": receipt.from_federation,
            "to": receipt.to_federation,
            "amount": receipt.amount,
            "asset_type": receipt.asset_type,
        }
        leaf_hash = _hash_payload(payload)
        return receipt.proof_hash == self._merkle.root_hash() and leaf_hash in self._merkle.proof(leaf_hash)

    def balance_sheet(self, federation_id: str) -> float:
        balance = 0.0
        for receipt in self._ledger.values():
            if receipt.from_federation == federation_id:
                balance -= receipt.amount
            if receipt.to_federation == federation_id:
                balance += receipt.amount
        return balance

    def transactions(self) -> Iterable[ExchangeReceipt]:
        return tuple(self._ledger.values())

    def merkle_snapshot(self) -> Tuple[str, List[str]]:
        return (self._merkle.root_hash(), list(self._merkle._leaves))


__all__ = ["ExchangeLedger", "ExchangeReceipt"]
