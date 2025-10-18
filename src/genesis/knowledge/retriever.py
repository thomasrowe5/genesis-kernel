"""Retrieval helpers bridging the knowledge graph and cognition modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .embeddings import EmbeddingStore
from .graphdb import KnowledgeGraph, KnowledgeNode


@dataclass(slots=True)
class RetrievedContext:
    """Bundle of nodes returned from semantic search."""

    nodes: List[KnowledgeNode]
    scores: List[float]


class KnowledgeRetriever:
    """Hybrid search using graph structure and embeddings."""

    def __init__(self, graph: KnowledgeGraph, embeddings: EmbeddingStore) -> None:
        self._graph = graph
        self._embeddings = embeddings

    def by_embedding(self, vector: Sequence[float], *, limit: int = 5) -> RetrievedContext:
        matches = self._embeddings.query(vector, limit=limit)
        nodes = [self._graph.get_node(match.node_id) for match in matches]
        scores = [self._score(match.vector, vector) for match in matches]
        return RetrievedContext(nodes=nodes, scores=scores)

    @staticmethod
    def _score(lhs: Sequence[float], rhs: Sequence[float]) -> float:
        numerator = sum(a * b for a, b in zip(lhs, rhs))
        return numerator


__all__ = ["KnowledgeRetriever", "RetrievedContext"]
