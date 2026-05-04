# Holdet v2 — Governance
# 06_governance.md

---

## 1. Purpose

The Governance Layer defines authority, configuration control, and evolution rules for all system-critical parameters. It does not participate in execution runs. It does not compute outcomes, probabilities, or EV. It governs system configuration and evolution only.

---

## 2. Governance-Critical Components

The following components are under governance control. No component may be modified without governance validation:

| Component | Defined In |
|-----------|-----------|
| Outcome Space | 03_outcome_space.md |
| Payoff Structure | 02_rules_payoff.md |
| Exclusion Window | 01_system_canonical.md |
| Parameter Training Regime | 04_layers.md (Layer 3) |
| Execution Boundary Declaration | 05_execution_and_validation.md |
| System Integrity Validator configuration | 05_execution_and_validation.md |
| Safety Margin value | GBC (Section 3 below) |
| System Objective operationalization | 01_system_canonical.md |

---

## 3. Governance Binding Certificate (GBC)

Every execution run must be bound to exactly one GBC. Execution without a valid GBC is structurally invalid (GI-10).

### GBC Contents

A GBC is a signed configuration object containing:
- Version of Outcome Space
- Version of Payoff Structure
- Version of Exclusion Window (including safety margin value)
- Version of Parameter Training Regime
- Version of Execution Protocol
- Version of System Integrity Validator
- Authority identifiers for each governance component
- Declared operationalization of System Objective targets ("structural correctness" and "EV consistency")
- Execution boundary declaration timestamp

### GBC Constraints

- Every execution run must reference exactly one GBC
- Once an execution run begins, its GBC cannot change
- Any mismatch between runtime configuration and GBC invalidates execution
- The SIV must verify GBC existence, completeness, and version consistency before S1

---

## 4. Authority Separation

No single agent may have unilateral authority over more than one governance-critical component. Authority must be distributed across independent roles or systems.

**Explicitly prohibited combined authorities:**
- Payoff Structure + Outcome Space (same agent)
- Parameter Training Regime + Exclusion Window (same agent)
- Execution Boundary declaration + Parameter Training (same process)
- Any governance role + EV outcome benefit

**Boundary declaration independence:** The process declaring the execution boundary must be independent of parameter training systems, simulation systems, and evaluation systems. It must not be co-located with training infrastructure and must produce an externally verifiable, auditable record.

---

## 5. Change Requirements

### Classification

Every proposed change must be classified as one of:
- Layer modification
- Parameter modification
- Structural constraint modification
- Governance modification

Unclassified changes are rejected.

### Approval

No structural change may proceed unless:
- At least 2 independent governance perspectives approve
- Evidence spans multiple execution runs
- No single-run EV, probability, or evaluation signal dominates justification

### Prohibited Justifications

The following are prohibited as sole or primary justification for structural change:
- Single-run performance improvement
- EV uplift in isolated runs
- Probability calibration gains without structural analysis
- Simulation findings (simulation may only surface structural violations, not drive parameter decisions)

### Conflict Rule

If performance improvement conflicts with structural integrity, structural integrity takes precedence without exception.

---

## 6. Versioning and Traceability

All governance-critical components must be versioned. Each version must include:
- Timestamp
- Authoring authority identifier
- Change justification (must not reference EV outputs as primary evidence)

Previous versions must remain immutable and auditable. Version history must be retained across all runs.

---

## 7. External Influence Constraint

External signals must not directly determine governance decisions. External signals may only inform governance decisions if:
- Explicitly declared
- Independent of system outputs
- Not correlated with EV or evaluation targets

Market odds, rankings, and model outputs from external sources are subject to the External Proxy Constraint in 01_system_canonical.md Section 3 and may not inform governance decisions that affect Layer 0, Layer 3, or Payoff Structure.

---

## 8. Drift Detection

Governance must periodically evaluate system evolution for:
- Gradual convergence toward EV maximization over structural fidelity
- Implicit collapse of layer separation
- Unintended reintroduction of feedback loops
- Increasing reliance on cross-run feedback paths

Drift detection must be explicit and recorded. It is triggered by pattern analysis across multiple runs, not by individual run signals. Detection findings must not themselves drive parameter changes without satisfying the full Change Requirements in Section 5.

---

## 9. Decision Governance (Post-Execution Human Decisions)

This section governs how humans may interpret system outputs and decide on structural modifications. It applies after execution, not during.

**Interpretation is unrestricted.** Acting on interpretations to modify system structure is regulated.

**No single-run triggers:** No structural change may be made solely on single-run performance signals (EV, probability, or evaluation outputs).

**Feedback containment:** System outputs may inform human understanding but must not directly dictate redesign. Interpretation must pass through a deliberate abstraction step before influencing changes. This abstraction step must be documented as part of the change evidence.

**Conflict of interpretation:** When multiple interpretations of system outputs exist, preference must be given to structural explanations over performance explanations. No single metric may dominate.

**Stability preference:** The system must prefer structural stability over performance optimization unless persistent multi-run degradation is observed or structural violation is detected by the SIV.

**Anti-drift rule:** Over time, system changes must be checked for gradual convergence toward EV maximization, implicit collapse of layer separation, and unintended feedback loop reintroduction. These checks must be explicit and documented.

---

## 10. What Governance Enforces vs. What It Cannot Enforce

**Enforces:**
- No runtime cross-layer contamination (via SIV)
- No simulation-to-execution leakage (via execution boundary and SIV)
- No EV-driven parameter feedback loops (via change requirements and GBC)
- No outcome-space bias infiltration (via authority separation)
- No silent structural drift (via drift detection)

**Cannot enforce:**
- Correctness of human interpretation outside system boundary
- Adherence to governance rules by actors outside the defined authority structure
- Absence of organizational bias in approval decisions
- Resistance to deliberate coordinated override by all authority holders simultaneously

Governance enforces system evolution. Execution enforces computation. Neither replaces the other.
