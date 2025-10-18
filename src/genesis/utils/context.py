"""Context helpers for structured logging and tracing."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator


_log_context: ContextVar[Dict[str, Any]] = ContextVar("genesis_log_context", default={})


def get_log_context() -> Dict[str, Any]:
    """Return a copy of the current logging context."""

    return dict(_log_context.get())


@contextmanager
def log_context(**overrides: Any) -> Iterator[None]:
    """Temporarily merge overrides into the structured log context."""

    current = get_log_context()
    next_context = {**current}
    next_context.update({k: v for k, v in overrides.items() if v is not None})
    token = _log_context.set(next_context)
    try:
        yield
    finally:
        _log_context.reset(token)


def clear_log_context() -> None:
    """Reset the structured log context."""

    _log_context.set({})

