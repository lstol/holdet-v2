# engine/ev/

Layer 4 — Expected Value computation.

EV = Σ(P(outcome) × payoff(outcome)) over all events in 03_outcome_space.md.

## Inputs
- Layer 3 probability outputs
- 02_rules_payoff.md payoff structure

## Outputs
- Per-rider per-stage EV with full line-item breakdown
- CaptainPositiveValueGrowth EV
- StageDepthCount EV
- TransferFeeApplied (deterministic)

## Constraints
- EV outputs must not feed back into any upstream layer
- No simulation, sampling, or runtime learning
- Strictly deterministic given fixed inputs
