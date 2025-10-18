import asyncio
from starlette.requests import Request

from genesis.api.routes.health import healthz, readyz


async def _request_for_app(app):
    async def receive() -> dict:
        return {"type": "http.request"}

    scope = {"type": "http", "app": app, "method": "GET", "path": "/readyz"}
    return Request(scope, receive)


def test_healthz():
    result = asyncio.get_event_loop().run_until_complete(healthz())
    assert result["status"] == "ok"


def test_readyz(app):
    request = asyncio.get_event_loop().run_until_complete(_request_for_app(app))
    result = asyncio.get_event_loop().run_until_complete(readyz(request))
    assert result["status"] == "ok"
