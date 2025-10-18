# Genesis Kernel

![Status: v1.0.1 – Perfection Build](https://img.shields.io/badge/Status-v1.0.1%E2%80%93Perfection%20Build-4c1.svg)

Genesis is a unified, self-optimising AI infrastructure kernel that orchestrates cognition, evaluation, optimisation, and governance under a single control plane. Phase 13 completes the "Perfection Build" by consolidating every subsystem behind a consistent FastAPI gateway, observability fabric, and policy-aware worker fleet. The platform continuously learns from live traffic, curates canonical experiment trails, and feeds discoveries back into its optimisation loops.

The kernel pairs deterministic orchestration with reflexive autonomy. Governance, provenance, and temporal safety nets ensure that every optimisation, benchmark, and deployment remains auditable, reproducible, and reversible. Phase 13 delivers the final polish: harmonised APIs, deterministic rollouts, and near-instant chaos recovery while preserving the experimental agility that defined earlier phases.

## Quickstart

```bash
# Install dependencies and lock the toolchain
make install

# Launch the local demo stack (API gateway, worker, Redis, Postgres, Prometheus)
make demo

# Enqueue a sample optimisation benchmark and stream live diagnostics
poetry run genesis benchmark run
poetry run genesis diag
```

Once the stack is running, visit `http://localhost:8000/docs` for the live API explorer and `http://localhost:9000/metrics` for Prometheus telemetry.

## Documentation

- [Full Documentation Portal](https://example.com/genesis) – architecture, operations, and governance guides
- [Performance Benchmarks](docs/performance_benchmarks.md) – Phase 13 throughput and latency analysis
- [Operations Manual](docs/operations_manual.md) – deployment, monitoring, and troubleshooting recipes
- [Research Whitepaper](docs/research_whitepaper.md) – engineering principles and validation study

For change history and release highlights see [CHANGELOG.md](CHANGELOG.md).
