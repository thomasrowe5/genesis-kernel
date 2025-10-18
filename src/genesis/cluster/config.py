"""Configuration helpers for Genesis distributed cluster nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

import json
import os


@dataclass(frozen=True)
class PeerConfig:
    """Representation of a peer entry in the cluster topology."""

    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class ClusterConfig:
    """Runtime configuration passed to :class:`ClusterNodeService`."""

    node_id: str
    host: str
    port: int
    peers: List[PeerConfig] = field(default_factory=list)
    heartbeat_interval: float = 5.0
    heartbeat_timeout: float = 15.0

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> "ClusterConfig":
        """Create a configuration object using environment variables."""

        node_id = os.getenv("GENESIS_CLUSTER_NODE_ID", "node-0")
        host = os.getenv("GENESIS_CLUSTER_HOST", "127.0.0.1")
        port = int(os.getenv("GENESIS_CLUSTER_PORT", "8080"))
        heartbeat_interval = float(os.getenv("GENESIS_CLUSTER_HEARTBEAT_INTERVAL", "5"))
        heartbeat_timeout = float(os.getenv("GENESIS_CLUSTER_HEARTBEAT_TIMEOUT", "15"))
        peers_raw = os.getenv("GENESIS_CLUSTER_PEERS", "")
        peers = [
            PeerConfig(host=entry.split(":")[0], port=int(entry.split(":")[1]))
            for entry in peers_raw.split(",")
            if entry
        ]
        return cls(
            node_id=node_id,
            host=host,
            port=port,
            peers=peers,
            heartbeat_interval=heartbeat_interval,
            heartbeat_timeout=heartbeat_timeout,
        )

    @classmethod
    def from_file(cls, path: Path) -> "ClusterConfig":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        peers = [PeerConfig(**peer) for peer in payload.get("peers", [])]
        return cls(
            node_id=payload["node_id"],
            host=payload["host"],
            port=int(payload["port"]),
            peers=peers,
            heartbeat_interval=float(payload.get("heartbeat_interval", 5.0)),
            heartbeat_timeout=float(payload.get("heartbeat_timeout", 15.0)),
        )

    def peer_urls(self) -> Sequence[str]:
        return [peer.url for peer in self.peers]

    def with_peers(self, peers: Iterable[PeerConfig]) -> "ClusterConfig":
        self.peers = list(peers)
        return self
