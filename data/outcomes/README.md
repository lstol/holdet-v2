# data/outcomes/

Historical race outcome archive. Used for parameter training only.

## Current files

| File | Races | Years | Records | Notes |
|------|-------|-------|---------|-------|
| `outcomes_grand_tours_2020_2025.json` | Giro, Tour, Vuelta | 2020–2025 | Partial sample | Run fetch script for full archive |

## Fetch script
`fetch_outcomes.py` — scrapes ProCyclingStats for the full archive.

```bash
# Fetch everything (all 3 races, 2020-2025):
python3 data/outcomes/fetch_outcomes.py --all

# Fetch single race/year:
python3 data/outcomes/fetch_outcomes.py --race giro --year 2024
```

Expected full archive: ~45,000–60,000 records (3 races × 6 years × 21 stages × ~150 riders).

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
