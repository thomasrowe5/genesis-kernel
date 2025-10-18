"""Database helpers for creating SQLModel engines and sessions."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, create_engine
except Exception:  # pragma: no cover - fallback when SQLModel unavailable
    Session = None  # type: ignore[assignment]

    def create_engine(*args, **kwargs):  # type: ignore[override]
        raise RuntimeError("SQLModel is not available in this environment")


from genesis.core.config import get_settings
from genesis.utils.retry import RetryPolicy, retry


_ENGINE_CACHE: Dict[Any, Any] = {}


@retry(RetryPolicy(attempts=3, backoff_factor=0.2, max_backoff=1.0), operation="db_engine_create")
def _create_engine(url: str, connect_args: Dict[str, Any], engine_kwargs: Dict[str, Any]):
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def get_engine(database_url: str | None = None):
    settings = get_settings()
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine_kwargs: Dict[str, Any] = {}
    if not url.startswith("sqlite"):
        engine_kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10)
    cache_key = (url, tuple(sorted(engine_kwargs.items())))
    if cache_key not in _ENGINE_CACHE:
        _ENGINE_CACHE[cache_key] = _create_engine(url, connect_args, engine_kwargs)
    return _ENGINE_CACHE[cache_key]


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    if Session is None:  # pragma: no cover - requires SQLModel
        raise RuntimeError("Session management requires SQLModel")
    engine = get_engine(database_url=database_url)
    with Session(engine) as session:
        yield session
