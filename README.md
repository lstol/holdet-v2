# Holdet v2

Contracts-first cycling outcome modeling system for Holdet tournament decision support.

## Structure

| Folder | Phase | Purpose |
|--------|-------|---------|
| `contracts/v2.0/` | ✅ Done | 6-file architecture contracts — read-only |
| `data/` | Phase 2 | Raw inputs: riders, stages, odds, outcomes, snapshots |
| `models/` | Phase 3–4 | Baseline rule model → trained probability models |
| `engine/` | Phase 3–4 | Layer 2–4 computation + SIV |
| `decisions/` | Phase 5 | Per-stage output records and override logs |
| `interface/` | Phase 3 + 6 | Early inspection UI → operational dashboard |
| `runs/` | Ongoing | Execution run logs and GBC records |
| `competition/` | Ongoing | Competition protocol and per-stage comparison artifacts |
| `notes/` | Ongoing | Governance logs and post-stage reviews |

## Contracts

All architecture is defined in `contracts/v2.0/`. These files are the single source of truth. Do not modify without governance approval.

## Roadmap

See `competition/roadmap.md` for full phase breakdown.
