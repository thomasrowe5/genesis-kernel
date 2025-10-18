"""Unified FastAPI gateway exposing Genesis subsystems."""
from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
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
from genesis.metrics import genesis_api_latency_seconds, update_uptime_metric
from genesis.utils.context import log_context
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


class _MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, excluded_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._excluded_paths = excluded_paths or set()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        path = request.url.path
        if path in self._excluded_paths:
            response = await call_next(request)
            update_uptime_metric()
            return response

        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        method = request.method
        start = time.perf_counter()
        with log_context(trace_id=trace_id, http_method=method, http_route=path):
            response = await call_next(request)
            status = response.status_code
        elapsed = time.perf_counter() - start
        genesis_api_latency_seconds.labels(
            route=path,
            method=method,
            status=str(status),
        ).observe(elapsed)
        uptime = update_uptime_metric()
        response.headers["x-trace-id"] = trace_id
        response.headers["x-genesis-uptime"] = f"{uptime:.3f}"
        return response


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
    app.add_middleware(
        _MetricsMiddleware,
        excluded_paths={"/metrics", "/health/live", "/health/ready"},
    )

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
