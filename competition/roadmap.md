# Holdet v2 — Development Roadmap
# Corrected version — all phases contract-compliant

---

## Phase 1 — Done
### Architecture & contracts

6-file contract system, outcome space, governance. Foundation is locked.

---

## Phase 2 — Now
### Data foundation

Build the raw inputs that feed the model. No modeling yet — just clean, versioned data.

**Rider-Intrinsic dataset**
Physiological proxies from power data, terrain affinity, consistency — all outside exclusion window. Sources: ProCyclingStats, FirstCycling, training load APIs.

**Race-State schema**
Stage profiles, elevation, course classification, TTT flag, weather snapshots per stage.

**Odds snapshot pipeline** *(corrected)*
Stage win and top-k odds from bookmakers. Versioned and snapshotted pre-race. Used as an external benchmark and divergence signal only. May trigger human review. Must not be used as model features, labels, parameters, or automatic calibration targets.

**Historical outcome archive**
Past race results for all Outcome Space events: StageFinishPosition, GCPosition, JerseyHold, SprintPoint, KOMPoint. Used for parameter training only.

---

## Phase 3 — Key milestone
### Early test interface

Visible logic before the model is correct. You inspect, challenge, and correct the system early.

**Rider card view**
All Layer 0 attributes for each rider — visible values, provenance, data age. You can flag suspect inputs.

**Stage profile viewer**
Elevation, classification, TTT flag, weather. Race-State rendered visually per stage.

**Interaction output inspector** *(corrected)*
Layer 2 outputs per rider per stage shown as terrain fit diagnostics, fatigue condition indicators, and capability-condition mismatches. No cross-rider scalar scores — each diagnostic describes one rider's relationship to one race condition.

**Naive probability baseline**
Simple rule-based probabilities from historical base rates + terrain affinity. Not ML — but produces real Outcome Space distributions you can inspect and override.

**EV table per rider per stage**
Full EV breakdown: stage win, GC, jersey, sprint/KOM, team bonus, captain bonus. Transparent line items, not a black box score.

**Your override layer**
You can adjust probability weights based on race strategy knowledge, form signals, team orders. Overrides are logged and versioned — not merged into the model.

---

## Phase 4
### Probability model

Replace the rule-based baseline with trained models. Built on Layer 3 contract constraints.

**Stage-type classifier**
Predict stage type outcome distribution (sprint, climber, breakaway, TTT). First real model — narrow scope, verifiable.

**StageFinishPosition model**
Core model. P(position ≤ k) per rider per stage. Trained on historical outcome data only. Odds used as a human-facing divergence check after training — not as a feature or label.

**GC trajectory model**
P(GCPosition) as a function of cumulative stage outcomes. Multi-stage dependency handled explicitly.

**Sprint/KOM point model**
Expected points per rider based on terrain affinity and specialist profile. High variance — treat as distribution, not point estimate.

**DNF/DNS risk model**
P(FinishStatus ≠ FINISH) per rider per stage. Fatigue accumulation, crash history, team role. Critical for avoiding DNS cascade losses.

**Odds divergence review**
After model is trained and fixed, compare output to bookmaker implied probabilities. Large divergence surfaces for human review. You determine: model error or genuine edge. No automatic parameter adjustment allowed.

---

## Phase 5
### Decision engine

Convert EV into actionable transfer and captain decisions under budget constraints.

**Captain optimizer**
Rank riders by CaptainPositiveValueGrowth EV per stage. Account for captain bonus doubling asymmetry — positive-only.

**Transfer planner**
Multi-stage lookahead. Models transfer fee cost against expected EV gain. Bank interest opportunity cost included.

**Team composition optimizer**
8-rider selection under budget + 2-per-team constraints. Optimize for StageDepthCount bonus alongside individual EV.

**Scenario comparison**
Side-by-side EV for alternative team lineups and captain choices. You pick — the system explains the tradeoff.

---

## Phase 6
### Operational UI

Full interface for live race management. Pre-stage briefing → decision → post-stage review.

**Pre-stage briefing dashboard**
Stage profile, top EV riders, captain recommendation, transfer suggestions, odds divergence panel, your override input. Everything needed before the trading window opens.

**Live race diagnostic mode** *(corrected)*
Runs diagnostic re-executions from fresh Race-State snapshots as the race unfolds. Each re-execution has its own execution boundary and GBC reference. Outputs are informational only — they do not trigger decisions unless explicitly authorized by governance rules aligned with the trading window.

**Post-stage review**
Actual vs predicted outcome breakdown. Where did the model miss? Probability calibration log. Feeds decision governance — not the model directly.

**Expert knowledge capture**
Structured input for race strategy signals: team orders, protected rider declarations, form notes from race radio. Versioned. Feeds your override layer, not Layer 0.

**Multi-race learning loop**
Aggregate post-race reviews across multiple races. Pattern analysis for governance-controlled model updates. Single-run changes prohibited by contract.

---

*Three corrections applied from initial version:*
*1. Odds pipeline: "calibration" removed — odds may not feed Layer 3 directly or indirectly*
*2. Interaction inspector: "scores" replaced — rankable scalars prohibited at Layer 2*
*3. Live tracker: separate execution boundary per re-run; outputs informational unless governance pre-authorizes*
