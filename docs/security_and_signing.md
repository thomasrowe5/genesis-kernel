# Security and Signing

## API Security

- JWT / API keys are validated through the `RBACManager`. API keys are hashed via
  bcrypt with unique salts before storage. The FastAPI dependency `require_role`
  enforces role membership for protected routes.
- Default credentials can be injected via `GENESIS_API_KEY_ID`,
  `GENESIS_API_KEY_SECRET`, and `GENESIS_API_KEY_ROLES` environment variables.

## Signing Workflow

1. Create or modify a module implementation.
2. Run `genesis sign <module> <version>` to generate a signature JSON file.
3. Distribute the signature alongside the module package.
4. On deployment, run `genesis verify path/to/signature.json` to ensure integrity.

Example CLI output:

```
$ genesis sign fibonacci v2
signature=5c2f... path=fibonacci-v2.signature.json
$ genesis verify fibonacci-v2.signature.json
verification=success
```

## Hash Chain

Each signature embeds the previous hash in the lineage, forming a hash chain.
This enables tamper detection: if any intermediary signature is modified, the
next verification fails.

## Audit Logging

- Policy and provenance changes are logged in JSON with node identifier,
  signature hash, and signer ID.
- Prometheus metrics:
  - `genesis_signature_verifications_total{status="success"}` counts successful
    verifications.
  - `genesis_policy_violations_total` tracks governance incidents.

## Secure Storage

Store signature files and API keys in encrypted secrets managers. The signer
secret used by the CLI is configured through `GENESIS_SIGNING_SECRET` and is used
for HMAC-based signatures.
