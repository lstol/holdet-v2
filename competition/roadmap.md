# Holdet v2 — Development Roadmap
# Last updated: 2026-05-08

---

## Phase 1 — Done ✅
### Architecture & contracts
6-file canonical contract system locked in contracts/v2.0/.
Old 17-file system archived in contracts/v2.0/Old/.

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
- Pre-race price snapshot saved, team snapshot saved (EMPTY at time)
- Cookie auto-capture via Playwright working
- Auth confirmed: Better Auth (not NextAuth/legacy session)
- API_NOTES.md complete with all confirmed endpoints and cookie requirements

---

## Phase 3a — Done ✅
### Stage 1 decision dashboard (May 5, 2026)
- Recommended 8-rider team within 50M budget
- 3-stage EV lookahead (fixed team, summed — later replaced by optimizer)
- Dashboard: interface/early/stage1_dashboard.html
- Build script: interface/early/build_stage1.py
- Captain: Jonathan Milan

---

## Phase 3b — Done ✅
### EV model, optimizer, risk profiles (May 5, 2026)

**data/stages/stage_profiles_parsed.json**
- All 21 stage images parsed via Anthropic vision API
- Intermediate sprints and KOM climbs extracted as lists (never null)
- Key finds: Stage 2 has 3 KOMs, Stage 14 has 5 KOMs, Stage 19 HC Passo Giau (40 pts)

**models/ev_breakdown.py**
- Six-component per-rider per-stage EV model:
  stage_finish, gc, jersey, sprint_kom, team_bonus, captain_bonus
- models/ev_breakdown_stage{1–21}.json pre-computed for all active riders

**models/optimizer.py**
- Multi-stage transfer-aware optimizer
- Per-stage optimal team + explicit hold/transfer decision with net EV rationale
- StageDepthCount bonus modeled at team level
- decisions/stage1_system_b.yaml in competition protocol format

**models/risk_profiles.py**
- Three named compositions: Conservative / Balanced / All-In
- EV, variance (σ), and EV/σ per rider
- Consensus picks (in all 3 profiles) flagged

---

## Phase 3c — Done ✅
### Scoring fixes (May 5–6, 2026)

Five modeling errors corrected:

| Fix | Before | After |
|-----|--------|-------|
| Sprint/KOM points | Calibration constant | Actual roadbook data |
| GC EV flat stages | 0 kr | Reflects P(win) × GC leader payoff |
| Sprint/KOM EV (Milan S1) | 1,242 kr | 51,858 kr |
| Captain bonus | 0.6× multiplier | E[max(ΔV,0)] from full distribution |
| Stage image in dashboard | Broken relative path | Base64 data URI |

New file: data/stages/stage_roadbook.json — official sprint/KOM point scales
for all 21 stages (HC: 40/20/12..., Cat1: 25/16/10..., etc.)

---

## Phase 3d — Done ✅
### Rider intelligence + probability recalibration (May 8, 2026)

**Rider attribute pipeline**
- data/external/riders_copilot.json — Copilot-researched attributes for full startlist
- scripts/ingest_copilot_attributes.py — ingests Copilot data, matches by name,
  writes to override file with fuzzy matching and dry-run support
- data/overrides/rider_attribute_overrides.yaml — single source of truth for
  all attribute corrections. Append-only. Three source tiers:
    manual (priority 3) > expert_intel (priority 2) > copilot/web (priority 1)
- scripts/review_contender_pool.py — shows sprint/climb/GC contender pool
  with ✓ researched / ⚠ synthetic flags per rider
- scripts/apply_corrections_and_rebuild.py — propagates any override change
  through EV model → optimizer → risk profiles → dashboard in one command

**Probability model fixes**
- Win probability: contender pool model (8–15 riders per stage type),
  not diluted across full 182-rider field
- Sprint/KOM EV derived from same win probability as stage finish (consistency)
- Terrain mismatch: pure sprinters get negative EV on hilly/mountain stages
  (arrival penalty applied)

**Manual calibrations**
- Jonathan Milan: sprint_affinity = 0.96 (field anchor, source: manual)
- Dylan Groenewegen: sprint_affinity = 0.88 (toned down from Copilot 1.00)
- Note: affinities are relative within this startlist, not absolute speed

**Sprint contender pool result**
- Before: 45 riders with synthetic sprint_affinity ≥ 0.65
- After: ~12 genuine sprint contenders, all ✓ researched

**Final Stage 1 team (50M, exact)**
- Jonathan Milan ★ captain (11.5M), Dylan Groenewegen (10M), Arnaud De Lie (8M),
  Kaden Groves (8.5M), Luca Mozzato (4M), Tord Gudmestad (3M),
  Jasper De Buyst (2.5M), Markus Hoelgaard (2.5M)
- Tobias Bayer correctly excluded after sprint_affinity corrected downward

**load_rider_attributes() implementation notes**
- Overrides sorted by priority before application — manual always wins
- mode: adjust = additive on base value, clamped [0,1]
- mode: replace = exact value set
- stage_last_applicable = override silently expires after target stage
- _overridden list tracks which attributes were modified and by what source

---

## Phase 3e — Done ✅
### Expert intelligence pipeline (May 8, 2026)

Pre-stage intelligence gathering from multiple sources, with structured
signal extraction and weighted merge. Runs before every stage decision.

**scripts/gather_expert_intel.py**
- Sources (with trust weights):
    Emil Axelgaard / TV2 Sport (1.5) — primary, fetched via web_search
    VeloNews (1.0), CyclingNews (1.0) — secondary
    ProCyclingStats (0.8), FirstCycling (0.8) — tertiary
- Extraction via Anthropic API: signal_type, direction, magnitude, confidence
- Signal types: form, tactics, team_strategy, terrain_fit, injury_risk,
  crash, illness, dns_risk, saving_legs, gc_protection, stage_hunter
- Merge logic: agreement across sources → ×1.2 amplification
                conflict across sources → ×0.5 dampening
- Caps by signal type (SOFT_CAP_BY_TYPE):
    crash, injury_risk, illness, dns_risk → ±1.0 (uncapped, [UNCAPPED] flagged)
    saving_legs, gc_protection → ±0.40
    form, tactics → ±0.25
    terrain_fit → ±0.20
- Writes data/intelligence/stage{N}_expert_intel.yaml (raw + merged)
- Writes mode:adjust overrides with stage_last_applicable=N (no bleedthrough)

**Adjustment caps rationale**
- Uncapped crash/injury: a crashed sprinter can drop from 0.96 to 0.11 sprint_affinity
  for one stage — a −0.85 adjustment is correct, not a model error
- Manual overrides have no pre-cap — human operator sets what they set
- Form/tactics capped at ±0.25 — prevents overreaction to one analyst's opinion

**Dashboard intelligence panel**
- "Gather Intelligence" button shows terminal commands to run
- Loads stage{N}_expert_intel.yaml at build time
- Signal table: adjustment direction, magnitude, sources, consensus flag
- Uncapped signals flagged with [UNCAPPED] in print output

**Pre-stage workflow**
```
T-3h: python3 scripts/gather_expert_intel.py --stage N
T-3h: python3 scripts/apply_corrections_and_rebuild.py
T-2h: Review dashboard intelligence panel
T-2h: Add manual overrides if needed (crashes, insider knowledge)
T-1h: python3 scripts/apply_corrections_and_rebuild.py (if manual changes made)
T-1h: Review final team recommendation, confirm, submit
```

---

## Phase 3f — Done ✅
### Multi-stage optimizer + archetype risk profiles + dashboard overhaul (May 8, 2026)

- True multi-stage optimizer with transfer cost vs EV gain decisions
- StageDepthCount bonus modeled at team level
- Three archetype risk profiles (Conservative / Balanced / All-In)

---

## Phase 3h — Done ✅
### Point scales, power weighting, scenario sliders (May 9, 2026)

**Part 0 — Model fixes**
- Fix A: P(win) recomputed per-stage from stage_group (not cached from stage 1 defaults)
- Fix B: sprint_kom_ev ≤ stage_finish_ev × 1.5 assertion + conservation check
- Fix C: Team bonus as proper expectation Σ P(teammate at pos k) × bonus(k)
- Fix D: Optimizer recomputes team bonus per proposed team during swap evaluation

**Part 1 — Official Giro 2026 Holdet point scales (scripts/update_roadbook_points.py)**
- flat: [50, 35, 25, 18, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
- hilly: [25, 18, 12, 8, 6, 5, 4, 3, 2, 1]
- mountain: [15, 12, 9, 7, 6, 5, 4, 3, 2, 1]
- Single intermediate sprint per non-TT stage: [12, 8, 5, 3, 1]
- stage_group field added to each roadbook entry

**Part 2 — Scenario-based EV model (models/ev_breakdown.py)**
- AFFINITY_POWER = 8: amplifies elite/journeyman gap in win probability
- 4 scenarios: bunch_sprint, reduced_sprint, breakaway, gc_day
- Per-scenario threshold + contender_mass → Milan P(win|bunch_sprint) = 25.6%
- STAGE_TYPE_DEFAULTS: flat 70/20/10/0, hilly 15/35/35/15, mountain 0/5/25/70
- PURE_SCENARIOS for per-scenario dashboard data
- build_rider_scenario_data() generates per-scenario EV + P(win) for all active riders

**Part 3 — Scenario sliders in dashboard (interface/early/build_stage1.py)**
- 4 sliders (Bunch Sprint / Reduced Sprint / Breakaway / GC Day), sum locked to 100%
- 6 presets: pure_sprint, sprint_risk, breakaway, mountain, open, default
- Scenario mix color bar (visual weight indicator)
- JavaScript team selection updates in real time with slider changes
- Collapsible per-rider detail rows with per-scenario EV breakdown (S1+S2+S3)
- Stage 2 and 3 EVs pre-blended at build time using stage-type defaults

**Key numbers (Stage 1 flat, default weights 70/20/10/0)**
- Jonathan Milan: P(win|bunch_sprint) = 25.6%, blended S1 EV = 73,944 kr
- Top-5 by blended EV: De Lie > Milan > Groves > Groenewegen > Andresen
- Recommended team: Milan★, De Lie, Groves, Groenewegen + 4 budget fillers (50M exact)

---

## Current Status — Pre-Stage 1 (May 9, 2026)

**Stage 1:** Friday May 9 — Nessebar → Burgas, 156km, Flat, bunch sprint expected
**Next action:** Run intelligence gather before window closes

---

## Phase 4 — After Giro (June 2026)
### Probability model — trained
Replace rule-based baseline with trained models.
Prerequisite: capture stage outcomes throughout the Giro via fetch_outcomes.py.

- StageFinishPosition model (replaces geometric decay approximation)
- GC trajectory model
- Sprint/KOM point model (replaces rule-based affinity × probability)
- DNF/DNS risk model
- Captain bonus: trained E[max(ΔV,0)] from full outcome distribution
- Affinity calibration method: define anchor system per race,
  cap at 0.95 (reserve 1.0 for unambiguous field dominance only)

Note: affinities from different races are not directly comparable.
Phase 4 training must normalise per-race, not pool raw values.

---

## Phase 5 — Before Tour de France (June 2026)
### Decision engine — trained
- Full multi-stage lookahead optimizer (trained EV)
- Captain optimizer (trained CaptainPositiveValueGrowth EV)
- Transfer planner with fee vs EV gain analysis
- Scenario comparison (breakaway vs peloton, weather, GC disruption)
- Local HTTP server for dashboard button integration (currently terminal fallback)

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
| May 5 | Phase 2b, 3a, 3b, 3c complete |
| May 8 | Phase 3d, 3e complete — full intelligence pipeline operational |
| May 9 (Friday) | Stage 1 start — Nessebar → Burgas, 156km, Flat |
| May 31 | Giro final stage |
| June 2026 | Phase 4 model training |
| July 5 | Tour de France starts |

---

## Repo Health (May 8, 2026)

| Area | Status |
|------|--------|
| contracts/v2.0/ | ✅ 6 canonical files |
| data/riders/riders_giro2026_v1.json | ✅ 199 riders with real prices |
| data/external/riders_copilot.json | ✅ Copilot-researched attributes |
| data/overrides/rider_attribute_overrides.yaml | ✅ Copilot + manual calibrations |
| data/stages/stage_profiles_parsed.json | ✅ 21 stages vision-parsed |
| data/stages/stage_roadbook.json | ✅ Actual sprint/KOM point scales |
| data/intelligence/ | ✅ Pipeline ready, gather before each stage |
| data/snapshots/ | ✅ Pre-race state saved |
| data/odds/ | ⚠️ Template only — populate before each stage |
| data/outcomes/ | ⚠️ Empty — begin capturing from Stage 1 |
| data/reviews/ | ✅ Contender pool review artifacts |
| models/ev_breakdown.py | ✅ Scenario-based, AFFINITY_POWER=8, Fix A/B/C |
| models/ev_breakdown_stage{1–21}.json | ✅ Re-generated with scenario_ev + scenario_p_win |
| models/optimizer.py | ✅ Fix D: team bonus per proposed team |
| models/risk_profiles.py | ✅ Conservative/Balanced/All-In |
| scripts/update_roadbook_points.py | ✅ Official 2026 Holdet point scales |
| scripts/gather_expert_intel.py | ✅ 5 sources, weighted merge, uncapped crash |
| scripts/ingest_copilot_attributes.py | ✅ Full field attribute ingestion |
| scripts/review_contender_pool.py | ✅ Researched/synthetic flags |
| scripts/apply_corrections_and_rebuild.py | ✅ One-command rebuild |
| decisions/stage1_system_b.yaml | ✅ Stage 1 decision record |
| decisions/stage1_risk_profiles.yaml | ✅ Three risk profiles |
| interface/early/stage1_dashboard.html | ✅ Scenario sliders, collapsible rows, intel panel |
| interface/early/build_stage1.py | ✅ Scenario sliders, 6 presets, JS team selection |
| engine/siv/capture_cookie.py | ✅ Playwright login working |
| engine/siv/fetch_riders.py | ✅ Ready |
| competition/roadmap.md | ✅ This file |
| notes/reviews/phase3_summary.md | ✅ Full Phase 3 account |

---

## Corrections log
1. Odds: benchmark/sanity check only — never model input or calibration target
2. Interaction outputs: terrain fit diagnostics, not rankable scores
3. Transfer cost: 1% buy fee only (no separate exit fee)
4. GC EV: nonzero on flat stages — stage win = GC lead on bunch sprint stages
5. Captain bonus: E[max(ΔV,0)] from full distribution, not a multiplier
6. Sprint/KOM points: deterministic from roadbook, not calibration constants
7. Win probability: contender pool only (~10 riders on sprint stage), not full field
8. Sprint/KOM EV: must derive from same win probability as stage finish
9. Terrain mismatch: pure sprinters have negative EV on hilly/mountain stages
10. Rider attributes: synthetic Phase 2a replaced by Copilot web research
11. Affinity values: relative within this startlist, not absolute speed measurements
12. Affinity cap at 0.95 for future ingestion — reserve higher values for clear dominance
13. Override priority: manual > expert_intel > copilot — sort guaranteed in load_rider_attributes()
14. Crash/injury signals: uncapped (±1.0) — a crashed sprinter correctly drops to 0.11
15. stage_last_applicable: expert_intel overrides expire silently — no bleedthrough
16. AFFINITY_POWER=8: power-weighting to separate elite from journeyman (Milan 25.6% vs field 2%)
17. Scenario contender_mass: non-contenders in a scenario genuinely cannot win (return 0, not 0.002)
18. Sprint EV: p_win × total_sprint_pts × POINT_VALUE (no division by n_contenders)
19. Team bonus Fix D: computed per proposed team during swap evaluation, not cached standalone
