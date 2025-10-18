# Genesis Kernel

Genesis is a modular experimentation kernel that now supports a closed self-optimization loop.

## Phase 2 – Evaluation Loop and Self-Optimization

Phase 2 introduces an evaluator service, reinforcement-learning powered optimizer, and a persistent module registry. Together these services:

- Discover candidate modules under `src/genesis/modules/`.
- Execute declarative benchmarks stored in `benchmarks/*.yaml` using the AutoTest Cloud client.
- Compute rewards from accuracy, latency, and stability metrics.
- Promote higher scoring variants and route traffic via PromptMesh.
- Expose observability primitives through Prometheus metrics and a FastAPI leaderboard endpoint.

### Key Commands

```bash
poetry run genesis eval --module fibonacci
poetry run genesis leaderboard
poetry run genesis promote --module fibonacci --version v2
```

### API

Mount `genesis.api.routes.modules.router` inside the FastAPI application to surface `/modules/leaderboard`.

### Telemetry

The evaluator emits Prometheus histograms (`genesis_eval_duration_seconds`), gauges (`genesis_module_score{module,version}`), and replacement counters (`genesis_replacements_total`). Wire these into Grafana to visualise the top-performing modules.

### Further Reading

See [`docs/self_optimization.md`](docs/self_optimization.md) for reward function details and future roadmap items.
