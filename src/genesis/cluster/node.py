"""Cluster node service exposing FastAPI and gossip capabilities."""
from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from genesis.cluster.config import ClusterConfig
from genesis.cluster.registry_sync import ModuleVersionPayload, RegistrySnapshot, RegistrySyncClient
from genesis.cluster.scheduler import ConsistentHashScheduler, SchedulerAssignment
from genesis.metrics import (
    genesis_cluster_heartbeat_lag_seconds,
    genesis_cluster_nodes_total,
    genesis_policy_violations_total,
    genesis_replay_runs_total,
    genesis_signature_verifications_total,
)
from genesis.provenance.replay import ReplayEngine, ReplayRequest


@dataclass
class HeartbeatState:
    node_id: str
    last_seen: dt.datetime
    status: str = "unknown"


class ClusterHealth(BaseModel):
    node_id: str
    status: str
    last_seen: dt.datetime
    is_leader: bool


class ClusterMetrics(BaseModel):
    nodes: int
    metrics: Mapping[str, Any]


class ReplayPayload(BaseModel):
    experiment_id: str


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


@dataclass
class RustClusterCore:
    """Small Python stand-in for the Rust heartbeat core."""

    heartbeat_interval: float
    heartbeat_timeout: float
    state: MutableMapping[str, HeartbeatState] = field(default_factory=dict)

    def register_node(self, node_id: str) -> None:
        self.state[node_id] = HeartbeatState(node_id=node_id, last_seen=_utcnow(), status="ready")

    def heartbeat(self, node_id: str) -> None:
        heartbeat = self.state.setdefault(node_id, HeartbeatState(node_id=node_id, last_seen=_utcnow()))
        heartbeat.last_seen = _utcnow()
        heartbeat.status = "ready"

    def mark_failed(self, node_id: str) -> None:
        heartbeat = self.state.get(node_id)
        if heartbeat:
            heartbeat.status = "failed"

    def quorum(self) -> List[HeartbeatState]:
        return list(self.state.values())


class ClusterNodeService:
    """Coordinates cluster metadata and exposes API endpoints."""

    def __init__(
        self,
        config: ClusterConfig,
        scheduler: Optional[ConsistentHashScheduler] = None,
        registry_snapshot: Optional[RegistrySnapshot] = None,
        replay_engine: Optional[ReplayEngine] = None,
    ) -> None:
        self.config = config
        self.scheduler = scheduler or ConsistentHashScheduler()
        self.registry_snapshot = registry_snapshot or RegistrySnapshot()
        self.replay_engine = replay_engine or ReplayEngine()
        self._router = APIRouter(prefix="/cluster", tags=["cluster"])
        self._heartbeats = RustClusterCore(
            heartbeat_interval=config.heartbeat_interval,
            heartbeat_timeout=config.heartbeat_timeout,
        )
        self._sync_client = RegistrySyncClient(config.peer_urls())
        self._peers: List[str] = list(config.peer_urls())
        self._leader_id: Optional[str] = None
        self._background_tasks: List[asyncio.Task[Any]] = []
        self._register_routes()
        self._initialise()

    def _initialise(self) -> None:
        self._heartbeats.register_node(self.config.node_id)
        self._leader_id = self.config.node_id
        self.scheduler.configure([SchedulerAssignment(node_id=self.config.node_id, weight=1.0)])
        genesis_cluster_nodes_total.set_function(lambda: len(self.scheduler.nodes()))

    def _register_routes(self) -> None:
        router = self._router

        @router.get("/nodes", response_model=List[ClusterHealth])
        def list_nodes() -> List[ClusterHealth]:
            data = []
            for heartbeat in self._heartbeats.quorum():
                lag_seconds = (_utcnow() - heartbeat.last_seen).total_seconds()
                genesis_cluster_heartbeat_lag_seconds.labels(node_id=heartbeat.node_id).set(lag_seconds)
                data.append(
                    ClusterHealth(
                        node_id=heartbeat.node_id,
                        status=heartbeat.status,
                        last_seen=heartbeat.last_seen,
                        is_leader=heartbeat.node_id == self._leader_id,
                    )
                )
            return data

        @router.get("/health", response_model=ClusterHealth)
        def get_health() -> ClusterHealth:
            heartbeat = self._heartbeats.state.get(self.config.node_id)
            if heartbeat is None:
                raise HTTPException(status_code=404, detail="Node heartbeat unknown")
            return ClusterHealth(
                node_id=heartbeat.node_id,
                status=heartbeat.status,
                last_seen=heartbeat.last_seen,
                is_leader=heartbeat.node_id == self._leader_id,
            )

        @router.post("/sync")
        async def sync(payload: Dict[str, Any]) -> Dict[str, Any]:
            topic = payload.get("topic")
            message = payload.get("payload", {})
            if topic == "module":
                module_payload = ModuleVersionPayload(**message)
                self.registry_snapshot.apply_version(module_payload)
            elif topic == "metrics":
                self.registry_snapshot.apply_metrics(message)
            elif topic == "heartbeat":
                node_id = message["node_id"]
                self._heartbeats.heartbeat(node_id)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown sync topic {topic}")
            return {"status": "ok"}

        @router.get("/metrics", response_model=ClusterMetrics)
        def metrics() -> ClusterMetrics:
            snapshot = self.registry_snapshot.summary()
            return ClusterMetrics(nodes=len(self.scheduler.nodes()), metrics=snapshot["metrics"])

        @router.post("/replay")
        async def trigger_replay(request: ReplayPayload) -> Dict[str, Any]:
            replay_request = ReplayRequest(experiment_id=request.experiment_id)
            result = await self.replay_engine.replay(replay_request)
            genesis_replay_runs_total.inc()
            return {"status": "ok", "result_hash": result.output_hash}

    @property
    def router(self) -> APIRouter:
        return self._router

    def sync_loop(self, payload_supplier: callable, interval: float) -> None:
        async def _loop() -> None:
            while True:
                payloads: Iterable[ModuleVersionPayload] = payload_supplier()
                for payload in payloads:
                    await self._sync_client.broadcast_version(payload)
                await asyncio.sleep(interval)

        self._background_tasks.append(asyncio.create_task(_loop()))

    def update_peers(self, peers: Iterable[str]) -> None:
        self._sync_client.update_peers(peers)
        self._peers = list(peers)

    def peers(self) -> List[str]:
        return list(self._peers)

    def health_snapshot(self) -> List[HeartbeatState]:
        return self._heartbeats.quorum()

    def record_policy_violation(self) -> None:
        genesis_policy_violations_total.inc()

    def record_signature_verification(self, success: bool) -> None:
        if success:
            genesis_signature_verifications_total.labels(status="success").inc()
        else:
            genesis_signature_verifications_total.labels(status="failed").inc()


def cluster_service_dependency() -> ClusterNodeService:
    """FastAPI dependency placeholder used by routers."""

    return _default_service


_default_service = ClusterNodeService(config=ClusterConfig.from_env())
router = _default_service.router
