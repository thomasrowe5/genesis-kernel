"""Adaptive router selecting the best module implementation at runtime."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from genesis.registry.models import ModuleVersion


class PromptMeshRouter:
    """Maintains an in-memory leaderboard of module variants for routing."""

    def __init__(self, top_n: int = 3) -> None:
        self._top_n = top_n
        self._registry: Dict[str, List[ModuleVersion]] = {}

    def update_module(self, module: str, candidates: Iterable[ModuleVersion]) -> None:
        sorted_candidates = sorted(candidates, key=lambda mv: mv.score, reverse=True)
        self._registry[module] = sorted_candidates[: self._top_n]

    def select(self, module: str) -> Optional[ModuleVersion]:
        variants = self._registry.get(module)
        if not variants:
            return None
        return variants[0]

    def ranked(self, module: str) -> List[ModuleVersion]:
        return list(self._registry.get(module, []))


__all__ = ["PromptMeshRouter"]
