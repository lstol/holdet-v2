# engine/probability/

Layer 3 — Probability computation.

Produces valid probability distributions over Outcome Space events for each rider and stage.

## Constraints
- Input: Layer 2 outputs only
- No direct dependency on Layer 0, Layer 1, or Layer 4
- No simulation at runtime
- No stochastic sampling at runtime
- Parameters fixed before execution boundary
- All distributions must be explicit and inspectable
