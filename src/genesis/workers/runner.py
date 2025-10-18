"""Worker runner integrating routing, caching, and optimization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

from genesis.registry.manager import ModuleRegistryManager

from ..optimizer.online import OnlineOptimizer, Outcome
from ..router.cache import CACHEABLE_TASKS, InMemoryCache
from ..router.rate_limit import TokenBucketRateLimiter
from ..router.router import PromptRouter


@dataclass(slots=True)
class ExecutionResult:
    output: Any
    score: float
    latency_ms: float
    success: bool = True


class RateLimitExceededError(Exception):
    """Raised when the rate limiter rejects an execution."""


class WorkerRunner:
    def __init__(
        self,
        registry: ModuleRegistryManager,
        router: PromptRouter,
        optimizer: OnlineOptimizer,
        cache: InMemoryCache,
        rate_limiter: TokenBucketRateLimiter,
        executor: Callable[[str, str, Tuple[Any, ...], Dict[str, Any]], ExecutionResult],
    ) -> None:
        self._registry = registry
        self._router = router
        self._optimizer = optimizer
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._executor = executor

    def run(
        self,
        task_type: str,
        args: Tuple[Any, ...] = (),
        kwargs: Dict[str, Any] | None = None,
        *,
        key: str | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Any:
        kwargs = kwargs or {}
        context = context or {}
        if not self._rate_limiter.allow(task_type, key=key):
            raise RateLimitExceededError(task_type)
        decision = self._router.route(task_type, context=context)
        module_version = self._registry.get_version(decision.module, decision.version)
        if module_version is None:
            raise RuntimeError(f"Unknown module version {decision.module}:{decision.version}")
        cache_key: str | None = None
        if self._is_cacheable(task_type):
            cache_key = self._cache.make_key(
                task_type,
                args,
                kwargs,
                module=decision.module,
                version=decision.version,
            )
            cached = self._cache.get(cache_key)
            if cached:
                return cached.value
        result = self._executor(decision.module, decision.version, args, kwargs)
        if not isinstance(result, ExecutionResult):
            raise TypeError("Executor must return ExecutionResult")
        if result.success and cache_key is not None:
            ttl = CACHEABLE_TASKS.get(task_type, self._cache.default_ttl)
            if ttl > 0:
                self._cache.set(cache_key, result.output, ttl=ttl)
        self._optimizer.update(
            Outcome(
                module=decision.module,
                version=decision.version,
                score=result.score,
                latency_ms=result.latency_ms,
                success=result.success,
            )
        )
        return result.output

    def _is_cacheable(self, task_type: str) -> bool:
        ttl = CACHEABLE_TASKS.get(task_type)
        return ttl is not None and ttl > 0


__all__ = ["WorkerRunner", "ExecutionResult", "RateLimitExceededError"]
