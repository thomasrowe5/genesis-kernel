# Self Modeling and Uncertainty

The reflexive layer cultivates a continuously updated *digital twin* that mirrors registries, metrics, and configuration. Each snapshot is persisted through `TwinSnapshot` records when SQLModel is available, ensuring historical replay of the system's evolution.

Uncertainty management is performed by the `UncertaintyTracker`, which maintains streaming statistics for every metric that the twin observes. The tracker provides:

- Running mean and standard deviation using numerically stable Welford updates.
- A global confidence score derived from the inverse of dispersion across metrics.
- Exportable `UncertaintyMetric` entries surfaced via the `/reflexion/uncertainty` API and the `genesis uncertainty` CLI command.

```text
Observation ──▶ Tracker.update(key, value)
                 │
                 ├─▶ Confidence(key)
                 ├─▶ Global Confidence
                 └─▶ Metrics Export
```

Meta-cognitive introspection feeds simulation outputs and sandbox observations back into the tracker, detecting drift or epistemic instability. When confidence falls below thresholds, validators halt automation and surface actionable anomalies to operators and downstream agents through the self-query interface.
