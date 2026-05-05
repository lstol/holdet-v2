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

## Phase 3f — Multi-stage optimizer + risk profiles (May 8, 2026)
True multi-stage optimizer with transfer cost vs EV gain decisions per stage.
StageDepthCount bonus modeled at team level via independence approximation over P(top-15).
Three archetype risk profiles: Conservative / Balanced / All-In.
decisions/stage1_system_b.yaml in competition protocol format.
decisions/stage1_risk_profiles.yaml with EV, variance, EV/σ per rider.

## Phase 3h — Point scales, power weighting, scenario sliders (May 9, 2026)

**Four model fixes:**
- Fix A: P(win) recomputed per-stage using stage's scenario weights (not cached from stage 1)
- Fix B: sprint_kom_ev ≤ stage_finish_ev × 1.5 assertion + conservation check (Σ ≈ contender_mass)
- Fix C: Team bonus = Σ P(teammate at pos k) × bonus(k) — proper expectation, not approximation
- Fix D: Optimizer recomputes team_bonus per proposed team during swap evaluation

**Official 2026 Holdet point scales (scripts/update_roadbook_points.py):**
- flat: [50, 35, 25, 18, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
- hilly: [25, 18, 12, 8, 6, 5, 4, 3, 2, 1]
- mountain: [15, 12, 9, 7, 6, 5, 4, 3, 2, 1]
- One intermediate sprint per non-TT stage: [12, 8, 5, 3, 1]
- stage_group field added to every roadbook entry; ITT stages (8, 14) have no sprint

**Scenario-based EV model (models/ev_breakdown.py):**
- AFFINITY_POWER = 8 — power-weighting amplifies elite/journeyman gap
- 4 scenarios: bunch_sprint, reduced_sprint, breakaway, gc_day
- Each has threshold (who can win) + contender_mass (what fraction of probability pool is shared)
- bunch_sprint threshold=0.85, contender_mass=0.95 → only elite GT sprinters in pool
- Milan P(win|bunch_sprint) = 25.6%; blended S1 EV (flat defaults 70/20/10/0) = 73,944 kr
- STAGE_TYPE_DEFAULTS: flat 70/20/10/0, hilly 15/35/35/15, mountain 0/5/25/70
- build_rider_scenario_data() generates pure-scenario EV + P(win) for dashboard sliders
- All 21 stage JSONs regenerated with scenario_ev and scenario_p_win fields

**Scenario sliders (interface/early/build_stage1.py):**
- 4 sliders with sum locked to 100%; 6 presets (pure_sprint, sprint_risk, breakaway, mountain, open, default)
- Scenario mix color bar shows relative probability by scenario
- JavaScript team selection updates in real time as sliders move
- Collapsible per-rider detail rows with per-scenario EV (S1 + S2 + S3)
- Stage 2 and 3 EVs pre-blended at build time using stage-type defaults

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
