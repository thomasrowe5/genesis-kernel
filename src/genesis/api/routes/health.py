"""Health endpoints."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import text

from ...db import get_session

router = APIRouter()


async def _check_db() -> bool:
    def _ping() -> bool:
        with get_session() as session:
            session.exec(text("SELECT 1"))
        return True

    return await asyncio.to_thread(_ping)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    ok_db = await _check_db()
    broker = request.app.state.broker
    try:
        depth = await broker.depth()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "db": str(ok_db), "queue_depth": str(depth)}
