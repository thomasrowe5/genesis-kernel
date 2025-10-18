"""Distributed scheduling primitives for Genesis."""
from __future__ import annotations

import bisect
import hashlib
import threading
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Tuple


@dataclass(frozen=True)
class SchedulerAssignment:
    node_id: str
    weight: float


class ConsistentHashScheduler:
    """Simple consistent hashing scheduler for assigning work to nodes."""

    def __init__(self, replicas: int = 100) -> None:
        self._replicas = max(1, replicas)
        self._ring: List[Tuple[int, str]] = []
        self._node_weights: Mapping[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return int(digest, 16)

    def configure(self, assignments: Iterable[SchedulerAssignment]) -> None:
        with self._lock:
            self._ring = []
            self._node_weights = {assignment.node_id: assignment.weight for assignment in assignments}
            for assignment in assignments:
                for replica in range(self._replicas):
                    key = f"{assignment.node_id}:{replica}"
                    position = self._hash(key)
                    self._ring.append((position, assignment.node_id))
            self._ring.sort(key=lambda item: item[0])

    def nodes(self) -> List[str]:
        with self._lock:
            return sorted(set(node for _, node in self._ring))

    def assign(self, key: str) -> str:
        with self._lock:
            if not self._ring:
                raise RuntimeError("ConsistentHashScheduler has no nodes configured")
            position = self._hash(key)
            index = bisect.bisect(self._ring, (position, ""))
            if index == len(self._ring):
                index = 0
            return self._ring[index][1]

    def rebalance(self, failed_node_id: str) -> None:
        with self._lock:
            self._ring = [(pos, node) for pos, node in self._ring if node != failed_node_id]

    def describe(self) -> List[Tuple[int, str]]:
        with self._lock:
            return list(self._ring)
