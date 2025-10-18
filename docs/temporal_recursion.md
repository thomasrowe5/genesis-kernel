# Temporal Recursion Engine

Genesis Phase 10 introduces a temporal core that continuously records, simulates, and reconciles state evolution. The workflow combines deterministic timeline commits with counterfactual simulations and reconciliation loops to maintain causal integrity.

## Components

- **Timeline Manager** — captures every state transition with monotonic vector clocks and content hashes.
- **Temporal Recursion Scheduler** — replays historical snapshots through seeded simulators to explore alternate futures.
- **Temporal Observer** — guards against entropy spikes and temporal loops, emitting alerts when safety bounds are crossed.
- **Temporal Reconciler** — compares predicted trajectories against the actual timeline and updates continuity metrics.
- **Temporal Branch Manager** — tracks forked futures and governs merges back into the primary history.

## Versioned History

Each snapshot is stored as a `TimelineCommit` record with:

- `vector_clock`: Lamport-style logical clock guaranteeing causal ordering.
- `hash`: SHA-256 digest of the canonical state payload.
- `state_json`: serialized twin state used for future simulations and audits.

The `genesis_timeline_commits_total` counter reflects total recorded commits for observability dashboards.

## Simulation Loop

1. Select a historical commit by ID or timestamp.
2. Run the recursion scheduler with a deterministic simulator to generate a predicted state.
3. Feed the prediction into the reconciler to compute continuity deltas.
4. Optionally materialize the prediction as a new commit when continuity holds.

The recursion scheduler exposes metrics via `genesis_recursion_runs_total{status}` to differentiate successful and halted simulations.

## Temporal Safeguards

- Entropy deltas are captured in `genesis_entropy_delta` and capped by the observer to prevent chaotic divergence.
- Any detected loop or entropy breach triggers `genesis_temporal_violations_total` and blocks projection commits.

This temporal stack underpins causal continuity by ensuring every prediction is validated before it can influence the live Genesis state.
