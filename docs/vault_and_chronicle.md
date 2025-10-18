# Archivum: Vault and Chronicle

Genesis now treats archival stewardship as a first-class system. The Archivum
subsystem provides error-tolerant storage and immutable history suitable for
million-year horizons.

```text
+-------------------+     +-------------------+
|   VaultStore      | --> |  VaultRetrieval   |
|  parity encode    |     | verify + restore  |
+-------------------+     +-------------------+
          |                          |
          v                          v
   Parity files            ChronicleLedger
          |                          |
          v                          v
   Cold storage        Tamper-evident events
```

* `VaultStore` persists payloads with XOR-style parity blocks allowing recovery
  from media loss while retaining constant-time verification.
* `VaultRetrieval` validates each read and raises if parity cannot repair the
  payload, ensuring silent corruption never propagates.
* `ChronicleLedger` serializes every major event (seed launch, branch genesis,
  convergence, snapshots) to an append-only hash chain stored alongside parity
  files.

These components integrate with Prometheus counters (`genesis_vault_records_total`,
`genesis_chronicle_events_total`) to surface archival health within Grafana.
