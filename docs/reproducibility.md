# Genesis Reproducibility Playbook (v1.0.1)

This guide documents how to regenerate the Phase 13 benchmarks, replay experiments, and validate releases for the Genesis Perfection Build.

## Deterministic Environment

1. **Toolchain Lock** – Install dependencies via `make install`. Poetry pins Python packages in `poetry.lock`.
2. **Python Version** – Use CPython 3.11.8. Validate with `python --version`.
3. **Environment Hash** – Capture `$(git rev-parse HEAD)` and `$(poetry env info --path)` to embed in reports.
4. **Container Snapshot** – Optional Docker image: `ghcr.io/genesis/kernel:v1.0.1` built from this commit.

## Dataset & Artefact Snapshots

- **Benchmark datasets** – Pull `s3://genesis-artifacts/v1.0.1/benchmarks.tar.gz` and unpack into `benchmarks/data/`.
- **Governance policies** – Verify `src/genesis/governance/policies.json` checksum matches release manifest.
- **Timeline baseline** – Capture a fresh snapshot after seeding data using `poetry run genesis snapshot` (outputs commit ID and hash).

## Seed Management

Use deterministic seeds for repeatability:

```bash
export GENESIS_RANDOM_SEED=1337
export GENESIS_EVALUATOR_SEED=20250815
export GENESIS_OPTIMIZER_SEED=314159
```

Record the seeds in experiment metadata before running any benchmarks or cognition plans.

## Benchmark Reproduction Steps

1. Ensure Redis/Postgres containers are running (`make demo`).
2. Load dataset snapshot and seeds as above.
3. Execute `make benchmark` to run the Phase 13 suite.
4. Export diagnostics: `poetry run genesis diag --output repro/metrics.json`.
5. Compare results with reference file `benchmarks/reference_phase13.json` using `jq` or custom diffing.
6. Optionally replay the most recent plan via API (`POST /cognition/cognition/run`) to validate end-to-end loops.

## Continuous Integration Matrix

Genesis CI validates reproducibility across the following matrix:

| OS | Python | Tooling |
|----|--------|---------|
| Ubuntu 22.04 | 3.11 | Poetry 1.7, Docker 24, Redis 7, Postgres 14 |
| macOS 14 (arm64) | 3.11 | Poetry 1.7, Colima 0.6, Redis 7, Postgres 14 |
| Windows Server 2022 | 3.11 | Poetry 1.7, WSL2 Docker Desktop, Redis 7, Postgres 14 |

Each job executes linting, unit tests, `make benchmark`, and documentation builds to ensure parity.

## Verification Checklist

- [ ] Git revision and Poetry environment hash captured in artefact metadata
- [ ] Seeds exported in CI logs
- [ ] Benchmark output diffed against reference snapshot (tolerance ±1%)
- [ ] Chaos recovery drill executed by terminating a worker pod and observing `poetry run genesis diag` recovery metrics
- [ ] Documentation regenerated (`make docs`) with no warnings

Following this playbook guarantees any team can reproduce Phase 13 performance claims and validate the Genesis Perfection Build.
