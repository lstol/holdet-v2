# Phase 2 — Data Foundation: Completion Summary
# Updated: May 5, 2026 (after Phase 2b hardening)

---

## Phase 2a — Structural (May 4, 2026)

| File | Contents |
|------|----------|
| data/riders/riders_giro2026_v1.json | 179 rider stubs (synthetic attributes) |
| data/riders/generate_riders.py | Generation script |
| data/stages/stages_giro2026.json | 21 stage profiles |
| data/outcomes/outcomes_grand_tours_2020_2025.json | Historical archive (partial sample) |
| data/outcomes/fetch_outcomes.py | Full archive fetch script |
| data/odds/odds_giro2026_stage1_T0.json | Stage 1 odds template |
| engine/siv/odds_snapshot.py | T0 odds snapshot pipeline |

## Phase 2b — Race Hardening (May 5, 2026)

| File | Contents |
|------|----------|
| data/riders/riders_giro2026_v1.json | UPDATED — 199 riders enriched with real holdet_id and prices |
| data/riders/prices_giro2026_stage0_pre.json | Pre-race price snapshot (timestamp: 2026-05-05T07:17:23Z) |
| data/snapshots/team_state_pre_race.json | Team 6796783 state — currently EMPTY (no riders selected yet) |
| engine/siv/fetch_riders.py | Live rider enrichment script |
| engine/siv/capture_cookie.py | Automated cookie capture via Playwright |
| data/API_NOTES.md | Updated with Better Auth details and confirmed endpoints |

---

## Rider Dataset (Layer 0)

- Total riders: 199 (23 teams)
- Active: 182
- DNS / isOut: 17 (including Germani 47380, Conca 47350)
- All active riders have holdet_id and real Holdet prices
- Terrain affinity, consistency, and recovery attributes are synthetic estimates
  pending roadbook confirmation and future Layer 0 hardening

## Authentication

- Auth system: Better Auth (not legacy session=uuid)
- Cookie auto-capture: engine/siv/capture_cookie.py (Playwright)
- Cookie is IP-sticky (AWSALB) — must be captured on the same machine
- Refresh when API returns 401/403

## Team State

- Team ID: 6796783
- Name: "Project Win The Giro"
- Tier: Gold (unlimited transfers)
- Status: EMPTY — no riders submitted yet
- Bank: 4,500,000 kr
- Action required: Select 8 riders in holdet.dk before Stage 1 (May 8, 17:00)

## Known Gaps

| Gap | Status |
|-----|--------|
| Sprint/KOM km positions | Estimated — roadbook_confirmed: false on all stages |
| Historical outcome archive | Partial sample — run fetch_outcomes.py --all |
| Odds snapshots | Template only — populate before each stage |
| holdet_id for ~17 unmatched synthetic riders | Low priority — not in Holdet market |

## Compliance Confirmation

- No race outcome data in Layer 0 attributes
- Exclusion window: all data predates race start
- Odds flagged as benchmark only in every file
- .env never committed to git
- API_NOTES.md updated with Better Auth and 199-rider correction

## What Is Ready for Phase 3a

- All 199 riders with holdet_id and real prices ✅
- 21 stage profiles with terrain classification ✅
- Pre-race price snapshot ✅
- Team state snapshot (empty — selection pending) ✅
- Cookie auto-capture working ✅
- Phase 3a dashboard handoff written ✅
