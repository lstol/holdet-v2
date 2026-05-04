# data/odds/

External benchmark snapshots only.

## Current files

| File | Stage | Status |
|------|-------|--------|
| `odds_giro2026_stage1_T0.json` | Stage 1 | Template (empty) |

## Snapshot script
`engine/siv/odds_snapshot.py` — capture bookmaker odds at T0 before each stage.

```bash
# Capture live odds (may be blocked by anti-bot):
python3 engine/siv/odds_snapshot.py --stage 7

# Use manually saved page HTML (recommended):
python3 engine/siv/odds_snapshot.py --stage 7 --html-file /tmp/stage7_odds.html --source oddschecker
```

Files are excluded from git by `.gitignore` (runtime snapshots). Commit templates explicitly with `git add -f`.

## File naming convention
`odds_{race_id}_stage{N}_{T0_timestamp}.json`

## Contents
- stage win implied probabilities per rider
- top-3 / top-10 implied probabilities per rider
- source bookmaker identifier
- snapshot timestamp

## CRITICAL CONSTRAINT
Odds data must never be used as:
- a Layer 3 model feature
- a training label
- a calibration target
- an automatic parameter adjustment signal

Permitted use: human-facing divergence signal only.
Large divergence between model output and implied odds triggers human review — not automatic model update.
