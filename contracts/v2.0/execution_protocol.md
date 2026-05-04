# Execution Protocol — Holdet v2.1
# State-Locked Deterministic Execution Model

---

## 1. Purpose

This protocol defines the only valid execution process for the Holdet system.

Constraint:
- Execution is a finite state machine
- All computation must occur inside locked phases
- No cross-phase mutation is permitted

---

## 2. Execution State Machine

The system operates in strictly ordered states:

---

### S0 — INITIALIZATION

Actions:
- Load RULES.md (immutable)
- Load Outcome_Space.md (immutable)
- Load system configuration
- Initialize dependency graph

Constraint:
- No computation allowed
- No probabilistic or model activity permitted

---

### S1 — CONTEXT FREEZE

Actions:
- Load Rider-Intrinsic Layer (Layer 0 snapshot)
- Load Race-State Layer (Layer 1 snapshot)
- Freeze all upstream inputs

Constraint:
- Inputs become immutable
- Any modification after this point invalidates execution

---

### S2 — MODEL FREEZE

Actions:
- Load Interaction Layer outputs
- Load Probability model parameters
- Load EV model parameters

Constraint:
- All parameters become immutable
- No retraining, recalibration, or adjustment allowed

---

### S3 — INFERENCE EXECUTION

Allowed operations:
- Compute Interaction Outputs
- Compute Probability distributions
- Compute Expected Value (EV)

Constraint:
- No new data sources allowed
- No structural modification allowed
- No external input allowed

---

### S4 — OUTPUT FINALIZATION

Actions:
- Compute final EV-ranked outputs
- Emit system recommendations
- Freeze output artifact

Constraint:
- Outputs become immutable immediately upon emission
- No feedback into any prior layer allowed

---

## 3. Execution Boundary Rule

Definition:
Execution boundary = transition from S1 → S2

Constraint:
- Must be recorded before S2 begins
- Must be immutable once S2 starts

---

## 4. No Cross-State Leakage Rule

Constraint:
- No state S(n) may access S(n+1)
- No backward modification is allowed
- No inference may depend on future state availability

---

## 5. Parameter Isolation Rule

Constraint:
- All parameters must be fixed prior to S2
- No runtime or mid-execution adjustment permitted

---

## 6. Output Integrity Rule

Constraint:
Outputs may depend only on:
- frozen inputs (S1)
- frozen parameters (S2)

---

## 7. System Invalidation Rule

Any violation of this protocol results in:
- immediate invalidation of execution
- discard of all outputs from current run