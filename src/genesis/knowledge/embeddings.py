"""Simple embedding store for semantic retrieval."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(slots=True)
class EmbeddingRecord:
    """Embedding associated with a node identifier."""

    node_id: str
    vector: Sequence[float]


class EmbeddingStore:
    """Lightweight in-memory vector index using cosine similarity."""

    def __init__(self) -> None:
        self._records: Dict[str, EmbeddingRecord] = {}

    def add(self, record: EmbeddingRecord) -> None:
        self._records[record.node_id] = record

    def query(self, vector: Sequence[float], *, limit: int = 5) -> List[EmbeddingRecord]:
        scored = [
            (self._cosine_similarity(vector, record.vector), record)
            for record in self._records.values()
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    @staticmethod
    def _cosine_similarity(lhs: Sequence[float], rhs: Sequence[float]) -> float:
        numerator = sum(a * b for a, b in zip(lhs, rhs))
        denom_lhs = math.sqrt(sum(a * a for a in lhs))
        denom_rhs = math.sqrt(sum(b * b for b in rhs))
        if denom_lhs == 0 or denom_rhs == 0:
            return 0.0
        return numerator / (denom_lhs * denom_rhs)


__all__ = ["EmbeddingRecord", "EmbeddingStore"]
