"""Registry manager supporting both SQLModel and in-memory backends."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, SQLModel, select
except Exception:  # pragma: no cover - fallback when SQLModel unavailable
    Session = None  # type: ignore[assignment]
    SQLModel = None  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

from genesis.metrics import (
    genesis_canary_promotions_total,
    genesis_canary_rollbacks_total,
    genesis_module_score,
    genesis_replacements_total,
    genesis_rl_reward,
    genesis_rl_update_total,
    genesis_traffic_share,
)

from .models import Event, ModuleVersion, OrchestrationEvent, SQLMODEL_AVAILABLE


class ModuleRegistryManager:
    """Encapsulates registry operations with transparent backend selection."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session
        if not SQLMODEL_AVAILABLE:
            self._modules: List[ModuleVersion] = []
            self._events: List[Event] = []
            self._orch_events: List[OrchestrationEvent] = []
            self._next_module_id = 1
            self._next_event_id = 1
            self._next_orch_event_id = 1

    @property
    def session(self) -> Optional[Session]:
        return self._session

    def register_version(
        self,
        name: str,
        version: str,
        path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModuleVersion:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            existing = self._session.exec(
                select(ModuleVersion).where(ModuleVersion.name == name, ModuleVersion.version == version)
            ).first()
            if existing:
                return existing
            module_version = ModuleVersion(
                name=name,
                version=version,
                path=path,
                params_json={},
                metadata_json=metadata or {},
            )
            self._session.add(module_version)
            self._session.commit()
            self._session.refresh(module_version)
            return module_version

        for module in self._modules:
            if module.name == name and module.version == version:
                return module
        module_version = ModuleVersion(
            id=self._next_module_id,
            name=name,
            version=version,
            path=path,
            params_json={},
            metadata_json=metadata or {},
        )
        self._next_module_id += 1
        self._modules.append(module_version)
        return module_version

    def get_version(self, name: str, version: str) -> Optional[ModuleVersion]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            return self._session.exec(
                select(ModuleVersion).where(ModuleVersion.name == name, ModuleVersion.version == version)
            ).first()
        return next((m for m in self._modules if m.name == name and m.version == version), None)

    def get_active_version(self, name: str) -> Optional[ModuleVersion]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            return self._session.exec(
                select(ModuleVersion).where(ModuleVersion.name == name, ModuleVersion.active.is_(True))
            ).first()
        return next((m for m in self._modules if m.name == name and m.active), None)

    def record_metrics(
        self,
        module_version: ModuleVersion,
        score: float,
        metrics: Dict[str, float],
    ) -> ModuleVersion:
        module_version.score = score
        module_version.metadata_json.setdefault("metrics", {}).update(metrics)
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            self._session.add(module_version)
            self._session.commit()
            self._session.refresh(module_version)
        genesis_module_score.labels(module_version.name, module_version.version).set(score)
        return module_version

    def activate_version(self, module_version: ModuleVersion) -> None:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            active_variants = self._session.exec(
                select(ModuleVersion).where(ModuleVersion.name == module_version.name, ModuleVersion.active.is_(True))
            ).all()
            for variant in active_variants:
                if variant.id == module_version.id:
                    continue
                variant.active = False
                variant.traffic_share = 0.0
                self._session.add(variant)
            module_version.active = True
            module_version.traffic_share = 1.0
            self._session.add(module_version)
            self._session.commit()
            self._session.refresh(module_version)
            self._emit_shares(module_version.name)
            return

        for variant in self._modules:
            if variant.name == module_version.name:
                variant.active = variant.id == module_version.id
                variant.traffic_share = 1.0 if variant.active else 0.0
        self._emit_shares(module_version.name)

    def select_best(self, name: str, limit: int = 1) -> List[ModuleVersion]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            statement = (
                select(ModuleVersion)
                .where(ModuleVersion.name == name)
                .order_by(ModuleVersion.score.desc())
                .limit(limit)
            )
            return list(self._session.exec(statement))
        candidates = [m for m in self._modules if m.name == name]
        return sorted(candidates, key=lambda mv: mv.score, reverse=True)[:limit]

    def select_active_versions(self, name: str) -> List[ModuleVersion]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            statement = select(ModuleVersion).where(
                ModuleVersion.name == name, ModuleVersion.traffic_share > 0.0
            )
            return list(self._session.exec(statement))
        return [m for m in self._modules if m.name == name and m.traffic_share > 0.0]

    def record_replacement(self, module_version: ModuleVersion, previous_version: Optional[ModuleVersion]) -> Event:
        payload: Dict[str, Any] = {
            "new_version": module_version.version,
            "new_score": module_version.score,
        }
        if previous_version is not None:
            payload["previous_version"] = previous_version.version
            payload["previous_score"] = previous_version.score

        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            event = Event(event_type="module_replacement", module_name=module_version.name, payload=payload)
            self._session.add(event)
            self._session.commit()
            self._session.refresh(event)
        else:
            event = Event(
                id=self._next_event_id,
                event_type="module_replacement",
                module_name=module_version.name,
                payload=payload,
            )
            self._next_event_id += 1
            self._events.append(event)
        genesis_replacements_total.inc()
        return event

    # --- Orchestration helpers -------------------------------------------------

    def _record_orch_event(
        self, module: str, version: str, event_type: str, payload: Optional[Dict[str, Any]] = None
    ) -> OrchestrationEvent:
        data = payload or {}
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            event = OrchestrationEvent(module=module, version=version, type=event_type, data_json=data)
            self._session.add(event)
            self._session.commit()
            self._session.refresh(event)
            return event
        event = OrchestrationEvent(
            id=self._next_orch_event_id,
            module=module,
            version=version,
            type=event_type,
            data_json=data,
        )
        self._next_orch_event_id += 1
        self._orch_events.append(event)
        return event

    def start_canary(
        self,
        name: str,
        candidate_version: str,
        initial_share: float,
    ) -> ModuleVersion:
        baseline = self.get_active_version(name)
        candidate = self.get_version(name, candidate_version)
        if candidate is None:
            raise ValueError(f"Unknown candidate version {candidate_version} for module {name}")
        if baseline is None:
            raise ValueError(f"No baseline active version for module {name}")
        if candidate.id == baseline.id:
            raise ValueError("Candidate is already the active version")
        candidate.canary = True
        candidate.traffic_share = max(0.0, min(initial_share, 1.0))
        baseline.traffic_share = max(0.0, 1.0 - candidate.traffic_share)
        self._persist([candidate, baseline])
        self._record_orch_event(name, candidate_version, "canary_start", {"share": candidate.traffic_share})
        self._emit_shares(name)
        return candidate

    def set_traffic_splits(self, name: str, splits: Mapping[str, float]) -> List[ModuleVersion]:
        updated: List[ModuleVersion] = []
        for version, share in splits.items():
            module_version = self.get_version(name, version)
            if module_version is None:
                raise ValueError(f"Unknown version {version} for module {name}")
            module_version.traffic_share = max(0.0, share)
            updated.append(module_version)
        self._persist(updated)
        self._emit_shares(name)
        self._record_orch_event(name, "*", "traffic_split", {"splits": dict(splits)})
        return updated

    def finalize_promotion(self, name: str, version: str) -> ModuleVersion:
        candidate = self.get_version(name, version)
        if candidate is None:
            raise ValueError(f"Unknown version {version} for module {name}")
        previous_active = self.get_active_version(name)
        if previous_active and previous_active.version == version:
            return candidate
        candidate.active = True
        candidate.canary = False
        candidate.traffic_share = 1.0
        self._persist([candidate])
        others = [m for m in self._iter_versions(name) if m.version != version]
        for other in others:
            other.active = False
            other.canary = False
            other.traffic_share = 0.0
        self._persist(others)
        genesis_canary_promotions_total.labels(name, version).inc()
        self._record_orch_event(name, version, "promotion", {})
        self._emit_shares(name)
        return candidate

    def rollback(self, name: str, version: str, reason: str) -> ModuleVersion:
        target = self.get_version(name, version)
        if target is None:
            raise ValueError(f"Unknown version {version} for module {name}")
        target.canary = False
        target.traffic_share = 0.0
        self._persist([target])
        baseline = self.get_active_version(name)
        if baseline:
            baseline.traffic_share = 1.0
            self._persist([baseline])
        genesis_canary_rollbacks_total.labels(name, version, reason).inc()
        self._record_orch_event(name, version, "rollback", {"reason": reason})
        self._emit_shares(name)
        return target

    def update_online_metrics(
        self,
        name: str,
        version: str,
        *,
        reward: float,
        latency_ms: float,
        ok: bool,
    ) -> ModuleVersion:
        module = self.get_version(name, version)
        if module is None:
            raise ValueError(f"Unknown version {version} for module {name}")
        alpha = 0.2
        module.reward_ma = (1 - alpha) * module.reward_ma + alpha * reward
        module.p95_ms = (1 - alpha) * module.p95_ms + alpha * latency_ms
        failure = 0.0 if ok else 1.0
        module.error_rate = (1 - alpha) * module.error_rate + alpha * failure
        self._persist([module])
        genesis_rl_reward.labels(name, version).set(module.reward_ma)
        genesis_rl_update_total.inc()
        self._record_orch_event(
            name,
            version,
            "online_update",
            {"reward": reward, "latency_ms": latency_ms, "ok": ok},
        )
        return module

    def update_params(self, name: str, version: str, params: Dict[str, Any]) -> ModuleVersion:
        module = self.get_version(name, version)
        if module is None:
            raise ValueError(f"Unknown version {version} for module {name}")
        module.params_json = params
        self._persist([module])
        self._record_orch_event(name, version, "param_update", {"params": params})
        return module

    # --- Helpers ----------------------------------------------------------------

    def _persist(self, modules: Iterable[ModuleVersion]) -> None:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            for module in modules:
                self._session.add(module)
            self._session.commit()
            for module in modules:
                self._session.refresh(module)

    def _iter_versions(self, name: str) -> Iterable[ModuleVersion]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            statement = select(ModuleVersion).where(ModuleVersion.name == name)
            yield from self._session.exec(statement)
        else:
            yield from (m for m in self._modules if m.name == name)

    def _emit_shares(self, name: str) -> None:
        for module in self._iter_versions(name):
            genesis_traffic_share.labels(module.name, module.version).set(module.traffic_share)

    def versions(self, name: str) -> List[ModuleVersion]:
        return list(self._iter_versions(name))

    def leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        if SQLMODEL_AVAILABLE:
            if self._session is None:
                raise RuntimeError("SQLModel backend requires a database session")
            statement = select(ModuleVersion).order_by(ModuleVersion.score.desc()).limit(limit)
            records = self._session.exec(statement)
        else:
            records = sorted(self._modules, key=lambda mv: mv.score, reverse=True)[:limit]
        return [
            {
                "name": module.name,
                "version": module.version,
                "score": module.score,
                "active": module.active,
                "path": module.path,
            }
            for module in records
        ]

    @staticmethod
    def create_all(engine: Any) -> None:  # pragma: no cover - integration hook
        if SQLMODEL_AVAILABLE and SQLModel is not None and engine is not None:
            SQLModel.metadata.create_all(engine)
