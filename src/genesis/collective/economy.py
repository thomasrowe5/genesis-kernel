"""Internal credit and token accounting for the Genesis federation."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable, Dict

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, select
except Exception:  # pragma: no cover - fallback when SQLModel is unavailable
    Session = Any  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

from genesis.metrics import genesis_economy_tx_total

from .models import EconomyTx


@dataclass(slots=True)
class LedgerSnapshot:
    """Simple view over the economy ledger."""

    balances: Dict[int, float]
    transactions: list[EconomyTx]


class EconomyLedger:
    """Records transfers of genesis credits between federation members."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        *,
        credit_cap: float = 1_000_000.0,
    ) -> None:
        self._session_factory = session_factory
        self.credit_cap = credit_cap

    async def record_transaction(
        self,
        *,
        from_id: int | None,
        to_id: int | None,
        amount: float,
        reason: str,
    ) -> EconomyTx:
        """Persist a debit/credit entry in the ledger."""

        if amount == 0:
            raise ValueError("Transaction amount must be non-zero")

        def _op() -> EconomyTx:
            with self._session_factory() as session:
                tx = EconomyTx(
                    from_id=from_id,
                    to_id=to_id,
                    amount=amount,
                    reason=reason,
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)
                genesis_economy_tx_total.labels(reason=reason).inc()
                return tx

        return await asyncio.to_thread(_op)

    async def balance(self, peer_id: int) -> float:
        """Compute the running balance for a peer."""

        def _calc() -> float:
            if select is None:
                return 0.0
            with self._session_factory() as session:
                outgoing = session.exec(
                    select(EconomyTx.amount).where(EconomyTx.from_id == peer_id)
                ).all()
                incoming = session.exec(
                    select(EconomyTx.amount).where(EconomyTx.to_id == peer_id)
                ).all()
                return sum(incoming) - sum(outgoing)

        return float(await asyncio.to_thread(_calc))

    async def snapshot(self, limit: int = 100) -> LedgerSnapshot:
        """Return a truncated history of ledger activity."""

        def _snapshot() -> LedgerSnapshot:
            if select is None:
                return LedgerSnapshot(balances={}, transactions=[])
            with self._session_factory() as session:
                transactions = list(
                    session.exec(
                        select(EconomyTx).order_by(EconomyTx.at.desc()).limit(limit)
                    )
                )
                balances: Dict[int, float] = {}
                for tx in transactions:
                    if tx.to_id is not None:
                        balances[tx.to_id] = balances.get(tx.to_id, 0.0) + tx.amount
                    if tx.from_id is not None:
                        balances[tx.from_id] = balances.get(tx.from_id, 0.0) - tx.amount
                return LedgerSnapshot(balances=balances, transactions=list(transactions))

        return await asyncio.to_thread(_snapshot)


__all__ = ["EconomyLedger", "LedgerSnapshot"]
