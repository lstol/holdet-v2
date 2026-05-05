# Phase 3 Summary — Holdet v2 / Giro d'Italia 2026
# Written: 2026-05-08

## Overview

Phase 3 ran from May 5–8 and was split into five sub-phases as scope expanded
and modeling errors were discovered. This is the definitive account.

## Phase 3a — Stage 1 dashboard
Minimal viable dashboard: 8-rider team, 3-stage EV, captain recommendation.
Team: Milan ★, Groenewegen, De Lie, Groves, Mozzato, Gudmestad, De Buyst, Hoelgaard.
Budget: exactly 50,000,000 kr.

## Phase 3b — EV model, optimizer, risk profiles
Six-component EV model (stage_finish, gc, jersey, sprint_kom, team_bonus, captain_bonus).
Multi-stage transfer-aware optimizer. StageDepthCount bonus at team level.
Conservative / Balanced / All-In risk profiles.
21 stage images parsed via Anthropic vision API for sprint/KOM locations.
Pre-computed ev_breakdown_stage{1–21}.json for all active riders.

## Phase 3c — Scoring fixes
Five errors corrected: roadbook sprint/KOM points, GC EV on flat stages,
captain bonus formula (E[max(ΔV,0)] not 0.6× multiplier), base64 image
embedding in dashboard, KOM category point scales (HC/1/2/3/4 table).
Milan S1 sprint_kom: 1,242 → 51,858 kr. Milan S1 GC EV: 0 → 16,480 kr.

## Phase 3d — Rider intelligence + probability recalibration
Synthetic Phase 2a attributes replaced by Copilot-researched data for full field
(data/external/riders_copilot.json, ingested via scripts/ingest_copilot_attributes.py).
Override system with three-tier priority: manual (3) > expert_intel (2) > copilot (1).
Contender pool corrected: 45 synthetic → ~12 genuine sprint contenders.
Manual calibrations: Milan 0.96, Groenewegen 0.88 (relative to this field).
load_rider_attributes() updated: PRIORITY-sorted application, mode:adjust (additive,
clamped [0,1]), mode:replace (exact), stage_last_applicable scoping, _overridden tracking.
One-command rebuild: python3 scripts/apply_corrections_and_rebuild.py.

## Phase 3e — Expert intelligence pipeline
Pre-stage intelligence from 5 sources:
  Emil Axelgaard / TV2 Sport (weight 1.5) — primary
  VeloNews (1.0), CyclingNews (1.0) — secondary
  ProCyclingStats (0.8), FirstCycling (0.8) — tertiary
Signal extraction via Anthropic API with signal_type field:
  form, tactics, team_strategy, terrain_fit, injury_risk, crash, illness,
  dns_risk, saving_legs, gc_protection, stage_hunter.
Weighted signal merge: agreement ×1.2, conflict ×0.5.
Signal-type-dependent caps (SOFT_CAP_BY_TYPE):
  crash/injury/illness/dns_risk → uncapped (±1.0, [UNCAPPED] flagged in output)
  saving_legs/gc_protection → ±0.40
  form/tactics → ±0.25
  terrain_fit → ±0.20
Overrides written with stage_last_applicable=N — expire silently after target stage.
Dashboard §9 Intelligence Panel: signal table with adjustment, sources, consensus.

## Operating model
Handoffs written in Claude.ai session. Programming done by Claude Code.
Human operator is integration layer and final decision maker.

## Key files for next session
- competition/roadmap.md — current phase status and corrections log
- notes/reviews/phase3_summary.md — this file
- data/API_NOTES.md — all confirmed Holdet endpoints and cookie requirements
- data/overrides/rider_attribute_overrides.yaml — all attribute corrections
- data/intelligence/ — per-stage expert intel artifacts (gather before each stage)
- interface/early/stage1_dashboard.html — current dashboard
- decisions/stage1_system_b.yaml — Stage 1 decision record

## Pre-stage checklist (run before every stage)
1. python3 scripts/gather_expert_intel.py --stage N
2. python3 scripts/apply_corrections_and_rebuild.py
3. Review dashboard §9 intelligence panel
4. Add manual overrides if needed (crashes, insider knowledge, lineup changes)
5. python3 scripts/apply_corrections_and_rebuild.py (if changes made)
6. Review team, confirm captain, submit before window closes
