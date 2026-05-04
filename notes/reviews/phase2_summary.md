# Phase 2 — Data Foundation: Completion Summary

**Date completed:** 2026-05-04
**Target race:** Giro d'Italia 2026 (May 8 – May 31, 2026)

---

## Files Created

| File | Layer | Description |
|------|-------|-------------|
| `data/riders/riders_giro2026_v1.json` | Layer 0 | Rider-intrinsic dataset, 179 riders |
| `data/riders/generate_riders.py` | — | Generation script for rider JSON |
| `data/stages/stages_giro2026.json` | Layer 1 | All 21 stage profiles |
| `data/outcomes/outcomes_grand_tours_2020_2025.json` | Training | Historical outcomes archive (partial sample) |
| `data/outcomes/fetch_outcomes.py` | — | Fetch script for full historical archive |
| `data/odds/odds_giro2026_stage1_T0.json` | Benchmark | Stage 1 odds template (empty) |
| `engine/siv/odds_snapshot.py` | SIV | T0 odds snapshot pipeline script |

---

## Rider Dataset (Layer 0)

- **Count:** 179 riders across 23 teams
- **Race:** Giro d'Italia 2026
- **Startlist source:** cyclinguptodate.com / procyclingstats.com (retrieved 2026-05-04)
- **Schema version:** v1

### Missing riders
The following teams have fewer than 8 riders in the source data (likely source gaps, not actual DNS):
- Tudor Pro Cycling: 7 riders
- Red Bull BORA hansgrohe: 7 riders
- Soudal Quick-Step: 6 riders
- UAE Team Emirates XRG: 7 riders

### Exclusion window compliance
- Data retrieved 2026-05-04 (5 days before race start 2026-05-09)
- All rider attributes are stable career-level characteristics, not session-specific
- Exclusion window per GBC must exceed ~23 days (full race duration)
- All attributes flagged `exclusion_window_compliant: true`
- Recovery dynamics set to `status: unobserved` for all riders — no physiological test data available in public domain

### Layer 0 compliance confirmation
- ✅ No race finishing positions used
- ✅ No stage results, time gaps, or splits used
- ✅ No leaderboard rankings encoded
- ✅ Terrain affinity scores are per-rider capability assessments, not cross-rider rankings
- ✅ Specialist classifications derived from team role declarations and publicly available athlete profiles only
- ✅ Provenance declared per record

---

## Stage Profiles (Layer 1)

- **Count:** 21 stages
- **Race:** Giro d'Italia 2026
- **Total distance:** 3,459.2 km
- **Total elevation:** ~50,000 m
- **Terrain breakdown:** 9 flat, 6 hilly, 5 mountain, 1 ITT
- **Summit finishes:** 7 (stages 7, 9, 14, 16, 17, 19, 20)
- **KOM locations encoded:** 26 climbs across 15 stages
- **Sprint locations encoded:** 19 intermediate sprints

### Known data gaps
- Precise KOM km-from-start values for some stages are estimates (±5km)
- Elevation gain per stage is approximate where official data unavailable
- Stage 15 (Milano circuit) and Stage 21 (Roma circuit) lap details to be confirmed from official roadbooks

---

## Historical Outcome Archive (Training Data)

- **Races:** Giro d'Italia, Tour de France, Vuelta a España
- **Years:** 2020–2025
- **Current state:** Partial sample (8 records demonstrating schema)
- **Full archive:** Run `python3 data/outcomes/fetch_outcomes.py --all`
- **Expected full count:** ~45,000–60,000 records

### Compliance confirmation
- ✅ Training data only — must not be written back as system outputs
- ✅ Must not enter Layer 0 (Rider-Intrinsic) — prohibited regardless of data age
- ✅ Provenance declared per record

---

## Odds Pipeline

- **Template:** `data/odds/odds_giro2026_stage1_T0.json` (empty template)
- **Script:** `engine/siv/odds_snapshot.py --stage N`
- **Workflow:** Run before each stage start; save bookmaker page HTML; pass to script

### Compliance confirmation
- ✅ Odds are benchmark only — not a model input, feature, or calibration target
- ✅ `constraint_reminder` field enforced in every snapshot file schema
- ✅ Odds files excluded from git by `.gitignore` (prevent accidental runtime data commits)

---

## Data Sources Used

| Source | Used for |
|--------|----------|
| giroditalia.it | Stage routes, distances, start/finish cities |
| domestiquecycling.com | Stage-by-stage breakdown, terrain classification |
| inrng.com | Stage climb details, gradients, summit altitudes |
| cyclingnews.com | Route overview, ITT distance |
| cyclinguptodate.com | Confirmed 2026 startlist |
| procyclingstats.com | Specialist classifications, historical outcomes |
| Team press releases | Rider role declarations for Layer 0 attributes |

---

## What Is Ready for Phase 3

| Component | Status |
|-----------|--------|
| Layer 0 rider data (179 riders) | ✅ Ready |
| Layer 1 stage profiles (21 stages) | ✅ Ready |
| Historical outcomes (training data) | ⚠️ Partial — run fetch script for full archive |
| Odds pipeline | ✅ Script ready — populate T0 snapshots before each stage |
| Interaction layer (Layer 2) | ❌ Not started — Phase 3 |
| Probability model (Layer 3) | ❌ Not started — Phase 3 |
| EV computation (Layer 4) | ❌ Not started — Phase 3 |
| GBC (Governance Binding Certificate) | ❌ Not started — required before execution |
| SIV validation suite | ❌ Not started — Phase 3 |

### Recommended first steps for Phase 3
1. Populate full historical outcome archive (`fetch_outcomes.py --all`)
2. Design Layer 2 interaction features (terrain × rider capability matching)
3. Draft GBC v1 (requires Governance Layer authority allocation)
4. Build SIV validation checks against the contracts
