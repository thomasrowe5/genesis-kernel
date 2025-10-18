"""Configuration helpers consolidating environment and runtime settings."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from genesis.utils.context import get_log_context


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_DEFAULT_BENCHMARKS_DIR = Path("benchmarks")
_DEFAULT_DOCS_BUILD_DIR = Path("site")


@dataclass(frozen=True)
class LoggingSettings:
    level: str = "INFO"
    json_enabled: bool = True
    service_name: str = "genesis"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "LoggingSettings":
        return cls(
            level=env.get("GENESIS_LOGGING_LEVEL", cls.level),
            json_enabled=_parse_bool(env.get("GENESIS_LOGGING_JSON"), cls.json_enabled),
            service_name=env.get("GENESIS_LOGGING_SERVICE", cls.service_name),
        )


@dataclass(frozen=True)
class ObservabilitySettings:
    prometheus_port: int = 9000
    enable_tracing: bool = True
    metrics_namespace: str = "genesis"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ObservabilitySettings":
        return cls(
            prometheus_port=int(env.get("GENESIS_OBSERVABILITY_PROMETHEUS_PORT", cls.prometheus_port)),
            enable_tracing=_parse_bool(env.get("GENESIS_OBSERVABILITY_ENABLE_TRACING"), cls.enable_tracing),
            metrics_namespace=env.get("GENESIS_OBSERVABILITY_METRICS_NAMESPACE", cls.metrics_namespace),
        )


@dataclass(frozen=True)
class GenesisSettings:
    environment: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_version: str = "v1"
    database_url: str = "sqlite:///./genesis.db"
    redis_url: str = "redis://localhost:6379/0"
    worker_concurrency: int = 4
    governance_policy_path: Path = Path("src/genesis/governance/policies.json")
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    observability: ObservabilitySettings = field(default_factory=ObservabilitySettings)
    benchmarks_dir: Path = field(default_factory=lambda: _DEFAULT_BENCHMARKS_DIR)
    docs_build_dir: Path = field(default_factory=lambda: _DEFAULT_DOCS_BUILD_DIR)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "GenesisSettings":
        return cls(
            environment=env.get("GENESIS_ENVIRONMENT", cls.environment),
            api_host=env.get("GENESIS_API_HOST", cls.api_host),
            api_port=int(env.get("GENESIS_API_PORT", cls.api_port)),
            api_version=env.get("GENESIS_API_VERSION", cls.api_version),
            database_url=env.get("GENESIS_DATABASE_URL", cls.database_url),
            redis_url=env.get("GENESIS_REDIS_URL", cls.redis_url),
            worker_concurrency=int(env.get("GENESIS_WORKER_CONCURRENCY", cls.worker_concurrency)),
            governance_policy_path=Path(env.get("GENESIS_GOVERNANCE_POLICY_PATH", str(cls.governance_policy_path))),
            logging=LoggingSettings.from_env(env),
            observability=ObservabilitySettings.from_env(env),
            benchmarks_dir=Path(env.get("GENESIS_BENCHMARKS_DIR", str(_DEFAULT_BENCHMARKS_DIR))),
            docs_build_dir=Path(env.get("GENESIS_DOCS_BUILD_DIR", str(_DEFAULT_DOCS_BUILD_DIR))),
        )

    def load_governance_policies(self) -> Dict[str, Any]:
        path = self.governance_policy_path
        if not path.exists():
            raise FileNotFoundError(f"Governance policy file missing at {path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def with_overrides(self, **overrides: Any) -> "GenesisSettings":
        update: Dict[str, Any] = {}
        for key, value in overrides.items():
            if key == "logging":
                if isinstance(value, LoggingSettings):
                    update[key] = value
                elif isinstance(value, dict):
                    update[key] = replace(self.logging, **value)
                else:
                    raise TypeError("logging override must be LoggingSettings or dict")
            elif key == "observability":
                if isinstance(value, ObservabilitySettings):
                    update[key] = value
                elif isinstance(value, dict):
                    update[key] = replace(self.observability, **value)
                else:
                    raise TypeError("observability override must be ObservabilitySettings or dict")
            elif key in {"benchmarks_dir", "docs_build_dir", "governance_policy_path"}:
                update[key] = Path(value)
            else:
                update[key] = value
        return replace(self, **update)


@lru_cache(maxsize=1)
def load_settings(**overrides: Any) -> GenesisSettings:
    settings = GenesisSettings.from_env(os.environ)
    if overrides:
        settings = settings.with_overrides(**overrides)
    return settings


get_settings = load_settings


class _JSONFormatter(logging.Formatter):
    """Minimal JSON log formatter for structured logging support."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": getattr(record, "service", None),
            "time": self.formatTime(record, self.datefmt),
        }
        payload.update(get_log_context())
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Optional[LoggingSettings] = None) -> None:
    logging_settings = settings or get_settings().logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_settings.level.upper())
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    if logging_settings.json_enabled:
        formatter = _JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s | %(context)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    handler.setFormatter(formatter)

    class _ServiceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            setattr(record, "service", logging_settings.service_name)
            setattr(record, "context", json.dumps(get_log_context()))
            return True

    handler.addFilter(_ServiceFilter())
    root_logger.addHandler(handler)


__all__ = [
    "GenesisSettings",
    "LoggingSettings",
    "ObservabilitySettings",
    "configure_logging",
    "get_settings",
    "load_settings",
]
