# Contributing to Genesis

Thank you for your interest in contributing! Genesis Phase 12 emphasises quality, safety, and
reproducibility. Please review the following guidelines before submitting changes.

## Development Workflow
1. Fork the repository and create a feature branch.
2. Ensure commit signing is enabled (`git config commit.gpgsign true`).
3. Run formatting and tests:
   ```bash
   poetry run ruff check .
   poetry run mypy --strict src
   poetry run pytest --cov=src/genesis --cov-report=term-missing
   ```
4. Add or update documentation in `docs/`.
5. Submit a pull request summarising the change and referencing related issues.

## Coding Standards
- Use type hints throughout new Python code.
- Prefer dependency injection through `GenesisSettings` rather than hard-coded environment
  lookups.
- Emit structured logs via `configure_logging` where appropriate.

## Reporting Issues
Open a GitHub issue with reproduction steps, expected behaviour, and environment details.
Security issues should be reported privately to `security@genesis.local`.

## Release Process
The `genesis release create` CLI command prepares changelog entries and metadata. Releases
require governance sign-off and successful CI runs across linting, type checking, tests,
docker builds, and documentation generation.
