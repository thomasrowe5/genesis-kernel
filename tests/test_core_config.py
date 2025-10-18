from __future__ import annotations

import json
from pathlib import Path

from genesis.core.config import (
    GenesisSettings,
    LoggingSettings,
    configure_logging,
    get_settings,
    load_settings,
)


def test_load_settings_reads_policies(tmp_path: Path, monkeypatch) -> None:
    policies = {"prime_ethic": ["one"]}
    policy_path = tmp_path / "policies.json"
    policy_path.write_text(json.dumps(policies), encoding="utf-8")

    settings = load_settings(governance_policy_path=policy_path)
    assert settings.load_governance_policies()["prime_ethic"] == ["one"]


def test_configure_logging_switches_to_text(monkeypatch) -> None:
    settings = GenesisSettings(logging=LoggingSettings(json_enabled=False))
    monkeypatch.setattr("genesis.core.config.get_settings", lambda: settings)
    configure_logging(settings.logging)

    import logging

    root = logging.getLogger()
    assert root.level == logging.INFO


def test_get_settings_cached() -> None:
    first = get_settings()
    second = get_settings()
    assert first is second
