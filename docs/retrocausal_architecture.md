# Retrocausal Architecture

Genesis Phase 11 introduces a retrocausal inference layer that complements the temporal engine established in Phase 10. The new layer replays stored timeline commits in reverse order, computes reversible deltas, and feeds the resulting gradients into a bidirectional optimisation loop.

## Component Stack

```
+------------------------------+
| Retrocausal Bridge          |
|  + ReverseSimulator         |
|  + Inference Engine         |
|  + Consistency Verifier     |
+------------------------------+
           ^           |
           |           v
+------------------------------+
| Timeline Repository          |
|  (commit stream from Phase10)|
+------------------------------+
```

1. **reverse_sim.py** replays recorded commits as reversible trajectories.
2. **inference.py** derives reverse-time gradients via finite differences.
3. **consistency.py** chains cryptographic proofs around each adaptation.
4. **bridge.py** keeps the forward and reverse signals synchronised.

## Bidirectional Loop

The bridge maintains a reversible loop:

1. Pull commits between the requested boundaries.
2. Execute the reverse simulation to identify entropy and reward deltas.
3. Run the inference engine to compute gradient hints for the present state.
4. Validate the update against the tolerance budget and extend the proof chain.
5. Emit telemetry for Prometheus and expose the results via API/CLI.

This loop ensures that reverse adjustments never break the observable timeline while still informing the forward optimiser.
