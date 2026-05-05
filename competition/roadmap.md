# Holdet v2 — Development Roadmap (Updated May 5, 2026)

---

## Phase 1 — Done ✅
### Architecture & contracts
6-file canonical contract system locked in contracts/v2.0/.
Old 17-file system archived in contracts/v2.0/Old/.

---

## Phase 2a — Done ✅
### Data foundation — structural (May 4, 2026)
- 179 rider stubs created with synthetic Layer 0 attributes
- 21 stage profiles created with estimated sprint/KOM positions
- Historical outcome archive schema + fetch script ready
- Odds snapshot pipeline template ready

---

## Phase 2b — Done ✅
### Data hardening — race-ready (May 5, 2026)
- 199 riders enriched with real holdet_id and Holdet prices
- 17 DNS riders flagged (isOut=true), including Germani and Conca
- Pre-race price snapshot saved
- Team state snapshot saved (team currently EMPTY — selection pending)
- Cookie auto-capture via Playwright working
- API_NOTES.md updated with Better Auth details
- Auth system: Better Auth (not legacy session=uuid)

---

## Phase 3a — IN PROGRESS (must complete before May 8 17:00)
### Stage 1 decision dashboard

Deliverable: interface/early/stage1_dashboard.html
- Recommended 8-rider team within 50M budget
- EV across Stages 1-3 (multi-stage lookahead)
- Captain recommendation
- Transfer cost formula with exit fee included
- Handoff: HANDOFF_phase3a_stage1_dashboard.md

ACTION REQUIRED before 17:00 May 8:
1. Run Phase 3a handoff in Claude Code
2. Review dashboard recommendations
3. Submit team in holdet.dk

---

## Phase 3b — During race (Stages 1-21, May 8-31)
### Iterative interface improvement

After each stage:
- Fetch updated prices via engine/siv/fetch_riders.py
- Rebuild dashboard for next stage
- Track actual vs predicted outcomes
- Refine rule-based probability baseline

Interface additions (prioritized):
- Rider card view (Layer 0 attributes)
- Stage profile viewer
- Interaction output inspector (terrain fit diagnostics)
- Override panel (log adjustments with reason + source)
- Post-stage review

---

## Phase 4 — After Giro (June 2026)
### Probability model
Replace rule-based baseline with trained models.
Prerequisite: run fetch_outcomes.py --all for full historical archive.

- Stage-type classifier
- StageFinishPosition model
- GC trajectory model
- Sprint/KOM point model
- DNF/DNS risk model
- Odds divergence review (human benchmark only)

---

## Phase 5 — Before Tour de France (June 2026)
### Decision engine
- Captain optimizer (CaptainPositiveValueGrowth EV)
- Transfer planner with full multi-stage lookahead
- Team composition optimizer (StageDepthCount bonus)
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
| May 5 | Phase 2b complete — real prices in repo |
| May 5 | Phase 3a handoff written |
| May 8 17:00 | Stage 1 start — Nessebar → Burgas, 156km, Flat |
| May 8 ~20:30 | Trading window opens — Stage 1 decision needed |
| May 31 | Giro final stage |
| June 2026 | Phase 4 model training |
| July 5 | Tour de France starts |

---

## Current Team Status

Team ID: 6796783 — "Project Win The Giro" — Gold tier
Bank: 4,500,000 kr | Budget: 50,000,000 kr
Status: EMPTY — must submit before May 8 17:00

DNS (do not select):
- Lorenzo Germani — holdet_id 47380
- Filippo Conca — holdet_id 47350

---

## Repo Health (May 5, 2026)

| Area | Status |
|------|--------|
| contracts/v2.0/ | ✅ 6 canonical files only — old files removed |
| data/riders/ | ✅ 199 riders with real prices |
| data/stages/ | ✅ 21 stages (sprint/KOM estimated) |
| data/snapshots/ | ✅ Pre-race team state saved |
| data/odds/ | ⚠️ Template only — populate before each stage |
| data/outcomes/ | ⚠️ Partial — run fetch_outcomes.py --all |
| engine/siv/ | ✅ fetch_riders.py + capture_cookie.py ready |
| interface/ | ❌ Phase 3a in progress |
| notes/reviews/ | ✅ phase2_summary.md current |
| competition/ | ✅ roadmap + competition_protocol current |

---

Corrections applied from initial roadmap:
1. Odds: benchmark/divergence signal only — not model input
2. Interaction outputs: terrain fit diagnostics, not rankable scores
3. Live tracker: separate execution boundary per re-run, informational only
4. Phase 2 split: 2a structural, 2b race-ready hardening
5. Phase 3 split: 3a minimal Stage 1 tool, 3b iterative during race
6. Transfer cost: always includes exit fee, not just buy fee
