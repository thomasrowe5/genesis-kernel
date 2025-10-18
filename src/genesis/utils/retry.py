"""Retry utilities with exponential backoff and circuit breaking."""
from __future__ import annotations

import asyncio
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterator, Optional, Tuple, TypeVar

from genesis.metrics import genesis_retry_total
from genesis.utils.context import log_context

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 5.0
    jitter: float = 0.1
    retry_exceptions: Tuple[type[BaseException], ...] = (Exception,)
    give_up_exceptions: Tuple[type[BaseException], ...] = ()
    circuit_threshold: int = 5
    circuit_reset_seconds: float = 30.0


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open."""


class _CircuitBreaker:
    def __init__(self, threshold: int, reset_seconds: float) -> None:
        self._threshold = threshold
        self._reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: Optional[float] = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def check(self) -> None:
        if self._opened_at is None:
            return
        if time.monotonic() - self._opened_at >= self._reset_seconds:
            self._failures = 0
            self._opened_at = None
            return
        raise CircuitBreakerOpenError("circuit breaker open")


def _compute_backoff(attempt: int, policy: RetryPolicy) -> float:
    base = min(policy.max_backoff, policy.backoff_factor * (2 ** (attempt - 1)))
    if policy.jitter:
        base += random.uniform(-policy.jitter, policy.jitter)
    return max(0.0, base)


@contextmanager
def _retry_context(operation: str, attempt: int, reason: str | None = None) -> Iterator[None]:
    with log_context(retry_operation=operation, retry_attempt=attempt, retry_reason=reason):
        yield


def _handle_failure(operation: str, reason: str | None) -> None:
    genesis_retry_total.labels(operation=operation, reason=reason or "unknown").inc()


def retry(policy: RetryPolicy | None = None, *, operation: str = "operation") -> Callable[[Callable[..., T]], Callable[..., T]]:
    policy = policy or RetryPolicy()
    breaker = _CircuitBreaker(policy.circuit_threshold, policy.circuit_reset_seconds)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            breaker.check()
            attempt = 1
            while True:
                try:
                    with _retry_context(operation, attempt):
                        result = func(*args, **kwargs)
                except policy.give_up_exceptions as exc:
                    _handle_failure(operation, exc.__class__.__name__)
                    raise
                except policy.retry_exceptions as exc:  # type: ignore[misc]
                    breaker.record_failure()
                    _handle_failure(operation, exc.__class__.__name__)
                    if attempt >= policy.attempts:
                        raise
                    sleep_for = _compute_backoff(attempt, policy)
                    time.sleep(sleep_for)
                    attempt += 1
                    continue
                breaker.record_success()
                return result

        return wrapper

    return decorator


def retry_async(policy: RetryPolicy | None = None, *, operation: str = "operation") -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    policy = policy or RetryPolicy()
    breaker = _CircuitBreaker(policy.circuit_threshold, policy.circuit_reset_seconds)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            breaker.check()
            attempt = 1
            while True:
                try:
                    with _retry_context(operation, attempt):
                        result = await func(*args, **kwargs)
                except policy.give_up_exceptions as exc:
                    _handle_failure(operation, exc.__class__.__name__)
                    raise
                except policy.retry_exceptions as exc:  # type: ignore[misc]
                    breaker.record_failure()
                    _handle_failure(operation, exc.__class__.__name__)
                    if attempt >= policy.attempts:
                        raise
                    sleep_for = _compute_backoff(attempt, policy)
                    await asyncio.sleep(sleep_for)
                    attempt += 1
                    continue
                breaker.record_success()
                return result

        return wrapper

    return decorator

