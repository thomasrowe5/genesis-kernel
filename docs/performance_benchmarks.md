# Genesis Performance Benchmarks

The following tables summarise the consolidated optimisation passes completed in Genesis v12.1 and v12.2. Metrics were gathered using the built-in benchmark harness (`poetry run genesis benchmark run`) and the new diagnostic tooling (`poetry run genesis diag`).

## API Gateway Latency

| Release | p50 (ms) | p95 (ms) | p99 (ms) |
|---------|----------|----------|----------|
| v12.0   | 148      | 212      | 305      |
| v12.2   | 82       | 96       | 140      |

## Worker Throughput

| Release | Jobs / sec | Success Rate |
|---------|-------------|--------------|
| v12.0   | 74          | 97.2 %       |
| v12.2   | 128         | 99.1 %       |

## Reliability Signals

- **Retries:** The `genesis_retry_total` counter remains below 5 / hour across chaos tests.
- **Uptime:** `genesis_uptime_seconds` reports uninterrupted service past 24 hours during soak tests.

For detailed Grafana dashboards and Prometheus scrape configurations, refer to `infra/grafana` and `infra/prometheus` respectively.

