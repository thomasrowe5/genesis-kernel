"""Registry manager supporting both SQLModel and in-memory backends."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency path
    from sqlmodel import Session, SQLModel, select
except Exception:  # pragma: no cover - fallback when SQLModel unavailable
    Session = None  # type: ignore[assignment]
    SQLModel = None  # type: ignore[assignment]
    select = None  # type: ignore[assignment]

from genesis.metrics import genesis_module_score, genesis_replacements_total

from .models import Event, ModuleVersion, SQLMODEL_AVAILABLE


class ModuleRegistryManager:
    """Encapsulates registry operations with transparent backend selection."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session
        if not SQLMODEL_AVAILABLE:
            self._modules: List[ModuleVersion] = []
            self._events: List[Event] = []
            self._next_module_id = 1
            self._next_event_id = 1

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
            module_version = ModuleVersion(name=name, version=version, path=path, metadata_json=metadata or {})
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
                self._session.add(variant)
            module_version.active = True
            self._session.add(module_version)
            self._session.commit()
            self._session.refresh(module_version)
            return

        for variant in self._modules:
            if variant.name == module_version.name:
                variant.active = variant.id == module_version.id

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
