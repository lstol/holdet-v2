# Phase 3 Summary — Holdet v2 / Giro d'Italia 2026
# Written: 2026-05-08 (pre-Stage 1)

---

## What Phase 3 delivered

Phase 3 was split into four sub-phases as modeling errors were discovered
and the scope expanded. This is the full account of what was built and fixed.

---

## Phase 3a — Stage 1 decision dashboard

**Deliverable:** interface/early/stage1_dashboard.html + build_stage1.py

**Recommended team:** Jonathan Milan ★, Dylan Groenewegen, Arnaud De Lie,
Kaden Groves, Tobias Bayer, Markus Hoelgaard, Max Walscheid, Luca Mozzato
Total: 50,000,000 kr. Captain: Jonathan Milan.

**Checks passed:** 8 riders, budget exact, no DNS riders, max 2 per real team.

---

## Phase 3b — EV model, optimizer, risk profiles

**EV model (models/ev_breakdown.py):**
Six auditable components: stage_finish, gc, jersey, sprint_kom, team_bonus,
captain_bonus. Pre-computed for all 182 active riders × 21 stages.

**Stage image parsing:**
All 21 stage profile images parsed via Anthropic vision API.
Key finds: Stage 2 has 3 KOMs (not 2). Stage 14 has 5 KOM climbs.
Stage 19: HC Passo Giau (40 pts).

**Optimizer (models/optimizer.py):**
Multi-stage transfer-aware. Finds optimal team per stage, computes net EV
gain minus transfer cost, outputs hold/transfer decision with rationale.
StageDepthCount bonus modeled at team level.

**Risk profiles (models/risk_profiles.py):**
Conservative (max EV/σ), Balanced (optimizer output), All-In (concentrate
top-EV picks + high-upside cheap riders). Consensus picks flagged.

---

## Phase 3c — Scoring fixes

Five errors corrected after initial Phase 3b validation:

| Error | Before | After |
|-------|--------|-------|
| Sprint/KOM points | Calibration constant | Actual roadbook data |
| GC EV flat stages | 0 kr | 16,480 kr (Milan S1) |
| Sprint/KOM EV | 1,242 kr | 51,858 kr (Milan S1) |
| Captain bonus | 0.6× multiplier | E[max(ΔV,0)] |
| Stage image | Broken path | Base64 data URI |

New file: data/stages/stage_roadbook.json — official sprint/KOM point
scales for all 21 stages.

---

## Phase 3d — Rider intelligence + probability recalibration

**Status: IN PROGRESS**

**Problem identified:** Synthetic Phase 2a attributes are wrong for many
riders. Milan's win probability was 5.4% (should be ~10–15%). Sprint/KOM
EV exceeded stage_finish EV (internally inconsistent). Stage 2 EV too high
for sprinters (terrain mismatch penalty not applied).

**Solution:** Web search intelligence per rider via Anthropic API.
scripts/gather_rider_intelligence.py researches each rider and writes
corrected attributes to data/overrides/rider_attribute_overrides.yaml.
The override file is append-only and never overwrites the main rider JSON.

**Intelligence workflow:**
1. gather_rider_intelligence.py --stage-type sprint (45 riders, ~11 min)
2. review_contender_pool.py 1 (confirm pool)
3. apply_corrections_and_rebuild.py (propagate downstream)

**Still to build (HANDOFF_phase3d_probability_and_risk.md):**
- Contender pool win probability model
- Sprint/KOM EV consistency assertion
- Terrain mismatch penalty (negative EV for sprinters on hilly stages)
- Stage-type-conditional risk profiles
- Collapsible dashboard rows with P(win) + per-component EV per stage

---

## Operating model

Handoffs are written in the Claude.ai session (this interface).
Programming is done by Claude Code.
The human operator is the integration layer and decision maker.

Session continuity: start each new session with the briefing block
at the top of this repo's README (or the session briefing template).
Read contracts/v2.0/ and competition/roadmap.md before doing anything.

---

## Key files for next session

| File | Purpose |
|------|---------|
| competition/roadmap.md | Current phase status |
| notes/reviews/phase3_summary.md | This file |
| data/API_NOTES.md | All confirmed Holdet API endpoints |
| data/overrides/rider_attribute_overrides.yaml | Rider attribute corrections |
| HANDOFF_phase3d_probability_and_risk.md | Next Claude Code task |
| interface/early/stage1_dashboard.html | Current dashboard |
| decisions/stage1_system_b.yaml | Stage 1 decision record |
