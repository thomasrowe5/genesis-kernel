"""FastAPI routes exposing module registry data."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from genesis.registry.manager import ModuleRegistryManager

router = APIRouter(prefix="/modules", tags=["modules"])


def get_registry_manager() -> ModuleRegistryManager:  # pragma: no cover - runtime wiring
    raise RuntimeError("ModuleRegistryManager dependency not configured")


@router.get("/leaderboard")
def leaderboard(
    limit: int = 10,
    registry: ModuleRegistryManager = Depends(get_registry_manager),
) -> list[dict[str, object]]:
    """Return the top scoring module variants."""

    return registry.leaderboard(limit=limit)


__all__ = ["router", "get_registry_manager"]
