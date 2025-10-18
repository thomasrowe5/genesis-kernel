from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("prometheus_fastapi_instrumentator")

from fastapi.testclient import TestClient

from genesis.api.main import create_app
from genesis.governance import rbac


def _make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GENESIS_API_KEY_ID", "test")
    monkeypatch.setenv("GENESIS_API_KEY_SECRET", "secret")
    monkeypatch.setenv("GENESIS_API_KEY_ROLES", "viewer,operator")
    rbac._rbac_singleton = None  # reset cached manager for deterministic tests
    app = create_app()
    return TestClient(app)


def test_openapi_available(monkeypatch) -> None:
    client = _make_client(monkeypatch)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Genesis Unified API"


def test_health_requires_credentials(monkeypatch) -> None:
    client = _make_client(monkeypatch)
    response = client.get("/health/live")
    assert response.status_code == 401

    headers = {"Authorization": "Bearer test:secret"}
    response = client.get("/health/live", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
