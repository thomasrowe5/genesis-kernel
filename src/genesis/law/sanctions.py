"""Sanction enforcement utilities leveraging the exchange ledger."""
from __future__ import annotations

from dataclasses import dataclass
from genesis.metanet.exchange import ExchangeLedger


@dataclass(slots=True)
class Sanction:
    federation_id: str
    amount: float
    reason: str


class SanctionsEngine:
    """Applies penalties to federation credit balances."""

    def __init__(self) -> None:
        self._history: list[Sanction] = []

    def apply_credit_penalty(self, federation_id: str, amount: float, *, ledger: ExchangeLedger) -> Sanction:
        receipt = ledger.execute_atomic_swap(
            from_federation=federation_id,
            to_federation="planetary-treasury",
            amount=amount,
            asset_type="sanction",
        )
        _ = receipt
        sanction = Sanction(federation_id=federation_id, amount=amount, reason="court-sanction")
        self._history.append(sanction)
        return sanction

    def history(self) -> list[Sanction]:
        return list(self._history)


__all__ = ["SanctionsEngine", "Sanction"]
