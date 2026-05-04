# models/baseline/

Phase 3 — Rule-based probability baseline. No machine learning. Fully inspectable logic.

## Purpose
Produce real Outcome Space distributions from historical base rates and terrain affinity — good enough to drive an EV table and test the full pipeline before a trained model exists.

## Contents
- `rules.py` — probability assignment logic
- `params/` — base rate tables per outcome type and stage type
- `version.json` — parameter version manifest

## Constraints
- No learned weights
- No simulation outputs
- All logic must be expressible as explicit functions of Layer 2 outputs and fixed tables
