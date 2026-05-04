# data/snapshots/

T0 execution snapshots. One per stage per run. Immutable once written.

## File naming convention
`snapshot_{race_id}_stage{N}_run{R}_{T0_timestamp}.json`

## Contents
- frozen rider universe (prices, statuses)
- frozen Race-State
- frozen odds reference (filename only — not the odds data itself)
- bank balance at T0
- current team composition at T0
- GBC version reference

## Constraints
- Files are write-once. No updates after creation.
- Both systems must reference identical snapshot file for a given stage.
- Snapshot filename is declared in the GBC.
