# engine/

Layer 2–4 computation and System Integrity Validator. Implements the contracts defined in `contracts/v2.0/04_layers.md` and `05_execution_and_validation.md`.

| Subfolder | Layer | Role |
|-----------|-------|------|
| `interaction/` | Layer 2 | Terrain fit diagnostics, fatigue indicators, capability-condition matching |
| `probability/` | Layer 3 | Outcome distributions over Outcome Space |
| `ev/` | Layer 4 | EV computation from probabilities and payoff structure |
| `siv/` | SIV | Pre-execution structural validation |

## Execution order
S0 → SIV → S1 → S2 → interaction → probability → ev → S4

No layer may be invoked out of order.
