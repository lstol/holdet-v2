# data/odds/

External benchmark snapshots only.

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
