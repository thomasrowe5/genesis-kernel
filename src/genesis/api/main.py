"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from redis.asyncio import Redis

from ..config import get_settings
from ..db import init_db
from ..logging import configure_logging
from ..metrics import setup_metrics
from ..queues.broker import InMemoryBroker, RedisBroker
from .routes import health, jobs, stats


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    init_db()
    app = FastAPI(title="Genesis Kernel", version="0.1.0")
    if settings.environment == "test":
        broker = InMemoryBroker()
    else:
        broker = RedisBroker(Redis.from_url(settings.redis_url, decode_responses=False))
    app.state.broker = broker
    app.state.settings = settings
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(stats.router)
    setup_metrics(app)
    return app


app = create_app()
