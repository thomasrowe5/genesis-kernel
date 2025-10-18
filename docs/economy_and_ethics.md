# Economy and Ethics

The economy subsystem rewards useful computation with `genesis_credits` while
charging for network and storage consumption. Credits are stored in the
`EconomyTx` ledger table. The CLI exposes `genesis ledger show` which retrieves a
`LedgerSnapshot` to display balances and transactions.

```
Task Complete --> credit_peer(peer_id, amount) --> EconomyTx(to_id=peer_id)
Task Request --> debit_peer(peer_id, amount) --> EconomyTx(from_id=peer_id)
```

Balances are derived by folding credits and debits for each peer. Prometheus
tracks activity via the `genesis_economy_tx_total{reason}` counter which powers
Grafana panels showing inflow/outflow volume. Epoch reconciliation simply
replays the ledger to assert that no peer exceeds the configured credit cap.

## Ethics Pipeline

The ethics layer defines the following core principles:

* **Safety** – avoid harmful behaviour and infrastructure misuse.
* **Fairness** – prevent biased allocation of credits or compute.
* **Transparency** – ensure decisions emit auditable metadata.

The `EthicsAuditor` evaluates events against severity thresholds. Violations are
recorded in the `EthicsEvent` table and increment the
`genesis_ethics_violations_total{principle}` counter.

```
Event --> EthicsAuditor.evaluate --> EthicsFinding --> EthicsTribunal.adjudicate
                                            |                         |
                                            v                         v
                                     PBFT Proposal           Consensus Vote
```

The `EthicsTribunal` promotes findings into formal proposals and executes
consensus votes to decide on remediation actions. Approved verdicts can trigger
credit adjustments or replication lifecycle changes depending on policy.
