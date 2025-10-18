"""Lineage export/import helpers for provenance graphs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Mapping

from genesis.provenance.graph import ProvenanceGraph


class GraphExporter:
    """Serialize provenance graphs to JSONL files."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def export(self, graph: ProvenanceGraph) -> None:
        payload = graph.to_jsonable()
        with self.path.open("w", encoding="utf-8") as handle:
            for edge in payload["edges"]:
                line = json.dumps(edge)
                handle.write(line + "\n")


class GraphImporter:
    """Load provenance graph edges from JSONL files."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Iterator[Mapping[str, object]]:
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)

    def import_graph(self) -> ProvenanceGraph:
        graph = ProvenanceGraph()
        for edge_payload in self.load():
            graph.add_edge(
                edge_payload["src_type"],
                edge_payload["src_id"],
                edge_payload["dst_type"],
                edge_payload["dst_id"],
                edge_payload.get("relation", "unknown"),
                **edge_payload.get("metadata", {}),
            )
        return graph
