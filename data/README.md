# data/

Raw inputs only. All files versioned and snapshotted. No derived or system-generated data here.

| Subfolder | Contents | Layer |
|-----------|----------|-------|
| `riders/` | Layer 0 snapshots — rider-intrinsic attributes, versioned per race | Layer 0 |
| `stages/` | Race-State profiles — elevation, classification, TTT flag, weather | Layer 1 |
| `odds/` | Pre-stage bookmaker snapshots — benchmark signal only, not model input | External |
| `outcomes/` | Historical result archive — StageFinishPosition, GCPosition, jerseys, etc. | Training |
| `snapshots/` | T0 execution snapshots — frozen inputs per stage per run | Execution |

## Constraints
- No file in `riders/` may contain data within the exclusion window
- No file in `odds/` may be used as a Layer 3 input or training feature
- All files in `snapshots/` are immutable once written
