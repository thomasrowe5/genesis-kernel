"""Command line interface exposing evaluator and optimizer workflows."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from genesis.db import get_engine
from genesis.evaluator.autotest_client import AutoTestClient
from genesis.evaluator.service import EvaluatorService
from genesis.optimizer.loop import OptimizerLoop
from genesis.registry.manager import ModuleRegistryManager

app = typer.Typer(help="Genesis self-optimization utilities")


def _module_path(module: str) -> str:
    return str(Path("src/genesis/modules") / f"{module}.py")


def _build_manager(database_url: Optional[str]) -> tuple[ModuleRegistryManager, Optional[object]]:
    try:
        from sqlmodel import Session  # type: ignore

        engine = get_engine(database_url)
        ModuleRegistryManager.create_all(engine)
        session = Session(engine)
        return ModuleRegistryManager(session), session
    except Exception:
        return ModuleRegistryManager(), None


@app.command()
def eval(
    module: str = typer.Argument(..., help="Target module name"),
    version: str = typer.Option("candidate", help="Version label for the candidate"),
    benchmark: Optional[str] = typer.Option(None, help="Override benchmark identifier"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Run the evaluation pipeline for a module candidate."""

    registry, session = _build_manager(database_url)
    try:
        evaluator = EvaluatorService(AutoTestClient())
        optimizer = OptimizerLoop(registry, evaluator)
        outcome = asyncio.run(
            optimizer.evaluate_candidate(
                name=module,
                version=version,
                path=_module_path(module),
                metadata={"benchmark": benchmark} if benchmark else None,
                benchmark=benchmark,
            )
        )
        typer.echo(
            f"module={outcome.module} version={outcome.version} reward={outcome.reward:.3f} promoted={outcome.promoted}"
        )
    finally:
        if session:
            session.close()


@app.command()
def leaderboard(
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
    limit: int = typer.Option(10, help="Number of entries to display"),
) -> None:
    """Display the top scoring module variants."""

    registry, session = _build_manager(database_url)
    try:
        for entry in registry.leaderboard(limit=limit):
            typer.echo(
                f"{entry['name']}@{entry['version']} score={entry['score']:.3f} active={entry['active']}"
            )
    finally:
        if session:
            session.close()


@app.command()
def promote(
    module: str = typer.Argument(..., help="Target module name"),
    version: str = typer.Option(..., "--version", "-v", help="Version to promote"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Manually promote a module implementation."""

    registry, session = _build_manager(database_url)
    try:
        candidate = registry.get_version(module, version)
        if candidate is None:
            raise typer.BadParameter(f"Unknown module version {module}@{version}")
        registry.activate_version(candidate)
        registry.record_replacement(candidate, previous_version=None)
        typer.echo(f"Promoted {module}@{version}")
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    app()
