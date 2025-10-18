from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("typer")

from typer.testing import CliRunner

from genesis.cli import app
from genesis.core.config import load_settings


def _reset_settings_cache() -> None:
    load_settings.cache_clear()  # type: ignore[attr-defined]


def test_benchmark_run_writes_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GENESIS_BENCHMARKS_DIR", str(tmp_path))
    _reset_settings_cache()
    runner = CliRunner()
    result = runner.invoke(app, ["benchmark", "run", "--samples", "2"])
    assert result.exit_code == 0
    files = list(tmp_path.glob("benchmark_*.json"))
    assert files, result.stdout


def test_docs_build_generates_html(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GENESIS_DOCS_BUILD_DIR", str(tmp_path))
    _reset_settings_cache()
    runner = CliRunner()
    result = runner.invoke(app, ["docs", "build"])
    assert result.exit_code == 0
    index = tmp_path / "index.html"
    assert index.exists()


def test_release_create_dry_run(tmp_path, monkeypatch) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _reset_settings_cache()
    runner = CliRunner()
    result = runner.invoke(app, ["release", "create", "--version", "1.5.0"])
    assert result.exit_code == 0
    assert "Preview release entry" in result.stdout
