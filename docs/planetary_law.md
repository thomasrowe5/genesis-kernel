# Planetary Law and Governance

Genesis Phase 7 introduces a codified planetary charter, distributed court, and
sanctions engine.  These subsystems ensure autonomous federations cooperate
peacefully while retaining transparency and accountability.

## Charter Ontology

Articles are managed by `GlobalCharter` and persisted using the SQLModel
stand-ins defined in `genesis.metanet.models`.  Each article captures:

- `identifier` – stable handle for references in treaties and sanctions.
- `title` and `text` – human-readable content.
- `version` – incremented on amendments.
- `active` – flag indicating current applicability.

## Court Operations

The `PlanetaryCourt` uses a deterministic PBFT stub that evaluates disputes
according to a consensus digest.  Verdicts with an "approve" outcome are marked
as enforceable and increment the `genesis_law_cases_total` counter.  Court cases
can be exported to the SQLModel `CourtCase` table for archival storage.

### Peace Index Formula

The global peace index is derived from treaty activity and disputes:

```
peace_index = 100 * treaties_active / max(1, treaties_active + disputes)
```

The value is clamped to the range [0, 100] and exported through the
`genesis_peace_index` gauge.

## Sanctions

When the court rules against a federation the `SanctionsEngine` executes a
credit penalty via the exchange ledger.  Credits flow to the
`planetary-treasury` federation using an atomic swap with asset type `sanction`.
Ledger proofs guarantee tamper evidence, preventing double-spend attempts.
