# Holdet v2 — Outcome Space
# 03_outcome_space.md

---

## 1. Purpose & Closure

This file defines the complete, closed ontology of all events that may be used in probability modeling and EV computation.

**Closure constraint:** Only events defined here exist for the system. Any observable race or financial event not in this set is undefined and must not be modeled. No derived or composite event may exist unless explicitly defined below.

**Core principle:** Outcomes are atomic observable race events, state transitions, or financial state snapshots. No outcome encodes value, desirability, EV, or ranking.

**EV computability requirement:** It must be possible to compute total EV using only probability outputs over this Outcome Space and the payoff mapping in 02_rules_payoff.md. No external or implicit logic may be required.

**Governance constraint:** The Outcome Space may only be modified through Governance Layer approval. The approving authority must not also control Payoff Structure (02_rules_payoff.md). Outcome Space selection must not be determined by which outcomes are rewarded under RULES.md.

---

## 2. Outcome Space (Closed Set)

### 2.1 Stage Outcomes

```
StageWin(rider, stage_t)
StageFinishPosition(rider, position, stage_t)    where position ∈ ℕ
StageTopK(rider, k, stage_t)
```

### 2.2 GC Outcomes

```
GCPosition(rider, position, stage_t)
```

GC is recomputed after each stage. It is a derived race-state observable, not a preference signal.

### 2.3 Sprint / KOM Micro-Events

```
SprintPoint(rider, sprint_id, stage_t)
KOMPoint(rider, climb_id, stage_t)
```

Each point event is atomic and independently countable. No aggregation permitted at definition level.

### 2.4 Jersey State Events (terminal per stage)

```
JerseyHold(rider, jersey_type, stage_t)
jersey_type ∈ {YELLOW, GREEN, KOM, WHITE, MOST_AGGRESSIVE}
```

Evaluated only at stage completion state.

### 2.5 Team Events

```
TeamStageWin(team, stage_t)
TeamPodium(team, stage_t, position)    where position ∈ {1, 2, 3}
```

### 2.6 Race Completion Events

```
FinishStatus(rider, stage_t) ∈ {FINISH, DNF, DNS, DSQ}
```

### 2.7 Late Arrival Penalty

```
LateArrivalMinutes(rider, stage_t)    where value ∈ ℕ₀ (truncated integer minutes)
```

Represents the number of full minutes a finishing rider arrives behind the stage winner. Truncated, not rounded. Only defined for riders with FinishStatus = FINISH. Capped at 30 (corresponding to the −90,000 kr ceiling in 02_rules_payoff.md). Not defined for TTT stages.

### 2.8 Team Time Trial Placement

```
TTTTeamPlacement(team, placement, stage_t)    where placement ∈ ℕ
```

Applies only on TTT stages. Represents the finishing placement of the real-world team in the TTT. Replaces StageFinishPosition on TTT stages for team-level scoring purposes. Individual rider payoffs derived from this event are computed in Layer 4 per the payoff table in 02_rules_payoff.md.

### 2.9 DNS Cascade Penalty

```
DNSRemainingStagePenalty(rider, stage_t)
```

Emitted once per stage for each stage where rider has DNS status. Distinct from the initial DNF event. Enables per-stage penalty accumulation without implicit cascade logic. Not emitted for the abandonment stage itself (covered by FinishStatus = DNF).

### 2.10 Captain State

```
CaptainSelection(rider, stage_t)
```

Boolean state: rider is designated captain for stage_t. Exactly one rider per team_entry per stage. Locked at stage start.

```
CaptainPositiveValueGrowth(rider, stage_t)    where value ∈ ℝ≥0
```

The positive component of captain's value growth in stage_t. Zero if value growth is negative or zero. Strictly non-negative. This is the quantity doubled into the bank — negative days produce no CaptainPositiveValueGrowth event.

### 2.11 Stage Depth Count

```
StageDepthCount(team_entry, count, stage_t)    where count ∈ {0,1,2,3,4,5,6,7,8}
```

The number of a team entry's active riders finishing in the stage top 15. Evaluated at stage completion. Not defined for TTT stages.

### 2.12 Rider Value State

```
RiderValue(rider, time_t)    where value ∈ ℝ
```

Snapshot of a rider's current market value at time_t. Used as the basis for transfer fee computation and final score calculation. Not a race outcome — a financial state observable.

### 2.13 Financial State Events

```
BankBalance(time_t)    where value ∈ ℝ
```

Snapshot of team entry bank balance at time_t. Includes all prior deposits (captain bonuses, stage depth bonuses) and interest.

```
BankInterestApplied(amount, time_t)    where amount ∈ ℝ≥0
```

The interest amount credited to the bank at time_t. Computed as 0.005 × BankBalance at start of round. Deterministic given BankBalance.

### 2.14 Transfer Events

```
TransferBuy(rider, price, time_t)
TransferSell(rider, price, time_t)
TransferFeeApplied(rider, fee_amount, time_t)
```

Transfer events are not race outcomes. They belong to financial state space and are represented for EV closure.

**Transfer fee formalization:** TransferFeeApplied is strictly deterministic.
```
fee = 0.01 × TransferBuy.price
```
Applied once per TransferBuy event. No probabilistic interpretation permitted. No EV influence on fee structure.

### 2.15 Final Score

```
FinalScore(team_entry)    where value ∈ ℝ
```

Terminal state computed at race completion.
```
FinalScore = Σ RiderValue(rider, t_final) for all active riders
           + BankBalance(t_final)
```
Defined only once per team_entry per race. Not a per-stage event.

---

## 3. RULES.md Mapping (Full Alignment)

Every scoring element in 02_rules_payoff.md maps directly to ≥1 explicit Outcome Space event. No row contains implicit, aggregated, or external logic.

| Scoring Element | Outcome Mapping |
|----------------|----------------|
| Stage position payout | StageFinishPosition(rider, position, stage_t) |
| GC payout | GCPosition(rider, position, stage_t) |
| Sprint points | SprintPoint(rider, sprint_id, stage_t) |
| KOM points | KOMPoint(rider, climb_id, stage_t) |
| Jersey bonuses | JerseyHold(rider, jersey_type, stage_t) |
| Team bonus | TeamPodium(team, stage_t, position) / TeamStageWin(team, stage_t) |
| TTT placement | TTTTeamPlacement(team, placement, stage_t) |
| DNF penalty (once) | FinishStatus(rider, stage_t) = DNF |
| DNS penalty (per stage) | DNSRemainingStagePenalty(rider, stage_t) |
| Disqualification penalty | FinishStatus(rider, stage_t) = DSQ |
| Late arrival penalty | LateArrivalMinutes(rider, stage_t) |
| Captain bonus | CaptainSelection(rider, stage_t) + CaptainPositiveValueGrowth(rider, stage_t) |
| Stage depth bonus | StageDepthCount(team_entry, count, stage_t) |
| Transfer fee | TransferFeeApplied(rider, fee_amount, time_t) |
| Bank interest | BankInterestApplied(amount, time_t) |
| Final score | FinalScore(team_entry) |

**Validation constraint:** Every scoring element in 02_rules_payoff.md must map to ≥1 event in this table. Unmapped scoring rules constitute a System Integrity Validator failure.

---

## 4. Structural Constraints

**Outcome isolation:** Outcome nodes must not contain EV values, ranking signals, or payoff structure information.

**Anti-compression:** No function may map multiple Outcome events into a single latent scalar unless explicitly defined in this file. This prevents hidden ranking reconstruction, EV shortcut features, and interaction-layer proxy leakage.

**No desirability encoding:** No outcome encodes value or desirability. Payoff values are defined in 02_rules_payoff.md and applied only in Layer 4.

**No implicit logic:** No EV computation may rely on logic not expressible as a function of events in this file and payoff values in 02_rules_payoff.md. Constructs labeled "downstream," "external," "derived implicitly," or "aggregation outside Outcome Space" are prohibited.
