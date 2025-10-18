"""Distributed cluster services for Genesis."""
from .config import ClusterConfig, PeerConfig
from .scheduler import ConsistentHashScheduler

try:  # pragma: no cover - optional FastAPI dependency
    from .node import ClusterNodeService
except ModuleNotFoundError as exc:  # pragma: no cover - optional FastAPI dependency
    if exc.name != "fastapi":
        raise
    ClusterNodeService = None  # type: ignore[assignment]

__all__ = [
    "ClusterConfig",
    "PeerConfig",
    "ClusterNodeService",
    "ConsistentHashScheduler",
]
