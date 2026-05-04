# models/v1/

Phase 4 — First trained probability model.

## Model targets (per 03_outcome_space.md)
- StageFinishPosition distribution
- GCPosition trajectory
- SprintPoint / KOMPoint expectations
- FinishStatus (DNF/DNS risk)

## Contents
- `params/` — versioned parameter files
- `version.json` — training data reference, exclusion window version, training date
- `training/` — training scripts (not runtime artifacts)

## Constraints
- No EV outputs in training data
- No odds as features or labels
- Parameters frozen at execution boundary
- version.json must be referenced in GBC
