"""Cache helpers for pure tasks."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Tuple

from genesis.metrics import genesis_cache_hits_total


CACHEABLE_TASKS: Dict[str, int] = {
    "fibonacci": 3600,
    "http_fetch": 0,
    "sleep": 0,
}


@dataclass(slots=True)
class CacheResult:
    hit: bool
    value: Any


class InMemoryCache:
    """Simple TTL cache keyed by task/module/version."""

    def __init__(self, default_ttl: int = 3600) -> None:
        self._default_ttl = default_ttl
        self._store: Dict[str, Tuple[float, Any]] = {}

    def _now(self) -> float:
        return time.time()

    @property
    def default_ttl(self) -> int:
        return int(self._default_ttl)

    def make_key(
        self,
        task_type: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        *,
        module: str,
        version: str,
    ) -> str:
        payload = json.dumps([task_type, args, kwargs], sort_keys=True, default=str)
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
        return f"cache:{task_type}:{module}:{version}:{digest}"

    def get(self, key: str) -> CacheResult | None:
        entry = self._store.get(key)
        if not entry:
            return None
        expiry, value = entry
        if expiry < self._now():
            self._store.pop(key, None)
            return None
        return CacheResult(hit=True, value=value)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (self._now() + ttl, value)

    def get_or_set(
        self,
        task_type: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        *,
        module: str,
        version: str,
        compute: Callable[[], Any],
    ) -> CacheResult:
        key = self.make_key(task_type, args, kwargs, module=module, version=version)
        cached = self.get(key)
        if cached:
            genesis_cache_hits_total.labels(task_type).inc()
            return cached
        value = compute()
        ttl = CACHEABLE_TASKS.get(task_type, self._default_ttl)
        if ttl > 0:
            self.set(key, value, ttl=ttl)
        return CacheResult(hit=False, value=value)

    def invalidate(self, prefix: str | None = None) -> None:
        if prefix is None:
            self._store.clear()
            return
        keys = [key for key in self._store if key.startswith(prefix)]
        for key in keys:
            self._store.pop(key, None)

    def keys(self, prefix: str | None = None) -> Iterable[str]:
        if prefix is None:
            return list(self._store.keys())
        return [key for key in self._store if key.startswith(prefix)]


__all__ = ["CACHEABLE_TASKS", "CacheResult", "InMemoryCache"]
