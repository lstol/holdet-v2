# notes/reviews/

Post-stage review records.

## File naming
`review_{race_id}_stage{N}.md`

## Contents
- Outcome accuracy (predicted vs actual per Outcome Space event)
- EV accuracy (predicted vs realized per rider)
- Assumption audit (which held, which failed, why)
- System A vs System B realized performance
- Flags for governance (if pattern warrants review)

## Constraint
Review findings feed governance only. Single-stage findings cannot trigger model updates.
