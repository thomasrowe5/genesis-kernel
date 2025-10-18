# Causality and Continuity

Maintaining causal integrity in Genesis requires continuous measurement of divergence between predicted and actual states. Phase 10 introduces a continuity loop that quantifies drift, verifies ethical constraints, and reports temporal health in real time.

## Continuity Enforcer

The `ContinuityEnforcer` aggregates a set of Prime Ethic principles and evaluates candidate futures against a baseline snapshot. It inspects numeric metrics and declared violations to compute a `ContinuityStatus`:

- `score`: normalized continuity rating, capped at 1.0 for perfect alignment.
- `delta`: aggregate magnitude of metric drift.
- `violations`: list of failed invariants, including any ethic clauses when breached.

A branch can only merge back into the primary timeline when `status.is_consistent` is `True`, ensuring ethical compliance.

## Reconciliation Metrics

The `TemporalReconciler` flattens both actual and predicted states, producing per-metric deltas. Every reconciliation updates two observability feeds:

- `genesis_continuity_score` gauge captures the latest alignment score.
- `ContinuityMetric` SQLModel table (or in-memory fallback) persists historical continuity snapshots.

These metrics power dashboards showing long-term stability of the temporal core.

## Temporal Alerts

The `TemporalObserver` translates entropy breaches and loop detections into `TemporalAlert` records. Each alert increments `genesis_temporal_violations_total`, enabling alerting pipelines to halt unsafe projections.

Together, the enforcer, reconciler, and observer create a closed causal loop where every prediction is stress-tested before influencing Genesis.
