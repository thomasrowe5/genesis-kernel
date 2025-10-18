"""Cache administration routes."""
from __future__ import annotations

from typing import Any, Dict, Iterable

from fastapi import APIRouter, Depends, Query

from ...router.cache import InMemoryCache

router = APIRouter(prefix="/cache", tags=["cache"])


def get_cache() -> InMemoryCache:  # pragma: no cover - runtime wiring
    raise RuntimeError("Cache dependency not configured")


@router.delete("")
def flush_cache(
    task: str | None = Query(default=None, description="Optional task prefix"),
    cache: InMemoryCache = Depends(get_cache),
) -> Dict[str, Any]:
    if task:
        cache.invalidate(f"cache:{task}")
    else:
        cache.invalidate()
    return {"cleared": True, "task": task}


@router.get("/keys")
def list_keys(
    prefix: str | None = Query(default=None, description="Optional prefix"),
    cache: InMemoryCache = Depends(get_cache),
) -> Dict[str, Iterable[str]]:
    keys = list(cache.keys(prefix))
    return {"keys": keys}


__all__ = ["router", "get_cache"]
