"""API routes exposing distributed cluster controls."""
from __future__ import annotations

from fastapi import APIRouter

from genesis.cluster.node import router as cluster_router

router: APIRouter = cluster_router
