"""Ontology definitions for the Genesis knowledge graph."""
from __future__ import annotations

from enum import Enum


class KnowledgeNodeType(str, Enum):
    """Supported node categories."""

    MODULE = "module"
    METRIC = "metric"
    EXPERIMENT = "experiment"
    POLICY = "policy"


class KnowledgeRelation(str, Enum):
    """Relationships between knowledge nodes."""

    IMPROVES = "improves"
    DEGRADES = "degrades"
    MEASURES = "measures"
    DERIVED_FROM = "derived_from"


__all__ = ["KnowledgeNodeType", "KnowledgeRelation"]
