# runs/

Execution run logs and Governance Binding Certificate records. One folder per run.

## Folder naming convention
`{race_id}_stage{N}_run{R}_{timestamp}/`

## Contents per run folder
- `gbc.json` — Governance Binding Certificate for this run
- `siv_result.json` — SIV PASS/FAIL record
- `execution_log.md` — S0→S4 state machine trace
- `outputs/` — frozen output artifact

## Constraints
- Run folders are immutable once execution completes
- GBC must exist before S1 begins
- SIV result must be PASS before S2 begins
