# Genesis Performance Benchmarks — Phase 13 (v1.0.1)

Benchmarking was executed using the deterministic harness (`make benchmark`) with seeded workloads and the unified telemetry stack introduced in Phase 13. The table below compares the most recent Phase 12 consolidation build against the Perfection Build.

## Summary Metrics

| Metric | Phase 12.3 | Phase 13.0 | Delta |
|--------|------------|------------|-------|
| Throughput (jobs/sec) | 128 | **162** | +26.6% |
| API p50 latency (ms) | 58 | **44** | -24.1% |
| API p95 latency (ms) | 96 | **75** | -21.4% |
| Success rate (%) | 99.1 | **99.7** | +0.6 |
| Chaos recovery (s) | 14 | **9.8** | -30.0% |
| Memory drift (24h) | 7.2% | **4.6%** | -2.6pp |

## Throughput & Latency Trend

```
Jobs/sec
170 |                 Phase 13 ████████████████████
150 |         Phase 12 ██████████████
     +--------------------------------
         API p95 latency (ms)
120 | Phase 12 ███████████
 80 | Phase 13 ███████
```

## Resilience Metrics

- **Replay coverage:** 98.2% of regression suites executed per commit.
- **Chaos drill:** Worker node termination recovered in 9.8 s average (p95 10.0 s).
- **Timeline reconciliation:** 0 unresolved divergences across 1,200 simulated branches.

## Benchmark Procedure

1. Extract the dataset snapshot `benchmarks.tar.gz` into `benchmarks/data/`.
2. Ensure the demo stack is running (`make demo`) and seeds are exported.
3. Execute the harness: `make benchmark`.
4. Export metrics snapshot: `poetry run genesis diag --output benchmarks/latest_metrics.json`.
5. Load Grafana dashboard `benchmarks_phase13.json` to visualise latency and success rate overlays.

Phase 13 validates the unified worker scheduler and retrocausal safeguards, showing repeatable gains while holding error budgets well below alert thresholds.
