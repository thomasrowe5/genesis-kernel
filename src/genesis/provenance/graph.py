"""In-memory provenance graph capturing causal relationships."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Tuple

from genesis.metrics import genesis_provenance_edges_total


@dataclass(frozen=True)
class ProvenanceEdge:
    src_type: str
    src_id: str
    dst_type: str
    dst_id: str
    relation: str
    at: dt.datetime
    metadata: Mapping[str, Any]


class ProvenanceGraph:
    """Mutable provenance graph storing edges and node metadata."""

    def __init__(self) -> None:
        self._nodes: MutableMapping[Tuple[str, str], Dict[str, Any]] = {}
        self._edges: List[ProvenanceEdge] = []

    def add_node(self, node_type: str, node_id: str, **metadata: Any) -> None:
        self._nodes[(node_type, node_id)] = metadata

    def add_edge(
        self,
        src_type: str,
        src_id: str,
        dst_type: str,
        dst_id: str,
        relation: str,
        at: Optional[dt.datetime] = None,
        **metadata: Any,
    ) -> ProvenanceEdge:
        if (src_type, src_id) not in self._nodes:
            self.add_node(src_type, src_id)
        if (dst_type, dst_id) not in self._nodes:
            self.add_node(dst_type, dst_id)
        edge = ProvenanceEdge(
            src_type=src_type,
            src_id=src_id,
            dst_type=dst_type,
            dst_id=dst_id,
            relation=relation,
            at=at or dt.datetime.now(tz=dt.timezone.utc),
            metadata=metadata,
        )
        self._edges.append(edge)
        genesis_provenance_edges_total.inc()
        return edge

    def nodes(self) -> Iterator[Tuple[str, str, Mapping[str, Any]]]:
        for (node_type, node_id), metadata in self._nodes.items():
            yield node_type, node_id, metadata

    def edges(self) -> Iterable[ProvenanceEdge]:
        return list(self._edges)

    def neighbors(self, node_type: str, node_id: str) -> List[ProvenanceEdge]:
        return [edge for edge in self._edges if edge.src_type == node_type and edge.src_id == node_id]

    def inbound(self, node_type: str, node_id: str) -> List[ProvenanceEdge]:
        return [edge for edge in self._edges if edge.dst_type == node_type and edge.dst_id == node_id]

    def subgraph(self, node_type: str, node_id: str) -> "ProvenanceGraph":
        visited = set()
        stack = [(node_type, node_id)]
        subgraph = ProvenanceGraph()
        while stack:
            current_type, current_id = stack.pop()
            if (current_type, current_id) in visited:
                continue
            visited.add((current_type, current_id))
            metadata = self._nodes.get((current_type, current_id), {})
            subgraph.add_node(current_type, current_id, **metadata)
            for edge in self.neighbors(current_type, current_id):
                subgraph.add_edge(
                    edge.src_type,
                    edge.src_id,
                    edge.dst_type,
                    edge.dst_id,
                    edge.relation,
                    at=edge.at,
                    **edge.metadata,
                )
                stack.append((edge.dst_type, edge.dst_id))
        return subgraph

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "nodes": [
                {
                    "type": node_type,
                    "id": node_id,
                    "metadata": metadata,
                }
                for (node_type, node_id), metadata in self._nodes.items()
            ],
            "edges": [
                {
                    "src_type": edge.src_type,
                    "src_id": edge.src_id,
                    "dst_type": edge.dst_type,
                    "dst_id": edge.dst_id,
                    "relation": edge.relation,
                    "at": edge.at.isoformat(),
                    "metadata": dict(edge.metadata),
                }
                for edge in self._edges
            ],
        }

    @classmethod
    def from_jsonable(cls, payload: Mapping[str, Any]) -> "ProvenanceGraph":
        graph = cls()
        for node in payload.get("nodes", []):
            graph.add_node(node["type"], node["id"], **node.get("metadata", {}))
        for edge_payload in payload.get("edges", []):
            graph.add_edge(
                edge_payload["src_type"],
                edge_payload["src_id"],
                edge_payload["dst_type"],
                edge_payload["dst_id"],
                edge_payload["relation"],
                at=dt.datetime.fromisoformat(edge_payload["at"]),
                **edge_payload.get("metadata", {}),
            )
        return graph
