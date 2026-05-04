# data/stages/

Layer 1 — Race-State stage profiles.

## File naming convention
`stages_{race_id}.json`
Example: `stages_giro2026.json`

## Contents per stage
- stage number, name, date
- distance, elevation profile
- terrain classification (flat / hilly / mountain / ITT / TTT)
- designated sprint locations and IDs
- designated KOM locations, IDs, and categories
- TTT flag (boolean)
- weather snapshot (at T0)

## Constraints
- Weather must be snapshotted at T0 — no live updates after freeze
- Stage profiles are read-only during execution
