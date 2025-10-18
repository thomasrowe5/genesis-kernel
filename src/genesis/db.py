"""Database helpers for creating SQLModel engines and sessions."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, create_engine
except Exception:  # pragma: no cover - fallback when SQLModel unavailable
    Session = None  # type: ignore[assignment]

    def create_engine(*args, **kwargs):  # type: ignore[override]
        raise RuntimeError("SQLModel is not available in this environment")


from genesis.core.config import get_settings


def get_engine(database_url: str | None = None):
    settings = get_settings()
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    if Session is None:  # pragma: no cover - requires SQLModel
        raise RuntimeError("Session management requires SQLModel")
    engine = get_engine(database_url=database_url)
    with Session(engine) as session:
        yield session
