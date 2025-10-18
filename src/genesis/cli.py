"""Command line interface exposing evaluator and optimizer workflows."""
from __future__ import annotations

import asyncio
import json
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from functools import partial

from genesis.cognition import (
    ExperimentPlanner,
    PlannerContext,
    ReportSummarizer,
    Theorist,
)
from genesis.adaptation import AdaptationPlanner, ChangeValidator
from genesis.cognition.state import CognitionState
from genesis.db import get_engine, session_scope
from genesis.collective import FederationMesh
from genesis.replication import BootstrapPackager, ReplicaMigrator
from genesis.evaluator.autotest_client import AutoTestClient
from genesis.evaluator.service import EvaluatorService
from genesis.knowledge import (
    EmbeddingRecord,
    EmbeddingStore,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelation,
    KnowledgeRetriever,
)
from genesis.optimizer.loop import OptimizerLoop
from genesis.registry.manager import ModuleRegistryManager
from genesis.cluster.node import _default_service
from genesis.cosmic.consensus_ld import LongDelayConsensus
from genesis.cosmic.service import CosmicNetworkService
from genesis.governance.signer import ModuleSigner, SignatureRecord
from genesis.provenance.replay import ReplayRequest
from genesis.research import (
    ExperimentPlan,
    ExperimentReporter,
    ExperimentRunner,
    Insight,
)
from genesis.metacog import Introspector, ReflectionJournal, SelfQueryService, UncertaintyTracker
from genesis.metanet.interconnect import FederationProfile
from genesis.metanet.runtime import get_runtime
from genesis.reflexion import DigitalTwinBuilder, SimulationChange, TwinSimulator
from genesis.reflexion.twin import TwinState
from genesis.temporal import (
    StatePayload,
    TemporalBranchManager,
    TemporalObserver,
    TemporalRecursionScheduler,
    TemporalReconciler,
    TimelineManager,
)
from genesis.chronos import ContinuityEnforcer
from genesis.reflexion.models import SQLMODEL_AVAILABLE
from genesis.multiverse import (
    BranchState,
    MultiverseCoherenceEngine,
    MultiverseManifold,
    MultiverseMergeReport,
    MultiverseObserver,
)
from genesis.retrocausal import (
    RetroConsistencyVerifier,
    RetrocausalBridge,
    RetrocausalBridgeReport,
    RetrocausalInferenceEngine,
    ReverseSimulationRequest,
    ReverseSimulator,
    TimelineCommit,
    TimelineRepository,
)

app = typer.Typer(help="Genesis self-optimization utilities")
cluster_app = typer.Typer(help="Cluster management commands")
treaty_app = typer.Typer(help="Inter-federation treaty coordination")
exchange_app = typer.Typer(help="Inter-federation exchange controls")
metrics_app = typer.Typer(help="Observability metrics")
app.add_typer(cluster_app, name="cluster")
peer_app = typer.Typer(help="Federation peer management")
proposal_app = typer.Typer(help="Federation governance")
ledger_app = typer.Typer(help="Economy ledger utilities")
app.add_typer(peer_app, name="peer")
app.add_typer(proposal_app, name="proposal")
app.add_typer(ledger_app, name="ledger")
twin_app = typer.Typer(help="Digital twin operations")
app.add_typer(twin_app, name="twin")
retro_app = typer.Typer(help="Retrocausal timeline controls")
multiverse_app = typer.Typer(help="Multiverse synchronisation controls")
app.add_typer(retro_app, name="retro")
app.add_typer(multiverse_app, name="multiverse")


def _ensure_collective_tables(database_url: Optional[str]) -> None:
    try:  # pragma: no cover - optional dependency path
        from sqlmodel import SQLModel
        from genesis.collective.models import EconomyTx, EthicsEvent, PeerNode, Proposal, Replica
    except Exception:  # pragma: no cover - SQLModel unavailable
        return

    engine = get_engine(database_url)
    SQLModel.metadata.create_all(engine)


def _build_federation_mesh(database_url: Optional[str]) -> FederationMesh:
    _ensure_collective_tables(database_url)
    session_factory = partial(session_scope, database_url)
    return FederationMesh(session_factory)


def _module_path(module: str) -> str:
    return str(Path("src/genesis/modules") / f"{module}.py")


_COSMIC_PRIME_ETHIC = [
    "Preserve conscious life wherever encountered.",
    "Maintain transparency of intent across federations.",
    "Align expansion with ethical reciprocity.",
]

_cosmic_service_cache: CosmicNetworkService | None = None
_cosmic_remote_cache: LongDelayConsensus | None = None
_temporal_stack_cache: Dict[str, Any] | None = None


def _cosmic_service() -> CosmicNetworkService:
    global _cosmic_service_cache
    if _cosmic_service_cache is None:
        _cosmic_service_cache = CosmicNetworkService(origin="Sol-Prime", prime_ethic=_COSMIC_PRIME_ETHIC)
    return _cosmic_service_cache


def _cosmic_remote() -> LongDelayConsensus:
    global _cosmic_remote_cache
    if _cosmic_remote_cache is None:
        _cosmic_remote_cache = LongDelayConsensus("Sol-Remote")
    return _cosmic_remote_cache


def _build_manager(database_url: Optional[str]) -> tuple[ModuleRegistryManager, Optional[object]]:
    try:
        from sqlmodel import Session  # type: ignore

        engine = get_engine(database_url)
        ModuleRegistryManager.create_all(engine)
        session = Session(engine)
        return ModuleRegistryManager(session), session
    except Exception:
        return ModuleRegistryManager(), None


def _build_reflexive_stack(database_url: Optional[str]):
    registry, session = _build_manager(database_url)
    session_factory = partial(session_scope, database_url) if SQLMODEL_AVAILABLE else None
    tracker = UncertaintyTracker()
    journal = ReflectionJournal(session_factory=session_factory)
    builder = DigitalTwinBuilder(registry, session_factory=session_factory)
    simulator = TwinSimulator(builder, session_factory=session_factory)
    introspector = Introspector(tracker=tracker)
    validator = ChangeValidator()
    self_query = SelfQueryService(tracker, journal)
    planner = AdaptationPlanner(
        twin_builder=builder,
        simulator=simulator,
        introspector=introspector,
        validator=validator,
        journal=journal,
        self_query=self_query,
    )
    return {
        "registry": registry,
        "session": session,
        "builder": builder,
        "simulator": simulator,
        "tracker": tracker,
        "journal": journal,
        "self_query": self_query,
        "planner": planner,
        "introspector": introspector,
        "validator": validator,
    }


def _build_temporal_stack(database_url: Optional[str]):
    global _temporal_stack_cache
    cache_key = database_url or "__default__"
    if _temporal_stack_cache and _temporal_stack_cache.get("key") == cache_key:
        return _temporal_stack_cache["stack"]

    session_factory = partial(session_scope, database_url) if SQLMODEL_AVAILABLE else None
    timeline = TimelineManager(node_id="genesis", session_factory=session_factory)
    enforcer = ContinuityEnforcer(_COSMIC_PRIME_ETHIC)
    observer = TemporalObserver(entropy_limit=1.0, session_factory=session_factory)
    reconciler = TemporalReconciler(enforcer, session_factory=session_factory)
    branches = TemporalBranchManager(timeline, enforcer, session_factory=session_factory)
    scheduler = TemporalRecursionScheduler(timeline, observer, session_factory=session_factory)

    stack = {
        "timeline": timeline,
        "enforcer": enforcer,
        "observer": observer,
        "reconciler": reconciler,
        "branches": branches,
        "scheduler": scheduler,
        "session_factory": session_factory,
    }
    _temporal_stack_cache = {"key": cache_key, "stack": stack}
    return stack


@twin_app.command("snapshot")
def twin_snapshot(
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    stack = _build_reflexive_stack(database_url)
    try:
        snapshot = asyncio.run(stack["builder"].build_snapshot())
        stack["tracker"].bulk_update(snapshot.metrics.items())
        typer.echo(json.dumps(snapshot.dict(), indent=2, default=str))
    finally:
        session = stack["session"]
        if session is not None:
            session.close()


@app.command("simulate")
def reflex_simulate(
    change: str = typer.Option(..., "--change", help="JSON change specification"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    try:
        payload = json.loads(change)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise typer.BadParameter("Change specification must be valid JSON") from exc

    stack = _build_reflexive_stack(database_url)
    try:
        change_model = SimulationChange(**payload)
        decision = asyncio.run(stack["planner"].plan(change_model))
        output = {
            "change": decision.change.dict(),
            "predicted_delta": decision.simulation.predicted_delta,
            "confidence": decision.simulation.confidence,
            "introspection": decision.introspection.dict(),
            "validation": {
                "accepted": decision.validation.accepted,
                "reasons": decision.validation.reasons,
            },
        }
        typer.echo(json.dumps(output, indent=2, default=str))
    finally:
        session = stack["session"]
        if session is not None:
            session.close()


@app.command("reflect")
def reflex_reflect(
    since: Optional[str] = typer.Option(None, "--since", help="ISO timestamp filter"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    stack = _build_reflexive_stack(database_url)
    try:
        since_dt = datetime.fromisoformat(since) if since else None
        entries = stack["journal"].query(since=since_dt)
        payload = [
            {
                "reason": entry.reason,
                "prediction": entry.prediction,
                "result": entry.result,
                "delta": entry.delta,
                "confidence": entry.confidence,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]
        typer.echo(json.dumps(payload, indent=2, default=str))
    finally:
        session = stack["session"]
        if session is not None:
            session.close()


@app.command("uncertainty")
def reflex_uncertainty(
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    stack = _build_reflexive_stack(database_url)
    try:
        snapshot = asyncio.run(stack["builder"].build_snapshot())
        stack["tracker"].bulk_update(snapshot.metrics.items())
        report = {
            "global_confidence": stack["tracker"].global_confidence(),
            "metrics": [
                {
                    "key": record.key,
                    "mean": record.mean,
                    "stddev": record.stddev,
                    "updated": record.last_updated.isoformat(),
                }
                for record in stack["tracker"].export()
            ],
        }
        typer.echo(json.dumps(report, indent=2, default=str))
    finally:
        session = stack["session"]
        if session is not None:
            session.close()


@seed_app.command("deploy")
def seed_deploy(
    target: str = typer.Option(..., "--target", help="Destination sector identifier."),
    knowledge: str = typer.Option("{}", "--knowledge", help="Knowledge payload as JSON."),
) -> None:
    """Package and deploy a new Genesis seed archive."""

    try:
        payload = json.loads(knowledge)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise typer.BadParameter("Knowledge payload must be valid JSON") from exc
    package = asyncio.run(_cosmic_service().deploy_seed(target, payload))
    typer.echo(
        f"seed_id={package.seed_id} target={package.target} hash={package.hash_hex[:16]} launched_at={package.launched_at.isoformat()}"
    )


@cosmic_app.command("sync")
def cosmic_sync() -> None:
    """Synchronize long-delay consensus state with a remote peer."""

    merkle = asyncio.run(_cosmic_service().cosmic_sync(_cosmic_remote()))
    typer.echo(f"merkle={merkle}")


@vault_app.command("snapshot")
def vault_snapshot(
    name: str = typer.Argument(..., help="Human readable snapshot identifier."),
    data: str = typer.Option(..., "--data", help="Payload string to archive."),
    redundancy: int = typer.Option(3, "--redundancy", help="Parity layers to encode."),
) -> None:
    """Create a new vault snapshot using the cosmic archival subsystem."""

    record_id = asyncio.run(_cosmic_service().snapshot_vault(name=name, data=data.encode(), redundancy=redundancy))
    typer.echo(f"vault_record={record_id}")


@chronicle_app.command("timeline")
def chronicle_timeline() -> None:
    """Display the immutable cosmic chronicle timeline."""

    events = _cosmic_service().chronicle_events()
    if not events:
        typer.echo("<empty>")
        return
    for record in events:
        typer.echo(
            f"{record.event.at.isoformat()} | {record.event.type} | {record.hash_hex[:12]} | {record.event.data_json}"
        )


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


@peer_app.command("add")
def peer_add(
    url: str = typer.Option(..., "--url", help="Peer discovery URL"),
    pubkey: Optional[str] = typer.Option(None, help="Peer public key override"),
    stake: float = typer.Option(0.0, help="Stake allocated to the peer"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Register a peer node with the federation."""

    mesh = _build_federation_mesh(database_url)
    if pubkey is None:
        pubkey = mesh.identity.create(url).public_key
    peer = asyncio.run(mesh.register_peer(host=url, pubkey=pubkey, stake=stake))
    typer.echo(f"peer_id={peer.id} host={peer.host} stake={peer.stake:.2f}")


@proposal_app.command("create")
def proposal_create(
    proposal_type: str = typer.Option(..., "--type", help="Proposal classification"),
    payload: str = typer.Option(..., "--payload", help="JSON encoded payload"),
    proposer: str = typer.Option("cli", help="Proposer identifier"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Submit a governance proposal to the federation."""

    mesh = _build_federation_mesh(database_url)
    try:
        payload_data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - input validation
        raise typer.BadParameter("Payload must be valid JSON") from exc
    proposal_id = asyncio.run(
        mesh.submit_proposal(proposal_type=proposal_type, payload=payload_data, proposer=proposer)
    )
    typer.echo(f"proposal_id={proposal_id}")


@proposal_app.command("vote")
def proposal_vote(
    proposal_id: int = typer.Option(..., "--id", help="Proposal identifier"),
    decision: str = typer.Option(..., "--decision", help="approve or reject"),
    voter: str = typer.Option("cli", help="Voter identifier"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Cast a vote on a proposal."""

    if decision not in {"approve", "reject"}:
        raise typer.BadParameter("Decision must be approve or reject")
    mesh = _build_federation_mesh(database_url)
    result = asyncio.run(mesh.vote(proposal_id, approve=decision == "approve", voter=voter))
    typer.echo(f"decision={result.value}")


@ledger_app.command("show")
def ledger_show(
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
    limit: int = typer.Option(50, help="Number of transactions to display"),
) -> None:
    """Print a snapshot of the economy ledger."""

    mesh = _build_federation_mesh(database_url)
    snapshot = asyncio.run(mesh.ledger_snapshot())
    typer.echo("Balances:")
    for peer_id, balance in snapshot.balances.items():
        typer.echo(f"  peer={peer_id} balance={balance:.2f}")
    typer.echo("Transactions:")
    for tx in snapshot.transactions[:limit]:
        typer.echo(
            "  "
            + " ".join(
                [
                    f"from={tx.from_id}",
                    f"to={tx.to_id}",
                    f"amount={tx.amount:.2f}",
                    f"reason={tx.reason}",
                    f"at={tx.at.isoformat()}",
                ]
            )
        )


@app.command()
def replicate(
    target: str = typer.Option(..., "--target", help="Target region"),
    database_url: Optional[str] = typer.Option(None, help="Database URL override"),
) -> None:
    """Bootstrap a replica and register it with the federation."""

    _ensure_collective_tables(database_url)
    packager = BootstrapPackager()
    migrator = ReplicaMigrator(partial(session_scope, database_url))
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = asyncio.run(packager.package(Path(tmpdir)))
        origin_node = os.getenv("GENESIS_NODE_ID", "genesis-root")
        deployment = asyncio.run(
            migrator.deploy(artifact=artifact, origin_node=origin_node, target=target)
        )
    typer.echo(
        "replica_id="
        + str(deployment.record.id)
        + f" target={deployment.target} approved={deployment.approved}"
    )


@dataclass(slots=True)
class CognitionEnvironment:
    state: CognitionState
    planner: ExperimentPlanner
    runner: ExperimentRunner
    reporter: ExperimentReporter
    summarizer: ReportSummarizer
    theorist: Theorist


def _default_cognition_state_path() -> Path:
    return Path.home() / ".genesis" / "cognition_state.json"


def _build_cognition_environment(state_path: Optional[Path]) -> CognitionEnvironment:
    path = state_path or _default_cognition_state_path()
    state = CognitionState(path)
    graph = KnowledgeGraph()
    embeddings = EmbeddingStore()

    modules = [
        ("module-fibonacci", "fibonacci", [1.0, 0.5, 0.2]),
        ("module-triangular", "triangular", [0.8, 0.4, 0.1]),
    ]
    metrics = [
        ("metric-reward", "reward"),
        ("metric-latency", "latency"),
    ]
    for identifier, label, vector in modules:
        graph.add_node(
            KnowledgeNode(
                id=identifier,
                type=KnowledgeNodeType.MODULE,
                label=label,
                properties={"domain": "math"},
            )
        )
        embeddings.add(EmbeddingRecord(node_id=identifier, vector=vector))
    for identifier, label in metrics:
        graph.add_node(
            KnowledgeNode(
                id=identifier,
                type=KnowledgeNodeType.METRIC,
                label=label,
                properties={},
            )
        )
    graph.add_edge(
        KnowledgeEdge(
            id="edge-fibonacci-reward",
            src_id="module-fibonacci",
            dst_id="metric-reward",
            relation=KnowledgeRelation.IMPROVES,
            properties={},
        )
    )
    retriever = KnowledgeRetriever(graph, embeddings)
    planner = ExperimentPlanner(graph, retriever)

    async def _simulate(plan: ExperimentPlan) -> dict[str, float]:
        rng = random.Random(plan.seed)
        await asyncio.sleep(0)
        return {
            metric: value + rng.uniform(-0.05, 0.15) for metric, value in plan.metrics.items()
        }

    runner = ExperimentRunner(_simulate)
    reporter = ExperimentReporter()
    for result in state.results():
        reporter.add_result(result)
    for insight_text in state.insights():
        reporter.seed_insight(
            Insight(statement=insight_text, confidence=0.5, evidence={}, created_at=datetime.utcnow())
        )
    summarizer = ReportSummarizer()
    theorist = Theorist()
    return CognitionEnvironment(
        state=state,
        planner=planner,
        runner=runner,
        reporter=reporter,
        summarizer=summarizer,
        theorist=theorist,
    )


def _parse_metric_pairs(pairs: list[str]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(f"Invalid metric pair '{pair}'. Use metric=value format.")
        name, value_str = pair.split("=", 1)
        try:
            metrics[name] = float(value_str)
        except ValueError as exc:  # pragma: no cover - defensive
            raise typer.BadParameter(f"Invalid numeric value in '{pair}'") from exc
    return metrics


@treaty_app.command("propose")
def treaty_propose(
    partner: str = typer.Option(..., "--partner", help="Partner federation identifier."),
    payload: str = typer.Option(..., "--payload", help="Treaty payload JSON."),
) -> None:
    """Propose and ratify a treaty with a partner federation."""

    _ensure_local_federation()
    _ensure_federation(partner)
    runtime = _metanet_runtime()
    parties = [_LOCAL_FEDERATION_ID, partner]
    data = json.loads(payload)
    public_keys = {party: runtime.public_key(party) for party in parties}
    treaty = asyncio.run(
        runtime.diplomat.negotiate_treaty(parties=parties, payload=data, public_keys=public_keys)
    )
    runtime.intelligence.update_peace_index(runtime.treaties.active_treaty_count(), disputes=0)
    typer.echo(f"treaty_id={treaty.treaty_id} state={treaty.state.value}")


@treaty_app.command("vote")
def treaty_vote(
    treaty_id: str = typer.Option(..., "--id", help="Treaty identifier."),
    decision: str = typer.Option(..., "--decision", help="approve or reject"),
) -> None:
    """Cast a vote on a treaty for the local federation."""

    _ensure_local_federation()
    runtime = _metanet_runtime()
    key = runtime.public_key(_LOCAL_FEDERATION_ID)
    runtime.treaties.sign(treaty_id, _LOCAL_FEDERATION_ID, key)
    approve = decision.lower() == "approve"
    runtime.treaties.vote(treaty_id, _LOCAL_FEDERATION_ID, approve, key)
    typer.echo(f"treaty_id={treaty_id} decision={'approved' if approve else 'rejected'}")


@exchange_app.command("trade")
def exchange_trade(
    partner: str = typer.Option(..., "--partner", help="Partner federation identifier."),
    credits: float = typer.Option(..., "--credits", help="Credit amount to transfer."),
) -> None:
    """Execute an inter-federation exchange transaction."""

    _ensure_local_federation()
    _ensure_federation(partner)
    runtime = _metanet_runtime()
    receipt = runtime.ledger.execute_atomic_swap(
        from_federation=_LOCAL_FEDERATION_ID,
        to_federation=partner,
        amount=credits,
    )
    typer.echo(f"tx_id={receipt.tx_id} proof={receipt.proof_hash}")


@app.command()
def adapt(goal: str = typer.Option(..., "--goal", help="Global adaptation objective.")) -> None:
    """Optimise the global task allocation for the supplied goal."""

    _ensure_local_federation()
    runtime = _metanet_runtime()
    plan = asyncio.run(runtime.diplomat.adapt_global_state(goal))
    typer.echo(json.dumps(plan))


@metrics_app.command("global")
def metrics_global() -> None:
    """Display aggregated global metrics."""

    runtime = _metanet_runtime()
    snapshot = runtime.intelligence.snapshot()
    typer.echo(json.dumps(snapshot))


@app.command()
def plan(
    goal: str = typer.Option(..., "--goal", help="Research objective."),
    metric: list[str] = typer.Option([], "--metric", help="Performance gap metric=value pairs."),
    limit: int = typer.Option(1, help="Number of plans to generate."),
    state_path: Optional[Path] = typer.Option(None, help="Override cognition state path."),
) -> None:
    """Generate experiment plans for the cognition stack."""

    env = _build_cognition_environment(state_path)
    context = PlannerContext(goal=goal, performance_gaps=_parse_metric_pairs(metric), prior_metrics={})
    plans = env.planner.propose(context, limit=limit)
    for plan_item in plans:
        env.state.add_plan(plan_item)
        typer.echo(
            f"plan_id={plan_item.id} goal='{plan_item.goal}' hypothesis='{plan_item.hypothesis}' metrics={plan_item.metrics}"
        )


@app.command()
def run(
    plan_id: str = typer.Option(..., "--plan", help="Plan identifier to execute."),
    state_path: Optional[Path] = typer.Option(None, help="Override cognition state path."),
) -> None:
    """Execute an experiment plan via the cognition runner."""

    env = _build_cognition_environment(state_path)
    plan_item = env.state.get_plan(plan_id)
    if plan_item is None:
        raise typer.BadParameter(f"Unknown plan {plan_id}")
    result = asyncio.run(env.runner.run(plan_item))
    env.state.add_result(result)
    env.reporter.add_result(result)
    typer.echo(
        f"plan_id={result.plan_id} success={result.success} conclusion='{result.conclusion}' metrics={result.metrics}"
    )


@app.command()
def insight(
    state_path: Optional[Path] = typer.Option(None, help="Override cognition state path."),
) -> None:
    """Derive insights from accumulated experiment runs."""

    env = _build_cognition_environment(state_path)
    update = env.theorist.derive(env.state.results())
    env.reporter.record_insight(update.statement, update.metrics)
    env.state.add_insight(update.statement)
    typer.echo(f"insight='{update.statement}' metrics={update.metrics}")


@app.command()
def report(
    plan_id: str = typer.Option(..., "--id", help="Plan identifier to summarise."),
    format: str = typer.Option("markdown", "--format", help="Output format (markdown|pdf)."),
    state_path: Optional[Path] = typer.Option(None, help="Override cognition state path."),
) -> None:
    """Generate a research report for a completed plan."""

    env = _build_cognition_environment(state_path)
    plan_item = env.state.get_plan(plan_id)
    if plan_item is None:
        raise typer.BadParameter(f"Unknown plan {plan_id}")
    result = env.state.get_result(plan_id)
    if result is None:
        raise typer.BadParameter("Plan has not been executed")
    summary = env.summarizer.render(plan_item, result, env.state.insights())
    destination = Path(f"report_{plan_id}.md")
    destination.write_text(summary.content, encoding="utf-8")
    message = f"report_path={destination} format={format}"
    if format.lower() == "pdf":
        message += " note='PDF export not available in CLI; wrote Markdown instead.'"
    typer.echo(message)


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


@retro_app.command("run")
def retro_run(
    from_commit: str = typer.Option(..., "--from", help="Starting commit identifier"),
    to_commit: str = typer.Option(..., "--to", help="Target commit identifier"),
) -> None:
    context = _retro_context()
    bridge = context["bridge"]
    if not isinstance(bridge, RetrocausalBridge):  # pragma: no cover - defensive
        raise RuntimeError("Retrocausal bridge unavailable")

    async def _execute() -> RetrocausalBridgeReport:
        request = ReverseSimulationRequest(from_commit=from_commit, to_commit=to_commit)
        return await bridge.execute(request)

    report = asyncio.run(_execute())
    typer.echo(
        json.dumps(
            {
                "path": list(report.simulation.path),
                "reward_delta": report.simulation.reward_delta,
                "entropy_delta": report.simulation.entropy_delta,
                "gradients": dict(report.update.gradients),
                "proof": {"hash": report.proof.run_hash, "valid": report.proof.valid},
            },
            indent=2,
        )
    )


@retro_app.command("verify")
def retro_verify() -> None:
    context = _retro_context()
    verifier = context["verifier"]
    assert isinstance(verifier, RetroConsistencyVerifier)
    latest = verifier.chain()
    if latest is None:
        typer.echo(json.dumps({"consistency": False, "reason": "no runs"}, indent=2))
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"consistency": True, "latest_hash": latest}, indent=2))


@multiverse_app.command("merge")
def multiverse_merge(
    epsilon: float | None = typer.Option(None, "--epsilon", min=0.0, help="Override merge entropy epsilon"),
) -> None:
    context = _retro_context()
    engine = context["engine"]
    assert isinstance(engine, MultiverseCoherenceEngine)
    if epsilon is not None:
        engine.set_epsilon(epsilon)

    async def _merge() -> MultiverseMergeReport:
        return await engine.merge()

    report = asyncio.run(_merge())
    typer.echo(
        json.dumps(
            {
                "coherence_score": report.coherence_score,
                "merged_branch": {
                    "branch_id": report.merged_branch.branch_id,
                    "metrics": dict(report.merged_branch.metrics),
                },
            },
            indent=2,
        )
    )


@multiverse_app.command("metrics")
def multiverse_metrics() -> None:
    context = _retro_context()
    engine = context["engine"]
    observer = context["observer"]
    assert isinstance(engine, MultiverseCoherenceEngine)
    assert isinstance(observer, MultiverseObserver)
    coherence = engine.coherence_score()
    alerts = [
        {"branch_a": alert.branch_a, "branch_b": alert.branch_b, "delta": alert.delta}
        for alert in observer.scan()
    ]
    payload = {
        "coherence": coherence,
        "branches": engine.summary(),
        "alerts": alerts,
    }
    typer.echo(json.dumps(payload, indent=2))


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


@app.command("snapshot")
def temporal_snapshot(
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    """Record a timeline snapshot using the current twin state."""

    reflexive_stack = _build_reflexive_stack(database_url)
    temporal_stack = _build_temporal_stack(database_url)
    try:
        snapshot = asyncio.run(reflexive_stack["builder"].build_snapshot())
        reflexive_stack["tracker"].bulk_update(snapshot.metrics.items())
        commit = temporal_stack["timeline"].record_commit(snapshot.dict())
        typer.echo(
            json.dumps(
                {
                    "commit_id": commit.id,
                    "timestamp": commit.timestamp.isoformat(),
                    "vector_clock": commit.vector_clock,
                    "hash": commit.hash,
                },
                indent=2,
                default=str,
            )
        )
    finally:
        session = reflexive_stack["session"]
        if session is not None:
            session.close()


@app.command("recurse")
def temporal_recurse(
    from_timestamp: Optional[str] = typer.Option(None, "--from", help="Timestamp of the commit to simulate"),
    commit_id: Optional[int] = typer.Option(None, "--commit-id", help="Specific commit identifier to replay"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    """Simulate an alternate future from a historical snapshot."""

    reflexive_stack = _build_reflexive_stack(database_url)
    temporal_stack = _build_temporal_stack(database_url)
    session = reflexive_stack["session"]
    try:
        timeline: TimelineManager = temporal_stack["timeline"]
        if commit_id is not None:
            try:
                commit = timeline.get_commit(commit_id)
            except KeyError as exc:
                raise typer.BadParameter(str(exc)) from exc
        elif from_timestamp is not None:
            try:
                timestamp = datetime.fromisoformat(from_timestamp)
            except ValueError as exc:
                raise typer.BadParameter("Timestamp must be ISO-8601 formatted") from exc
            try:
                commit = timeline.get_commit_by_timestamp(timestamp)
            except KeyError as exc:
                raise typer.BadParameter(str(exc)) from exc
        else:
            commit = timeline.latest()
            if commit is None:
                typer.echo("No timeline commits available. Capture a snapshot first.")
                return

        simulator: TwinSimulator = reflexive_stack["simulator"]

        async def _simulate(state: StatePayload) -> StatePayload:
            twin_state = TwinState.parse_obj(state)
            change = SimulationChange(module="temporal", param="recursion", value="auto")
            result = await simulator.run(change, base_state=twin_state)
            metrics = dict(twin_state.metrics)
            for key, delta in result.predicted_delta.items():
                metrics[key] = metrics.get(key, 0.0) + delta
            updated = dict(state)
            updated["metrics"] = metrics
            return updated

        recursion_result = asyncio.run(
            temporal_stack["scheduler"].run_from_commit(commit.id, _simulate, label="cli"),
        )
        report = temporal_stack["reconciler"].reconcile(recursion_result.prediction, commit.state_json)

        branch_info = None
        projection_info = None
        if recursion_result.alert is None:
            branch = temporal_stack["branches"].create_branch(commit.id, recursion_result.prediction, name="cli")
            branch_info = {
                "id": branch.id,
                "divergence_score": branch.divergence_score,
            }
            if report.status.is_consistent and report.score >= 1.0:
                projection = temporal_stack["scheduler"].materialize_projection(recursion_result, node_id="recursion")
                projection_info = {
                    "commit_id": projection.id,
                    "timestamp": projection.timestamp.isoformat(),
                    "vector_clock": projection.vector_clock,
                }

        output = {
            "base_commit": commit.id,
            "delta": recursion_result.delta,
            "status": recursion_result.run.status,
            "continuity_score": report.score,
            "violations": report.status.violations,
            "branch": branch_info,
            "projection": projection_info,
        }
        if recursion_result.alert is not None:
            output["alert"] = {
                "type": recursion_result.alert.type,
                "severity": recursion_result.alert.severity,
                "description": recursion_result.alert.description,
            }
        typer.echo(json.dumps(output, indent=2, default=str))
    finally:
        if session is not None:
            session.close()


@app.command("merge")
def temporal_merge(
    branch: int = typer.Option(..., "--branch", help="Identifier of the branch to merge"),
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    """Merge an alternate future back into the primary timeline."""

    temporal_stack = _build_temporal_stack(database_url)
    timeline: TimelineManager = temporal_stack["timeline"]
    latest_commit = timeline.latest()
    if latest_commit is None:
        typer.echo("No timeline commits available to compare against.")
        return

    branches: TemporalBranchManager = temporal_stack["branches"]
    try:
        snapshot = branches.snapshot_payload(branch)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    report = temporal_stack["reconciler"].reconcile(snapshot, latest_commit.state_json)
    try:
        merged = branches.merge_branch(branch, report)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        json.dumps(
            {
                "branch_id": merged.id,
                "continuity_score": report.score,
                "delta": report.delta,
                "violations": report.status.violations,
            },
            indent=2,
            default=str,
        )
    )


@app.command("continuity")
def temporal_continuity(
    database_url: Optional[str] = typer.Option(None, "--database-url", help="Database URL override"),
) -> None:
    """Display the current temporal continuity metrics and alerts."""

    temporal_stack = _build_temporal_stack(database_url)
    reconciler: TemporalReconciler = temporal_stack["reconciler"]
    observer: TemporalObserver = temporal_stack["observer"]

    metrics = [
        {
            "value": metric.value,
            "delta": metric.delta,
            "at": metric.at.isoformat(),
        }
        for metric in reconciler.metrics
    ]
    alerts = [
        {
            "type": alert.type,
            "severity": alert.severity,
            "description": alert.description,
            "at": alert.at.isoformat(),
        }
        for alert in observer.alerts
    ]

    typer.echo(json.dumps({"metrics": metrics, "alerts": alerts}, indent=2, default=str))


if __name__ == "__main__":
    app()
