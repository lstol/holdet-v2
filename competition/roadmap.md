# Holdet v2 — Development Roadmap (Updated May 5, 2026)

---

## Phase 1 — Done ✅
### Architecture & contracts
6-file contract system, outcome space, governance. Locked in contracts/v2.0/.

---

## Phase 2a — Done ✅ (but incomplete)
### Data foundation — structural
- 179 rider stubs created (synthetic — missing holdet_id and real prices)
- 21 stage profiles created (missing sprint/KOM km positions)
- Historical outcome archive schema + fetch script ready
- Odds snapshot pipeline template ready

---

## Phase 2b — URGENT (Must complete before May 8, 17:00)
### Data hardening — race-ready

**Why urgent:** Stage 1 starts May 8. Trading window closes at stage start.
Without real holdet_id and prices, EV computation and transfer fees are wrong.

**Step 1 — Enrich rider data with real API data**
Replace synthetic rider data with live data from:
GET /api/games/612/players
Map holdet_id, real prices, isOut/isInjured flags, captainPopularity.
File: data/riders/riders_giro2026_v1.json — update in place.

**Step 2 — Add sprint/KOM positions to stage profiles**
Source: Official Giro 2026 roadbooks (user has downloaded visually).
Add exact km positions to data/stages/stages_giro2026.json.
Critical for: SprintPoint and KOMPoint EV computation.

**Step 3 — Build live price update pipeline**
Script: engine/siv/fetch_riders.py
Runs after each stage to snapshot current prices.
Uses confirmed Python ingestion code from data/API_NOTES.md.

**Step 4 — Verify .env and cookie auth**
Confirm HOLDET_COOKIE, HOLDET_GAME_ID=612, HOLDET_FANTASY_TEAM_ID=6796783.
Test fetch_riders() returns 179 riders with real prices.
Never commit .env to git.

---

## Phase 3a — URGENT (Must complete before May 8, 20:30)
### Minimal Stage 1 interface — trading window ready

**Why urgent:** Trading window opens ~20:30 May 8 (after Stage 1 finish).
Need EV table and captain recommendation before window closes.

**Deliverable: Single-page Stage 1 decision dashboard**
- Rider list with real prices and holdet_id
- Stage 1 EV table (stage finish, sprint, team bonus, captain bonus)
- Captain recommendation (CaptainPositiveValueGrowth EV)
- Transfer suggestions vs current team (id: 6796783)
- Bank balance and budget remaining

This is a minimal working tool — not a polished UI.
Probability model is rule-based baseline only.

---

## Phase 3b — During race (Stages 1-21)
### Iterative interface improvement

After each stage:
- Update rider prices from API
- Update EV table for next stage
- Track actual vs predicted outcomes
- Refine rule-based probability baseline

Interface additions (prioritized):
- Rider card view
- Stage profile viewer
- Interaction output inspector (terrain fit diagnostics)
- Override panel (log manual adjustments with reason + source)
- Post-stage review

---

## Phase 4 — After Giro (June 2026)
### Probability model
Trained models replacing rule-based baseline.
- Stage-type classifier
- StageFinishPosition model
- GC trajectory model
- Sprint/KOM point model
- DNF/DNS risk model
- Odds divergence review (human-facing benchmark only)

---

## Phase 5 — Before Tour de France (June 2026)
### Decision engine
- Captain optimizer
- Transfer planner (multi-stage lookahead)
- Team composition optimizer
- Scenario comparison

---

## Phase 6 — Tour de France (July 2026)
### Operational UI
Full pre-stage briefing, live diagnostic mode, post-stage review.
Expert knowledge capture. Multi-race learning loop.

---

## Key dates
| Date | Event |
|------|-------|
| May 5 (today) | Phase 2b + 3a handoffs written |
| May 7 | Phase 2b complete — real prices + roadbook data in repo |
| May 8 17:00 | Stage 1 start (Nessebar - Burgas, 156km, Flat) |
| May 8 ~20:30 | Trading window opens — Stage 1 decision needed |
| May 31 | Giro final stage |
| June 2026 | Phase 4 model training |
| July 5 | Tour de France starts |

---

## Current team (pre-race)
Team ID: 6796783 — "Project Win The Giro" — Gold tier
Bank: 4,500,000 kr

| Rider | Holdet ID | Value |
|-------|-----------|-------|
| Lorenzo Germani | 47380 | 2,500,000 |
| Liam Slock | 47378 | 2,500,000 |
| Manuele Tarozzi (captain) | 47382 | 2,500,000 |
| Jonas Vingegaard | 47372 | 17,500,000 |
| Filippo Conca | 47350 | 2,500,000 |
| Dion Smith | 47341 | 2,500,000 |
| Lennert Van Eetvelt | 47377 | 7,500,000 |
| Jay Vine | 47368 | 8,000,000 |

Captain is a dummy pick — needs updating before Stage 1.

---

Corrections applied from initial roadmap:
1. Odds: benchmark/divergence signal only — not model input
2. Interaction outputs: terrain fit diagnostics, not rankable scores
3. Live tracker: separate execution boundary per re-run, informational only
4. Phase 2 split into 2a (done) and 2b (urgent — race-ready hardening)
5. Phase 3 split into 3a (minimal Stage 1 tool) and 3b (iterative during race)
