# Decision Governance Protocol — Holdet v2

---

## 1. Purpose

This protocol governs how humans may interpret system outputs and decide on structural modifications to the Holdet v2 architecture.

Constraint:
- This protocol does not affect runtime execution
- This protocol governs post-execution human decision-making only
- This protocol exists to prevent uncontrolled objective drift

---

## 2. Scope of Governance Decisions

This protocol applies to decisions involving:

- modifications to any system layer (0–4)
- changes to the Execution Protocol
- changes to the System Integrity Validator
- changes to Governance Layer rules
- updates to outcome space definitions
- updates to payoff structure
- updates to exclusion window or training regime

Constraint:
- All system-defining changes fall under governance control

---

## 3. Separation of Interpretation and Modification

Constraint:
- Interpreting system outputs is unrestricted
- Acting on interpretations to modify system structure is regulated

Rule:
- No structural change may be made solely based on single-run performance signals (EV, probability, or evaluation outputs)

---

## 4. Anti-Drift Constraint

Constraint:
- System modifications must not optimize for short-term output improvement alone
- Structural changes must preserve:
  - layer separation
  - information flow directionality
  - cross-run isolation guarantees

---

## 5. Evidence Aggregation Requirement

Constraint:
- Any system modification must be based on aggregated evidence across multiple runs
- Single-run anomalies must not trigger structural changes
- Evidence must include:
  - cross-run consistency checks
  - pattern stability analysis
  - not isolated EV or probability shifts

---

## 6. Feedback Containment Constraint

Constraint:
- System outputs (EV, probabilities, interaction features) may inform human understanding
- However, they must not directly dictate system redesign decisions
- Interpretation must pass through a deliberate abstraction step before influencing changes

---

## 7. Conflict-of-Interpretation Constraint

Constraint:
- When multiple interpretations of system outputs exist:
  - preference must be given to structural explanations over performance explanations
  - no single metric (EV, accuracy, ranking) may dominate decision-making

---

## 8. Change Authorization Constraint

Constraint:
- No single agent may unilaterally modify:
  - Outcome Space
  - Payoff Structure
  - Exclusion Window
  - Probability Layer design

Rule:
- Structural changes require multi-component validation (at least two independent governance perspectives)

---

## 9. Stability Preference Constraint

Constraint:
- The system must prefer structural stability over performance optimization unless:
  - persistent multi-run degradation is observed
  - structural violation is detected by System Integrity Validator

---

## 10. Drift Detection Requirement

Constraint:
- Over time, system changes must be checked for:
  - gradual convergence toward EV maximization
  - implicit collapse of layer separation
  - unintended reintroduction of feedback loops

---

## 11. Role in Architecture

This protocol ensures that human interpretation of system outputs does not silently redefine system objectives.

Constraint:
- This layer operates outside execution
- It governs system evolution, not system operation