# data/riders/

Layer 0 — Rider-Intrinsic snapshots.

## File naming convention
`riders_{race_id}_{version}.json`
Example: `riders_giro2026_v1.json`

## Contents per rider
- physiological capacity proxies
- terrain affinity profile
- consistency profile
- recovery dynamics
- data provenance (source, timestamp, exclusion window compliance)

## Constraints
- All data must predate the exclusion window relative to race start
- No race outcome data permitted regardless of age
- Version must be declared in the GBC before execution
