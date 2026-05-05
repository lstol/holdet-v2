# Holdet v2 — Development Roadmap
# Last updated: 2026-05-08 (pre-Stage 1)

---

## Phase 1 — Done ✅
### Architecture & contracts
6-file canonical contract system locked in contracts/v2.0/.

---

## Phase 2a — Done ✅
### Data foundation — structural (May 4, 2026)
- 179 rider stubs with synthetic Layer 0 attributes
- 21 stage profiles with estimated sprint/KOM positions
- Historical outcome archive schema + fetch script ready
- Odds snapshot pipeline template ready

---

## Phase 2b — Done ✅
### Data hardening — race-ready (May 5, 2026)
- 199 riders with real holdet_id and Holdet prices
- 17 DNS riders flagged (isOut=true), Germani and Conca excluded
- Pre-race price snapshot saved, team snapshot saved (EMPTY)
- Cookie auto-capture via Playwright working
- Auth confirmed: Better Auth (not NextAuth)
- API_NOTES.md complete with all confirmed endpoints

---

## Phase 3a — Done ✅
### Stage 1 decision dashboard (May 5, 2026)
- Recommended 8-rider team within 50M budget
- 3-stage EV lookahead (fixed team, summed)
- Dashboard: interface/early/stage1_dashboard.html
- Build script: interface/early/build_stage1.py

---

## Phase 3b — Done ✅
### EV model, optimizer, risk profiles (May 5, 2026)
- data/stages/stage_profiles_parsed.json — all 21 stage images parsed via vision API
- models/ev_breakdown.py — 6-component EV model
- models/ev_breakdown_stage{1–21}.json — pre-computed for 182 active riders
- models/optimizer.py — multi-stage transfer-aware optimizer
- models/risk_profiles.py — Conservative / Balanced / All-In compositions
- decisions/stage1_system_b.yaml — Stage 1 decision record
- decisions/stage1_risk_profiles.yaml — three risk profile outputs

---

## Phase 3c — Done ✅
### Scoring fixes (May 5–6, 2026)
Five confirmed modeling errors corrected:
1. Sprint/KOM points: from actual roadbook data (data/stages/stage_roadbook.json)
   not calibration constants. Milan S1 sprint_kom: 1,242 → 51,858 kr
2. GC EV on flat stages: nonzero for sprint contenders. Milan S1 gc_ev: 0 → 16,480 kr
3. Captain bonus: E[max(ΔV,0)] from full distribution, not 0.6× multiplier
4. Dashboard stage image: embedded as base64 data URI (was broken relative path)
5. KOM point scale: fixed category table (HC/1/2/3/4), not estimated

---

## Phase 3d — IN PROGRESS ⚠️
### Rider intelligence + probability recalibration

**Step 1 — Rider intelligence gathering: RUNNING NOW**
- scripts/gather_rider_intelligence.py — Anthropic API + web_search per rider
- data/overrides/rider_attribute_overrides.yaml — human-editable override file
- scripts/review_contender_pool.py — shows pool with ✓ researched / ⚠ synthetic flags
- scripts/apply_corrections_and_rebuild.py — propagates overrides downstream
- 45 sprint-relevant riders being researched (~11 minutes)

**Step 2 — Probability model fixes: NOT YET BUILT**
Handoff: HANDOFF_phase3d_probability_and_risk.md
- Win probability: contender pool model, not full field
  Milan P(win S1) currently 5.4% — should be 10–15%
- Sprint/KOM EV consistency: assert sprint_kom ≤ stage_finish × 1.5
- Stage 2 terrain mismatch: negative EV for sprinters (arrival penalty)

**Step 3 — Risk profile rework: NOT YET BUILT**
- Stage-type-conditional archetypes (sprinter / puncheur / breakaway artist)
- Breakaway artists explicit as All-In picks on hilly stages
- Conservative: never captain a breakaway artist

**Step 4 — Dashboard collapsible rows: NOT YET BUILT**
- Collapsed: Rider | Price | S1 EV | S2 EV | S3 EV | 3-Stage EV | P(win S1)
- Expanded: all 6 EV components × 3 stages, with P(win) per stage
- Breakaway analysis box in Risk Profiles tab

**Dependency order for 3d completion:**
1. gather_rider_intelligence.py finishes (running now)
2. review_contender_pool.py 1 — confirm pool
3. apply_corrections_and_rebuild.py — apply overrides
4. Run HANDOFF_phase3d_probability_and_risk.md in Claude Code
5. Rebuild dashboard with collapsible rows

---

## Phase 4 — After Giro (June 2026)
### Probability model — trained
Replace rule-based baseline with trained models.
Prerequisite: run fetch_outcomes.py --all for full historical archive.
- StageFinishPosition model (replaces geometric decay)
- GC trajectory model
- Sprint/KOM point model (replaces rule-based affinity)
- DNF/DNS risk model
- Captain bonus: trained E[max(ΔV,0)]

---

## Phase 5 — Before Tour de France (June 2026)
### Decision engine — trained
- Full multi-stage lookahead optimizer
- Captain optimizer (trained CaptainPositiveValueGrowth EV)
- Scenario comparison

---

## Phase 6 — Tour de France (July 2026)
### Operational UI
Full pre-stage briefing, live diagnostic mode, post-stage review.
Expert knowledge capture. Multi-race learning loop.

---

## Key Dates

| Date | Event |
|------|-------|
| May 4 | Phase 2a complete |
| May 5 | Phase 2b complete |
| May 5–6 | Phases 3a, 3b, 3c complete |
| May 8 | Phase 3d IN PROGRESS — intelligence gathering running |
| May 8 17:00 | Stage 1 start — Nessebar → Burgas, 156km, Flat |
| May 31 | Giro final stage |
| June 2026 | Phase 4 model training |
| July 5 | Tour de France starts |

---

## Current Team Status

Team ID: 6796783 — "Project Win The Giro" — Gold tier
Bank: 4,500,000 kr | Budget: 50,000,000 kr
Status: EMPTY — submit before 17:00 today

DNS (never select):
- Lorenzo Germani — holdet_id 47380
- Filippo Conca — holdet_id 47350

Recommended team (pending 3d rebuild):
  Jonathan Milan ★ | Dylan Groenewegen | Arnaud De Lie | Kaden Groves
  Tobias Bayer | Markus Hoelgaard | Max Walscheid | Luca Mozzato
  Total: 50,000,000 kr
⚠️ Do not submit until 3d rebuild is complete. Win probabilities are wrong until then.

---

## Repo Health

| Area | Status |
|------|--------|
| contracts/v2.0/ | ✅ 6 canonical files |
| data/riders/ | ✅ 199 riders with real prices |
| data/stages/stage_profiles_parsed.json | ✅ 21 stages vision-parsed |
| data/stages/stage_roadbook.json | ✅ Actual sprint/KOM point scales |
| data/overrides/rider_attribute_overrides.yaml | 🔄 Being populated now |
| data/reviews/ | 🔄 Stage 1 flags pending pool review |
| data/snapshots/ | ✅ Pre-race state saved |
| data/odds/ | ⚠️ Template only — populate before each stage |
| data/outcomes/ | ⚠️ Partial — run fetch_outcomes.py --all post-race |
| models/ev_breakdown.py | ⚠️ 3c fixes applied; 3d probability fixes pending |
| models/optimizer.py | ⚠️ Re-run after 3d |
| models/risk_profiles.py | ⚠️ Re-run after 3d |
| decisions/stage1_system_b.yaml | ⚠️ Re-run after 3d |
| scripts/gather_rider_intelligence.py | ✅ Running now |
| scripts/review_contender_pool.py | ✅ Ready |
| scripts/apply_corrections_and_rebuild.py | ✅ Ready |
| interface/early/stage1_dashboard.html | ⚠️ Rebuild after 3d |
| competition/roadmap.md | ✅ This file |
| notes/reviews/ | ⚠️ phase3_summary.md needs writing (see Step 2) |

---

## Corrections log
1. Odds: benchmark/sanity check only — never model input or calibration target
2. Interaction outputs: terrain fit diagnostics, not rankable scores
3. Transfer cost: 1% buy fee only (round-trip = fee on buy, no separate exit fee)
4. Phase 3 split: 3a minimal, 3b iterative, 3c scoring fixes, 3d probability
5. GC EV: nonzero on flat stages (stage win = GC lead)
6. Captain bonus: E[max(ΔV,0)] from full distribution, not multiplier
7. Sprint/KOM points: deterministic from roadbook, not calibration constants
8. Win probability: contender pool only (~10 riders on sprint stage), not full field
9. Sprint/KOM EV: must derive from same win probability — assert consistency
10. Terrain mismatch: pure sprinters have negative EV on hilly/mountain stages
11. Risk profiles: stage-type-conditional; breakaway artists are explicit variance picks
12. Rider attributes: synthetic Phase 2a attributes replaced by web search intelligence
