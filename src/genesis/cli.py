"""Command line interface exposing evaluator and optimizer workflows."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer

from genesis.db import get_engine
from genesis.evaluator.autotest_client import AutoTestClient
from genesis.evaluator.service import EvaluatorService
from genesis.optimizer.loop import OptimizerLoop
from genesis.registry.manager import ModuleRegistryManager
from genesis.cluster.node import _default_service
from genesis.governance.signer import ModuleSigner, SignatureRecord
from genesis.provenance.replay import ReplayRequest

app = typer.Typer(help="Genesis self-optimization utilities")
cluster_app = typer.Typer(help="Cluster management commands")
app.add_typer(cluster_app, name="cluster")


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


@cluster_app.command("join")
def cluster_join(peer: str = typer.Option(..., "--peer", help="Peer URL")) -> None:
    """Join a new peer to the cluster sync mesh."""

    peers = set(_default_service.peers())
    peers.add(peer)
    _default_service.update_peers(sorted(peers))
    typer.echo(f"cluster peers={' '.join(sorted(peers))}")


@cluster_app.command("status")
def cluster_status() -> None:
    """Display local heartbeat information."""

    snapshot = _default_service.health_snapshot()
    for heartbeat in snapshot:
        typer.echo(
            f"node={heartbeat.node_id} status={heartbeat.status} last_seen={heartbeat.last_seen.isoformat()}"
        )


@app.command()
def replay(experiment: str = typer.Option(..., "--experiment", help="Experiment identifier")) -> None:
    """Trigger deterministic replay for an experiment."""

    result = asyncio.run(_default_service.replay_engine.replay(ReplayRequest(experiment_id=experiment)))
    typer.echo(f"experiment={result.experiment_id} hash={result.output_hash}")


def _signer() -> ModuleSigner:
    secret = os.getenv("GENESIS_SIGNING_SECRET", "genesis-signing-secret").encode("utf-8")
    return ModuleSigner(secret=secret, on_verify=_default_service.record_signature_verification)


@app.command()
def sign(
    module: str = typer.Argument(..., help="Module name to sign"),
    version: str = typer.Argument(..., help="Module version label"),
    metadata: Optional[str] = typer.Option(None, help="Metadata string to include in the signature"),
    output: Optional[Path] = typer.Option(None, help="Optional path to write signature JSON"),
) -> None:
    """Sign a module implementation and emit a lineage record."""

    signer = _signer()
    module_path = Path(_module_path(module))
    metadata_str = metadata or json.dumps({"module": module, "version": version})
    record = signer.sign(
        module_version_id=f"{module}:{version}",
        source_path=module_path,
        metadata=metadata_str,
        signer="cli",
    )
    payload = {
        "module_version_id": record.module_version_id,
        "hash_hex": record.hash_hex,
        "signer": record.signer,
        "verified": record.verified,
        "previous_hash": record.previous_hash,
        "metadata": metadata_str,
    }
    destination = output or Path(f"{module}-{version}.signature.json")
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(f"signature={record.hash_hex} path={destination}")


@app.command()
def verify(
    signature_path: Path = typer.Argument(..., help="Path to the signature JSON"),
    metadata: Optional[str] = typer.Option(None, help="Metadata string used during signing"),
) -> None:
    """Verify a previously signed module version."""

    payload = json.loads(signature_path.read_text(encoding="utf-8"))
    record = SignatureRecord(
        module_version_id=payload["module_version_id"],
        hash_hex=payload["hash_hex"],
        signer=payload.get("signer", "unknown"),
        verified=payload.get("verified", False),
        previous_hash=payload.get("previous_hash"),
    )
    module, version = record.module_version_id.split(":", 1)
    module_path = Path(_module_path(module))
    metadata_str = metadata or payload.get("metadata", "")
    signer = _signer()
    success = signer.verify(record, module_path, metadata_str)
    status = "success" if success else "failed"
    typer.echo(f"verification={status}")


if __name__ == "__main__":
    app()
