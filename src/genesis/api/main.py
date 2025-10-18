"""Unified FastAPI gateway exposing Genesis subsystems."""
from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from genesis.api.routes import (
    cache,
    cluster,
    cognition,
    cosmic,
    federation,
    metanet,
    modules,
    orchestration,
    provenance,
    reflexion,
    temporal,
)
from genesis.core import configure_logging, get_settings
from genesis.governance.rbac import require_role


DOMAIN_ROUTERS: dict[str, list[APIRouter]] = {
    "core": [modules.router, cache.router],
    "cognition": [cognition.router],
    "reflexion": [reflexion.router],
    "temporal": [temporal.router],
    "governance": [provenance.router],
    "router": [orchestration.router, federation.router],
    "cosmic": [cosmic.router, metanet.router, cluster.router],
}


def _apply_domain_routes(app: FastAPI) -> None:
    for domain, routers in DOMAIN_ROUTERS.items():
        for router in routers:
            app.include_router(router, prefix=f"/{domain}")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.logging)

    app = FastAPI(
        title="Genesis Unified API",
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    _apply_domain_routes(app)

    @app.get("/health/live", tags=["health"], dependencies=[Depends(require_role("viewer"))])
    async def liveness() -> dict[str, str]:
        return {"status": "alive", "environment": settings.environment}

    @app.get("/health/ready", tags=["health"], dependencies=[Depends(require_role("viewer"))])
    async def readiness() -> dict[str, str]:
        return {
            "status": "ready",
            "database": settings.database_url,
            "redis": settings.redis_url,
        }

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        excluded_handlers={"/health/live", "/health/ready"},
    )
    instrumentator.instrument(app).expose(app, include_in_schema=False)

    return app


app = create_app()
