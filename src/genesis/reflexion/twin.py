"""Digital twin builder mirroring the Genesis runtime state."""
from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional

from genesis.metrics import genesis_reflexive_cycles_total, genesis_twin_sync_latency_seconds
from genesis.registry.manager import ModuleRegistryManager
from genesis.utils.json_utils import canonical_dumps
from genesis.utils.pydantic_compat import BaseModel

from .models import SQLMODEL_AVAILABLE, TwinSnapshot

StateProvider = Callable[[], Mapping[str, Any]]


class TwinState(BaseModel):
    """Serializable view of the current Genesis digital twin."""

    at: datetime
    topology: dict[str, Any]
    metrics: dict[str, float]
    config: dict[str, Any]

    class Config:
        frozen = True


@dataclass(slots=True)
class TwinPersistence:
    """Persist twin snapshots either in SQLModel or in-memory."""

    session_factory: Optional[Callable[[], Any]] = None
    _records: list[TwinSnapshot] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._records is None:
            self._records = []

    def store(self, snapshot: TwinSnapshot) -> None:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                session.add(snapshot)
                session.commit()
                session.refresh(snapshot)
        else:
            self._records.append(snapshot)

    def recent(self, limit: int = 10) -> list[TwinSnapshot]:
        if SQLMODEL_AVAILABLE and self.session_factory is not None:
            from sqlmodel import Session, select  # type: ignore

            with self.session_factory() as session:  # type: ignore[attr-defined]
                assert isinstance(session, Session)
                statement = select(TwinSnapshot).order_by(TwinSnapshot.at.desc()).limit(limit)
                return list(session.exec(statement))
        return list(self._records[-limit:])


class DigitalTwinBuilder:
    """Construct a consistent digital twin for the Genesis kernel."""

    def __init__(
        self,
        registry: ModuleRegistryManager,
        *,
        topology_providers: Optional[Iterable[StateProvider]] = None,
        metrics_providers: Optional[Iterable[StateProvider]] = None,
        config_providers: Optional[Iterable[StateProvider]] = None,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._registry = registry
        self._topology_providers = tuple(topology_providers or ())
        self._metrics_providers = tuple(metrics_providers or ())
        self._config_providers = tuple(config_providers or ())
        self._persistence = TwinPersistence(session_factory=session_factory)

    async def build_snapshot(self) -> TwinState:
        start = time.perf_counter()
        modules = self._registry.leaderboard(limit=100)
        modules_sorted = sorted(modules, key=lambda m: (m["name"], m["version"]))
        topology: MutableMapping[str, Any] = {"modules": modules_sorted}
        metrics: MutableMapping[str, float] = {}
        active_config: MutableMapping[str, Any] = {"active": {}}

        for module in modules_sorted:
            key = f"{module['name']}:{module['version']}"
            metrics[key] = float(module.get("score", 0.0))
            if module.get("active"):
                active_config["active"][module["name"]] = module["version"]

        self._merge_state(topology, self._topology_providers)
        self._merge_state(metrics, self._metrics_providers)
        self._merge_state(active_config, self._config_providers)

        state = TwinState(
            at=datetime.utcnow(),
            topology=json.loads(canonical_dumps(topology, default=str)),
            metrics={k: float(v) for k, v in metrics.items()},
            config=json.loads(canonical_dumps(active_config, default=str)),
        )
        self._persist(state)
        duration = time.perf_counter() - start
        genesis_reflexive_cycles_total.inc()
        genesis_twin_sync_latency_seconds.observe(duration)
        return state

    def recent_snapshots(self, limit: int = 5) -> list[TwinState]:
        records = self._persistence.recent(limit=limit)
        return [
            TwinState(at=record.at, topology=record.topology_json, metrics=record.metrics_json, config=record.config_json)
            for record in records
        ]

    def _persist(self, state: TwinState) -> None:
        snapshot = TwinSnapshot(topology_json=state.topology, metrics_json=state.metrics, config_json=state.config, at=state.at)
        self._persistence.store(snapshot)

    @staticmethod
    def _merge_state(target: MutableMapping[str, Any], providers: Iterable[StateProvider]) -> None:
        for provider in providers:
            data = provider()
            for key, value in data.items():
                if isinstance(target.get(key), Mapping) and isinstance(value, Mapping):
                    merged = deepcopy(target[key])
                    merged.update(value)
                    target[key] = merged
                else:
                    target[key] = value
