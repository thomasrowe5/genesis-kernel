"""Prometheus metric definitions for the Genesis kernel."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Temporal recursion metrics.
genesis_timeline_commits_total = Counter(
    "genesis_timeline_commits_total",
    "Total number of timeline commits recorded by the temporal core.",
)

genesis_recursion_runs_total = Counter(
    "genesis_recursion_runs_total",
    "Temporal recursion runs executed by the causal simulator.",
    labelnames=("status",),
)

genesis_branch_merges_total = Counter(
    "genesis_branch_merges_total",
    "Total number of alternate futures merged back into the main timeline.",
)

genesis_entropy_delta = Gauge(
    "genesis_entropy_delta",
    "Latest entropy delta observed between predicted and actual metrics.",
)

genesis_continuity_score = Gauge(
    "genesis_continuity_score",
    "Continuity score representing alignment between predicted and actual states.",
)

genesis_temporal_violations_total = Counter(
    "genesis_temporal_violations_total",
    "Temporal violations detected by the causality observer.",
)

# Reflexive intelligence metrics.
genesis_reflexive_cycles_total = Counter(
    "genesis_reflexive_cycles_total",
    "Total number of reflexive intelligence cycles executed.",
)

genesis_simulations_total = Counter(
    "genesis_simulations_total",
    "Simulation executions within the reflexive intelligence layer.",
    labelnames=("status",),
)

genesis_reflection_confidence_mean = Gauge(
    "genesis_reflection_confidence_mean",
    "Rolling mean confidence recorded in reflection logs.",
)

genesis_uncertainty_metrics_total = Gauge(
    "genesis_uncertainty_metrics_total",
    "Number of metrics tracked by the uncertainty engine.",
)

genesis_twin_sync_latency_seconds = Histogram(
    "genesis_twin_sync_latency_seconds",
    "Latency required to construct or refresh the digital twin.",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)

genesis_meta_anomalies_total = Counter(
    "genesis_meta_anomalies_total",
    "Anomalies detected by reflexive introspection.",
)

# Histogram tracking the duration of each evaluator execution.
genesis_eval_duration_seconds = Histogram(
    "genesis_eval_duration_seconds",
    "Time spent running module evaluations via the AutoTest service.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Gauge capturing the latest score emitted for a module variant.
genesis_module_score = Gauge(
    "genesis_module_score",
    "Composite reward score per module variant.",
    labelnames=("module", "version"),
)

# Counter recording module replacement events triggered by the optimizer.
genesis_replacements_total = Counter(
    "genesis_replacements_total",
    "Number of times the optimizer promoted a new module implementation.",
)

# Router selection counter capturing policy decisions.
genesis_router_selection_total = Counter(
    "genesis_router_selection_total",
    "Router selections per policy and module variant.",
    labelnames=("policy", "module", "version"),
)

# Canary rollout counters.
genesis_canary_promotions_total = Counter(
    "genesis_canary_promotions_total",
    "Successful canary promotions per module version.",
    labelnames=("module", "version"),
)

genesis_canary_rollbacks_total = Counter(
    "genesis_canary_rollbacks_total",
    "Number of canary rollbacks triggered by SLO breaches.",
    labelnames=("module", "version", "reason"),
)

# Traffic share gauge for observability dashboards.
genesis_traffic_share = Gauge(
    "genesis_traffic_share",
    "Current traffic share per module version.",
    labelnames=("module", "version"),
)

# RL reward telemetry.
genesis_rl_reward = Gauge(
    "genesis_rl_reward",
    "Latest reward emitted by the online optimizer.",
    labelnames=("module", "version"),
)

genesis_rl_update_total = Counter(
    "genesis_rl_update_total",
    "Number of optimizer updates processed.",
)

genesis_cosmic_latency_seconds = Histogram(
    "genesis_cosmic_latency_seconds",
    "Latency distribution for long-delay cosmic consensus links.",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

genesis_adaptation_cycles_total = Counter(
    "genesis_adaptation_cycles_total",
    "Total number of adaptation engine cycles executed globally.",
)

genesis_reconciliation_cycles_total = Counter(
    "genesis_reconciliation_cycles_total",
    "Propagation reconciliation cycles executed across cosmic relays.",
)

genesis_seeds_total = Counter(
    "genesis_seeds_total",
    "Seed packages generated for cosmic propagation.",
)

genesis_branches_total = Counter(
    "genesis_branches_total",
    "Cosmic branches synchronized across the federation mesh.",
)

genesis_chronicle_events_total = Counter(
    "genesis_chronicle_events_total",
    "Chronicle events recorded across archival ledgers.",
)

genesis_information_entropy_ratio = Gauge(
    "genesis_information_entropy_ratio",
    "Information entropy ratio across interstellar data channels.",
)

genesis_vault_records_total = Counter(
    "genesis_vault_records_total",
    "Vault records processed by cosmic archival retrieval.",
)

# Cache and rate-limit instrumentation.
genesis_cache_hits_total = Counter(
    "genesis_cache_hits_total",
    "Cache hits recorded per task type.",
    labelnames=("task_type",),
)

genesis_rate_limit_drops_total = Counter(
    "genesis_rate_limit_drops_total",
    "Requests dropped because of rate limiting per task type.",
    labelnames=("task_type",),
)

# Orchestration decision latency histogram.
genesis_orch_decision_duration_seconds = Histogram(
    "genesis_orch_decision_duration_seconds",
    "Time spent computing orchestration decisions (routing, canary, optimizer).",
    buckets=(
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
    ),
)

# Cluster metrics
genesis_cluster_nodes_total = Gauge(
    "genesis_cluster_nodes_total",
    "Total number of nodes registered in the Genesis cluster.",
)

genesis_cluster_heartbeat_lag_seconds = Gauge(
    "genesis_cluster_heartbeat_lag_seconds",
    "Seconds since the last heartbeat was received for each node.",
    labelnames=("node_id",),
)

genesis_provenance_edges_total = Counter(
    "genesis_provenance_edges_total",
    "Total number of provenance edges recorded.",
)

genesis_policy_violations_total = Counter(
    "genesis_policy_violations_total",
    "Total number of policy violations detected by governance.",
)

genesis_replay_runs_total = Counter(
    "genesis_replay_runs_total",
    "Number of replay operations executed.",
)

genesis_signature_verifications_total = Counter(
    "genesis_signature_verifications_total",
    "Number of signature verification events.",
    labelnames=("status",),
)

# Cognitive research instrumentation.
genesis_experiments_total = Counter(
    "genesis_experiments_total",
    "Number of experiments executed by the cognition stack.",
    labelnames=("status",),
)

genesis_hypotheses_generated_total = Counter(
    "genesis_hypotheses_generated_total",
    "Number of experiment hypotheses generated by the planner.",
)

genesis_insights_total = Counter(
    "genesis_insights_total",
    "Insights derived from automated research.",
)

genesis_reasoner_latency_seconds = Histogram(
    "genesis_reasoner_latency_seconds",
    "Latency of cognition reasoner responses.",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

genesis_theorist_updates_total = Counter(
    "genesis_theorist_updates_total",
    "Theorist update invocations.",
)

genesis_publications_total = Counter(
    "genesis_publications_total",
    "Number of research publications exported.",
)

genesis_knowledge_nodes_total = Gauge(
    "genesis_knowledge_nodes_total",
    "Number of nodes tracked in the knowledge graph.",
)

# Global adaptation and cosmic coordination instrumentation.
genesis_adaptation_cycles_total = Counter(
    "genesis_adaptation_cycles_total",
    "Number of adaptation cycles executed by the planetary intelligence engine.",
)

genesis_global_energy_mwh = Gauge(
    "genesis_global_energy_mwh",
    "Estimated global energy consumption in megawatt hours.",
)

genesis_latency_mean_ms = Gauge(
    "genesis_latency_mean_ms",
    "Mean latency across planetary services in milliseconds.",
)

genesis_peace_index = Gauge(
    "genesis_peace_index",
    "Composite peace index aggregated from planetary telemetry.",
)

genesis_cosmic_latency_seconds = Histogram(
    "genesis_cosmic_latency_seconds",
    "Latency observations recorded while merging cosmic consensus states.",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 60.0, 120.0),
)

genesis_branches_total = Counter(
    "genesis_branches_total",
    "Cosmic branches propagated through the expansion network.",
)

genesis_chronicle_events_total = Counter(
    "genesis_chronicle_events_total",
    "Chronicle events recorded by the cosmic service.",
)

genesis_information_entropy_ratio = Gauge(
    "genesis_information_entropy_ratio",
    "Entropy ratio observed across cosmic signal propagation.",
)

genesis_reconciliation_cycles_total = Counter(
    "genesis_reconciliation_cycles_total",
    "Reconciliation cycles executed by the propagation service.",
)

genesis_seeds_total = Counter(
    "genesis_seeds_total",
    "Seed launches recorded by the cosmic seed archive.",
)

genesis_vault_records_total = Counter(
    "genesis_vault_records_total",
    "Vault records replicated across the cosmic archive.",
)

# Civilization layer instrumentation.
genesis_federation_peers_total = Gauge(
    "genesis_federation_peers_total",
    "Total number of peers registered in the federation mesh.",
)

genesis_consensus_rounds_total = Counter(
    "genesis_consensus_rounds_total",
    "Number of consensus rounds executed by the federation.",
    labelnames=("state",),
)

genesis_economy_tx_total = Counter(
    "genesis_economy_tx_total",
    "Economy ledger transactions grouped by reason.",
    labelnames=("reason",),
)

genesis_ethics_violations_total = Counter(
    "genesis_ethics_violations_total",
    "Ethics violations detected by the civilization auditor.",
    labelnames=("principle",),
)

genesis_replica_boots_total = Counter(
    "genesis_replica_boots_total",
    "Replica bootstrap operations executed across the federation.",
)

genesis_self_repair_events_total = Counter(
    "genesis_self_repair_events_total",
    "Self repair events triggered by lifecycle management.",
)

genesis_global_energy_mwh = Gauge(
    "genesis_global_energy_mwh",
    "Aggregate energy consumption tracked across the Genesis federation (MWh).",
)

genesis_latency_mean_ms = Gauge(
    "genesis_latency_mean_ms",
    "Mean interconnect latency measured across the metanet fabric (ms).",
)

genesis_peace_index = Gauge(
    "genesis_peace_index",
    "Composite stability index aggregated from planetary law sensors.",
)

genesis_law_cases_total = Counter(
    "genesis_law_cases_total",
    "Planetary law cases processed by the judicial engine.",
)

genesis_exchanges_total = Counter(
    "genesis_exchanges_total",
    "Metanet exchanges synchronized across federations.",
)

genesis_metanet_federations_total = Gauge(
    "genesis_metanet_federations_total",
    "Federations currently connected to the metanet interconnect.",
)

genesis_treaties_active_total = Gauge(
    "genesis_treaties_active_total",
    "Active treaties enforced across the metanet diplomacy layer.",
)

__all__ = [
    "genesis_timeline_commits_total",
    "genesis_recursion_runs_total",
    "genesis_branch_merges_total",
    "genesis_entropy_delta",
    "genesis_continuity_score",
    "genesis_temporal_violations_total",
    "genesis_eval_duration_seconds",
    "genesis_module_score",
    "genesis_replacements_total",
    "genesis_router_selection_total",
    "genesis_canary_promotions_total",
    "genesis_canary_rollbacks_total",
    "genesis_traffic_share",
    "genesis_rl_reward",
    "genesis_rl_update_total",
    "genesis_cosmic_latency_seconds",
    "genesis_adaptation_cycles_total",
    "genesis_reconciliation_cycles_total",
    "genesis_seeds_total",
    "genesis_cache_hits_total",
    "genesis_rate_limit_drops_total",
    "genesis_orch_decision_duration_seconds",
    "genesis_cluster_nodes_total",
    "genesis_cluster_heartbeat_lag_seconds",
    "genesis_provenance_edges_total",
    "genesis_policy_violations_total",
    "genesis_replay_runs_total",
    "genesis_signature_verifications_total",
    "genesis_experiments_total",
    "genesis_hypotheses_generated_total",
    "genesis_insights_total",
    "genesis_reasoner_latency_seconds",
    "genesis_theorist_updates_total",
    "genesis_publications_total",
    "genesis_knowledge_nodes_total",
    "genesis_federation_peers_total",
    "genesis_consensus_rounds_total",
    "genesis_economy_tx_total",
    "genesis_ethics_violations_total",
    "genesis_replica_boots_total",
    "genesis_self_repair_events_total",
    "genesis_global_energy_mwh",
    "genesis_latency_mean_ms",
    "genesis_branches_total",
    "genesis_chronicle_events_total",
    "genesis_information_entropy_ratio",
    "genesis_vault_records_total",
    "genesis_peace_index",
    "genesis_law_cases_total",
    "genesis_exchanges_total",
    "genesis_metanet_federations_total",
    "genesis_treaties_active_total",
    "genesis_reflexive_cycles_total",
    "genesis_simulations_total",
    "genesis_reflection_confidence_mean",
    "genesis_uncertainty_metrics_total",
    "genesis_twin_sync_latency_seconds",
    "genesis_meta_anomalies_total",
]

