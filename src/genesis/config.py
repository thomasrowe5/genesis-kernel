"""Application configuration helpers."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables."""

    environment: Literal["local", "test", "docker", "production"] = Field(
        default="local", alias="GENESIS_ENVIRONMENT"
    )
    db_url: str = Field(
        default="sqlite:///./genesis.db", alias="GENESIS_DB_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="GENESIS_REDIS_URL")
    worker_poll_interval: float = Field(default=1.0, alias="GENESIS_WORKER_POLL_INTERVAL")
    worker_concurrency: int = Field(default=1, alias="GENESIS_WORKER_CONCURRENCY")
    worker_heartbeat_interval: float = Field(
        default=15.0, alias="GENESIS_WORKER_HEARTBEAT_INTERVAL"
    )
    max_retries: int = Field(default=3, alias="GENESIS_JOB_MAX_RETRIES")
    dedupe_ttl: int = Field(default=300, alias="GENESIS_DEDUPE_TTL")

    class Config:
        populate_by_name = True

    @classmethod
    def from_env(cls) -> "Settings":
        data = {field.alias: os.getenv(field.alias, field.default) for field in cls.model_fields.values()}
        return cls(**data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
