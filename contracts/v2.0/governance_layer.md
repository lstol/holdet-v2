# Governance Layer — Holdet v2

---

## 1. Purpose of This Layer

This layer defines authority, control separation, and configuration governance for all system-critical parameters.

Constraint:
- This layer does not compute outcomes, probabilities, or EV
- This layer does not participate in execution runs
- This layer governs configuration authority only

---

## 2. Scope of Governance

This layer governs the following system components:

- Outcome Space Definition (Probability Layer)
- Payoff Structure (EV Layer)
- Exclusion Window (Race-State / Proximity constraints)
- Parameter Training Regime (Probability Layer)
- Execution Boundary Definition (Execution Protocol)
- System Integrity Validator configuration

Constraint:
- All listed components are considered governance-critical
- No component may be modified without governance validation

---

## 3. Separation of Authority Constraint

Constraint:
- No single agent may have unilateral authority over more than one governance-critical component
- Authority must be distributed across independent roles or systems
- Conflicting authority over coupled components is prohibited

Examples:
- An agent controlling both Payoff Structure and Outcome Space is invalid
- An agent controlling both Training Regime and Exclusion Window is invalid

---

## 4. Configuration Independence Constraint

Constraint:
- Each governance-critical component must be defined independently of:
  - EV outputs
  - Probability outputs
  - Interaction outputs
  - Evaluation metrics
- No component may be defined using signals derived from system execution

---

## 5. Boundary Declaration Authority Constraint

Constraint:
- The Execution Boundary must be declared by a process independent of:
  - parameter training systems
  - simulation systems
  - evaluation systems

- Boundary declaration must be externally verifiable and not co-located with training infrastructure

---

## 6. Versioning and Traceability Constraint

Constraint:
- All governance-critical components must be versioned
- Each version must include:
  - timestamp
  - authoring authority identifier
  - change justification (non-EV-based)
- Previous versions must remain immutable and auditable

---

## 7. Conflict-of-Interest Constraint

Constraint:
- No governance authority may derive benefit from EV outcomes of the system
- No authority may adjust system configuration based on performance feedback loops
- Structural alignment between payoff structure and outcome space must not be performed by the same agent

---

## 8. External Influence Constraint

Constraint:
- External signals (e.g. market odds, rankings, human preferences) must not directly determine governance decisions
- External signals may only be used if:
  - they are explicitly declared
  - they are independent of system outputs
  - they are not correlated with EV or evaluation targets

---

## 9. Governance Validation Rule

Before any Execution Run, the system must verify:

- all governance-critical components are versioned
- authority separation constraints are satisfied
- no forbidden coupling exists between controlled components

If any condition fails:
- Execution Run is invalidated before initialization phase

---

## 10. Role in System

The Governance Layer ensures that system structure cannot be reconfigured into a self-reinforcing optimization loop.

Constraint:
- This layer operates outside execution
- This layer enforces pre-execution legitimacy of system configuration

---

## 11. Governance Binding Constraint (CRITICAL ADDITION)

Constraint:
Every Execution Run must reference a valid Governance Binding Certificate (GBC).

---

### 11.1 Definition: Governance Binding Certificate

A Governance Binding Certificate is a signed configuration object that contains:

- version of Outcome Space
- version of Payoff Structure (RULES.md)
- version of Exclusion Window
- version of Parameter Training Regime
- version of Execution Protocol
- version of System Integrity Validator
- authority identifiers for each governance component

---

### 11.2 Binding Requirement

Constraint:
- Every Execution Run must be explicitly bound to exactly one GBC
- No execution is valid without a GBC reference

---

### 11.3 Immutability Constraint

Constraint:
- Once an Execution Run begins, its GBC cannot change
- Any mismatch between runtime configuration and GBC invalidates execution

---

### 11.4 Validator Enforcement Requirement

Constraint:
The System Integrity Validator MUST verify:
- GBC existence
- GBC completeness
- GBC version consistency across all governance components

Fail if:
- any mismatch exists
- any component is missing from GBC