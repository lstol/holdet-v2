# System Integrity Validator — Holdet v2.1
# Graph-Based Deterministic Enforcement Engine

---

## 1. Purpose

The System Integrity Validator (SIV) verifies structural correctness of the entire system BEFORE execution begins.

Constraint:
- Runs before S1 → S2 transition
- If validation fails, execution is blocked

---

## 2. Validation Model

The system is represented as a directed graph:

G = (Nodes, Edges)

Where:
- Nodes = Layers, variables, outcomes, parameters, rules
- Edges = allowed dependencies between nodes

Constraint:
- Only explicit edges are valid
- Implicit or inferred edges are invalid

---

## 3. Core Validation Rules

---

### 3.1 Outcome Coverage Validation

Constraint:
Every scoring element in RULES.md must map to ≥1 Outcome_Space event.

Fail if:
- any scoring rule has no corresponding outcome mapping

---

### 3.2 Outcome Isolation Validation

Constraint:
Outcome nodes must not contain:
- EV values
- ranking signals
- payoff structure information

Fail if:
- any outcome encodes value or desirability

---

### 3.3 Dependency Direction Validation

Allowed edges only:

- Layer 0 → Layer 2
- Layer 1 → Layer 2
- Layer 2 → Layer 3
- Layer 3 → Layer 4
- RULES.md → Layer 4 (value mapping only)

Fail if:
- reverse edges exist
- skipped-layer edges exist (unless explicitly declared)

---

### 3.4 Cross-Layer Leakage Validation

Constraint:
No upstream layer may encode downstream objectives.

Detect:
- EV-correlated proxies in Layer 0 or Layer 1
- ranking signals in Interaction Layer
- payoff-encoded features upstream of EV

Fail if:
- any upstream node contains downstream objective information

---

### 3.5 Transfer Integrity Validation

Constraint:
TransferFeeApplied must be strictly deterministic:

fee = 0.01 × TransferBuy.price

Fail if:
- fee depends on EV, probability, or external signals

---

### 3.6 Temporal Boundary Validation

Constraint:
Execution boundary must:

- be defined before S2
- be immutable after S2 begins

Fail if:
- boundary is undefined
- boundary is modified post-freeze
- boundary is inferred post-hoc

---

### 3.7 Cross-Run Contamination Validation

Constraint:
No outputs from run N may appear in run N+1 inputs unless explicitly declared as persistent state.

Fail if:
- implicit reuse of prior run outputs is detected

---

## 4. Validation Output

SIV returns:

### PASS
- system is structurally valid for execution

### FAIL
Includes:
- violated rule ID
- affected nodes
- dependency path trace
- reason for invalidation

---

## 5. Enforcement Principle

Constraint:
SIV performs only deterministic graph validation.

- No probabilistic reasoning allowed
- No semantic interpretation allowed
- Only structural rule enforcement