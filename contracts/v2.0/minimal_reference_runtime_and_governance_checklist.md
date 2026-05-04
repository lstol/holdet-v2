# Minimal Reference Runtime & Governance Checklist — Holdet v2

---

## 1. Purpose

This document defines:

- a minimal reference execution model for Holdet v2
- a governance enforcement checklist for all structural changes
- a verification layer that ensures contracts are actually applied, not merely defined

Constraint:
- This is not an implementation
- This is a verification and enforcement reference standard

---

# PART I — MINIMAL REFERENCE RUNTIME

---

## 2. Runtime Model Overview

The system operates in three phases:

1. Configuration Phase
2. Execution Phase
3. Post-Execution Phase

Constraint:
- Phases are strictly sequential
- No overlap is permitted

---

## 3. Configuration Phase

### 3.1 Required Preconditions

Before execution:

- All layer definitions must be versioned
- All parameters must be frozen
- Execution boundary must be declared
- Governance approval must be recorded

Constraint:
- If any precondition is missing → execution is INVALID

---

### 3.2 Configuration Integrity Check

The System Integrity Validator must verify:

- layer separation integrity
- parameter provenance compliance
- absence of EV-derived configuration inputs
- outcome space independence from payoff structure

Constraint:
- Failure in any check blocks execution

---

## 4. Execution Phase

### 4.1 Strict Execution Order

1. Load Rider-Intrinsic snapshot
2. Load Race-State snapshot
3. Compute Interaction Layer
4. Compute Probability Layer
5. Compute EV Layer

Constraint:
- Order is immutable
- No parallel execution of dependent layers

---

### 4.2 Runtime Enforcement

After each layer:

- System Integrity Validator executes
- Violations are logged
- Execution continues only in diagnostic mode if violations exist

Constraint:
- Diagnostic mode outputs are non-authoritative

---

### 4.3 Isolation Constraint

- No runtime mutation of upstream layers
- No cross-layer shared mutable state
- No feedback loops during execution

---

## 5. Post-Execution Phase

### 5.1 Output Finalization

- Probability outputs are finalized
- EV outputs are finalized
- Interaction outputs are discarded unless explicitly versioned externally

---

### 5.2 Cleanup Constraint

- All runtime memory is cleared
- No temporary state persists
- Only versioned outputs may be stored externally

---

# PART II — GOVERNANCE ENFORCEMENT CHECKLIST

---

## 6. Change Classification Requirement

Every proposed change must be classified as:

- Layer modification
- Parameter modification
- Structural constraint modification
- Governance modification

Constraint:
- Unclassified changes are rejected

---

## 7. Multi-Source Validation Requirement

No structural change may proceed unless:

- at least 2 independent governance perspectives approve
- evidence spans multiple execution runs
- no single-run EV or probability signal dominates justification

---

## 8. Anti-Shortcut Constraint

Prohibited as justification for change:

- single-run performance improvement
- EV uplift in isolated runs
- probability calibration gains without structural analysis

---

## 9. Provenance Verification Requirement

Before approving changes:

- verify no EV-derived signals influenced proposal formation
- verify no simulation outputs directly shaped decision
- verify no outcome-space-aligned bias in feature selection

---

## 10. Drift Detection Requirement

Governance must evaluate:

- trend toward EV maximization over structural fidelity
- gradual collapse of layer separation
- increasing reliance on feedback shortcuts

Constraint:
- Drift detection must be explicit, not implicit

---

## 11. Authority Separation Constraint

No single agent may simultaneously control:

- payoff structure definition
- outcome space definition
- parameter training regime
- execution boundary declaration

Constraint:
- Combined authority constitutes invalid governance state

---

## 12. Governance Override Rule

If conflict exists between:

- performance improvement
- structural integrity

Constraint:
- structural integrity always takes precedence

---

# PART III — SYSTEM GUARANTEE MODEL

---

## 13. What This System Guarantees

If enforced correctly:

- no runtime cross-layer contamination
- no simulation-to-execution leakage
- no EV-driven parameter feedback loops
- no outcome-space bias infiltration
- no silent structural drift without governance detection

---

## 14. What This System Does NOT Guarantee

- correctness of human interpretation
- adherence to governance rules outside system
- resistance to deliberate external override
- absence of organizational bias in approvals

---

## 15. Final Principle

Constraint systems enforce computation.

Governance systems enforce evolution.

Neither can fully replace the other.