# Genesis Unified API Reference

The unified API gateway is defined in `src/genesis/api/main.py` and aggregates routers for
all subsystems. Endpoints are grouped under domain-specific prefixes.

## Base URLs
- **OpenAPI schema**: `/openapi.json`
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

## Route Groups

| Prefix | Routers | Description |
| ------ | ------- | ----------- |
| `/core` | modules, cache | Module registry information and cache controls |
| `/cognition` | cognition | Experiment planning and researcher workflows |
| `/reflexion` | reflexion | Digital twin state and self-reflection APIs |
| `/temporal` | temporal | Timeline controls, reconciliation, and observers |
| `/governance` | provenance | Provenance queries and signature validation |
| `/router` | orchestration, federation | Optimizer → router orchestration pipelines |
| `/cosmic` | cosmic, metanet, cluster | Federation, metanet, and cluster controls |

## Authentication

API requests must include a bearer token formed as `<key_id>:<secret>`. The default RBAC roles
are defined inside `src/genesis/governance/policies.json` and enforced via `require_role` in
the API gateway.

For local development you can seed a key by exporting the following environment variables:

```bash
export GENESIS_API_KEY_ID=local-admin
export GENESIS_API_KEY_SECRET=local-secret
export GENESIS_API_KEY_ROLES=viewer,operator,governor
```

## Health Endpoints
- `GET /health/live`
- `GET /health/ready`

Both endpoints require at least the `viewer` role and expose environment, database, and Redis
status information.

## Generating Documentation

Run the CLI to rebuild static documentation:

```bash
poetry run genesis docs build
```

This produces a static HTML site inside the configured documentation build directory.
