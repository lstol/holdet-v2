Outcome_Space.md — v1.0 (Holdet v2)
1. Purpose

This document defines the complete, closed ontology of all events that may be used in probability modeling and EV computation.

Constraint:

Only events defined here exist for the system
All scoring in RULES.md must map to at least one event here
No derived or composite event may exist unless explicitly defined
2. Core Principle

Outcomes are atomic, observable race events or state transitions.

Constraint:

No outcome encodes value
No outcome encodes desirability
No outcome encodes EV or ranking
3. Outcome Space (Closed Set)
3.1 Stage Outcomes
StageWin(rider, stage_t)
StageFinishPosition(rider, position, stage_t) where position ∈ ℕ
StageTopK(rider, k, stage_t)
3.2 GC Outcomes
GCPosition(rider, position, stage_t)

Constraint:

GC is recomputed after each stage
GC is a derived race-state observable, not a preference signal
3.3 Sprint / KOM Micro-Events
SprintPoint(rider, sprint_id, stage_t)
KOMPoint(rider, climb_id, stage_t)

Constraint:

Each point event is atomic and independently countable
No aggregation allowed at definition level
3.4 Jersey State Events (terminal per stage)
JerseyHold(rider, jersey_type, stage_t)

jersey_type ∈ {YELLOW, GREEN, KOM, WHITE, MOST_AGGRESSIVE}

Constraint:

Evaluated only at stage completion state
3.5 Team Events
TeamStageWin(team, stage_t)
TeamPodium(team, stage_t, position ∈ {1,2,3})
3.6 Race Completion Events
FinishStatus(rider, stage_t) ∈ {FINISH, DNF, DNS, DSQ}
3.7 Transfer Events (CRITICAL ADDITION — aligns RULES.md)

These are required because RULES.md has economic transitions:

TransferBuy(rider, price, time_t)
TransferSell(rider, price, time_t)
TransferFeeApplied(rider, fee_amount, time_t)

Constraint:

Transfer events are NOT race outcomes
They belong to financial state space but must be represented for EV closure
4. RULES.md Mapping Constraint (FULL ALIGNMENT)

Every scoring rule MUST map to Outcome Space:

RULES.md Element	Outcome Mapping
Stage position payout	StageFinishPosition
GC payout	GCPosition
Sprint/KOM points	SprintPoint / KOMPoint
Jersey bonuses	JerseyHold
Team bonus	TeamPodium / TeamStageWin
TTT placement	StageFinishPosition (team-scoped interpretation)
DNF/DNS penalty	FinishStatus
Late arrival penalty	derived from StageFinishPosition delta
Captain bonus	requires downstream EV aggregation over StageWin / GCPosition
Stage depth bonus	aggregation over StageFinishPosition
Transfer fee (−1%)	TransferFeeApplied (derived from TransferBuy price)
Bank interest	external financial state (not race outcome, but linked via EV layer)
5. Transfer Cost Alignment Rule (explicit fix)

Constraint:

Transfer cost is NOT a model variable. It is a deterministic function of TransferBuy events.

Formalization:

fee = 0.01 × TransferBuy.price
applied once per TransferBuy event
no probabilistic interpretation allowed

This ensures:

no EV leakage into transfer mechanics
no optimization over fee structure
6. Anti-Compression Constraint (critical)

Constraint:

No function may map multiple Outcome events into a single latent scalar unless explicitly defined

This prevents:

hidden ranking reconstruction
EV shortcut features
interaction-layer proxy leakage
7. Closure Constraint

Constraint:

Any observable race or financial event not in Outcome Space is undefined and must not be modeled.