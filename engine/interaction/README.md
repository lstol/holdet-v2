# engine/interaction/

Layer 2 — Interaction computation.

Combines Layer 0 (Rider-Intrinsic) and Layer 1 (Race-State) into per-rider, per-stage diagnostics.

## Output types
- Terrain fit diagnostic (not a cross-rider score)
- Fatigue condition indicator
- Capability-condition mismatch flags

## Constraints
- No scalar outputs that produce a ranking across the rider set
- No probability estimates
- No persistence beyond current execution scope
- Inputs validated by SIV before this layer runs
