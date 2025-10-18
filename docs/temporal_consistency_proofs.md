# Temporal Consistency Proofs

Retrocausal adjustments must guarantee causal closure. The consistency module maintains a hash-chained ledger proving that every retroactive change remains within the reversible tolerance.

## Hash Chain Structure

```
run_n_payload = [deltas..., reward_delta, entropy_delta, valid_flag]
run_n_hash    = sha256(json(run_n_payload) + previous_hash_bytes)
```

* Each reverse simulation emits reward and entropy deltas for the touched commits.
* The inference engine converts those deltas into gradients for the present step.
* `consistency.py` verifies that the gradient magnitude does not exceed the reward delta plus tolerance \(ε\).
* The resulting payload is hashed together with the previous proof, forming a tamper-evident chain.

If any update exceeds the tolerance, the verifier rejects the change, increments the paradox prevention counter, and leaves the prior chain untouched.

## Exposure

* **CLI** – `genesis retro verify` prints the latest hash and exposes whether the ledger is populated.
* **API** – `GET /retrocausal/consistency` returns the current tip hash.
* **Metrics** – `genesis_retro_consistency_score` gauges the latest verification outcome.

These proofs enable bidirectional optimisation without violating the recorded cosmic chronicle.
