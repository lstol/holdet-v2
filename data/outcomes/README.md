# data/outcomes/

Historical race outcome archive. Used for parameter training only.

## File naming convention
`outcomes_{race_id}.json`

## Contents per stage
- StageFinishPosition (all finishers)
- GCPosition (after each stage)
- JerseyHold (per jersey type)
- SprintPoint (per sprint location)
- KOMPoint (per climb)
- FinishStatus (FINISH / DNF / DNS / DSQ)
- LateArrivalMinutes (per finishing rider)
- TeamPodium events

## Constraints
- Outputs from this system must not be written back here
- Used for training only — not as runtime inputs
