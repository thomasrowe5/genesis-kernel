import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from genesis.api.main import create_app
from genesis.config import get_settings
from genesis.db import init_db, reset_engine


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def configure_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("GENESIS_ENVIRONMENT", "test")
    monkeypatch.setenv("GENESIS_DB_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("GENESIS_REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    reset_engine()
    init_db()
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]
    reset_engine()


@pytest.fixture
async def app() -> AsyncGenerator:
    application = create_app()
    yield application
