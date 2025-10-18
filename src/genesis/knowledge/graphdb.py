"""In-memory knowledge graph backing the cognition stack."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

from genesis.metrics import genesis_knowledge_nodes_total

from .ontology import KnowledgeNodeType, KnowledgeRelation


@dataclass(slots=True)
class KnowledgeNode:
    """Vertex stored in the knowledge graph."""

    id: str
    type: KnowledgeNodeType
    label: str
    properties: Mapping[str, object]


@dataclass(slots=True)
class KnowledgeEdge:
    """Directed edge between knowledge nodes."""

    id: str
    src_id: str
    dst_id: str
    relation: KnowledgeRelation
    properties: Mapping[str, object]


class KnowledgeGraph:
    """Minimal in-memory knowledge graph with convenience queries."""

    def __init__(self) -> None:
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}

    def add_node(self, node: KnowledgeNode) -> None:
        self._nodes[node.id] = node
        genesis_knowledge_nodes_total.set(len(self._nodes))

    def add_edge(self, edge: KnowledgeEdge) -> None:
        if edge.src_id not in self._nodes or edge.dst_id not in self._nodes:
            raise KeyError("Edge references unknown nodes")
        self._edges[edge.id] = edge

    def get_node(self, node_id: str) -> KnowledgeNode:
        return self._nodes[node_id]

    def neighbors(self, node_id: str, relation: KnowledgeRelation | None = None) -> List[KnowledgeNode]:
        edges = [edge for edge in self._edges.values() if edge.src_id == node_id]
        if relation:
            edges = [edge for edge in edges if edge.relation == relation]
        return [self._nodes[edge.dst_id] for edge in edges]

    def nodes_by_type(self, node_type: KnowledgeNodeType) -> Iterable[KnowledgeNode]:
        return [node for node in self._nodes.values() if node.type == node_type]

    def summary(self) -> Mapping[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
        }


__all__ = ["KnowledgeGraph", "KnowledgeNode", "KnowledgeEdge"]
