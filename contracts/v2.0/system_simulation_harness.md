# System Simulation Harness — Holdet v2

---

## 1. Purpose

The System Simulation Harness is a controlled testing environment for validating the Holdet v2 architecture.

Constraint:
- The harness does not represent production execution
- The harness is used only to detect structural violations and emergent leakage patterns
- The harness must not influence production parameters or configurations

---

## 2. Scope of Simulation

The harness simulates:

- Layer 0 → Layer 4 computation flow
- Execution Protocol phases
- System Integrity Validator checks
- Governance Layer constraints (as pre-validated inputs)

Constraint:
- Simulation is structurally faithful but not performance-optimized
- No real-world deployment assumptions are permitted

---

## 3. Simulation Inputs

Allowed inputs:

- Fixed snapshot of Rider-Intrinsic data
- Fixed snapshot of Race-State data
- Versioned Interaction parameters
- Versioned Probability parameters
- Versioned Payoff structure
- Versioned Governance configuration

Constraint:
- Inputs must be frozen prior to simulation start
- No live data ingestion is permitted

---

## 4. Simulation Constraints

Constraint:
- All Execution Protocol rules apply inside simulation
- All layer constraints must be enforced identically to production
- System Integrity Validator must run on every simulated execution

---

## 5. Violation Detection Mode

The harness operates in diagnostic mode:

- It does NOT halt execution on first violation
- It records all structural violations
- It categorizes violations by:
  - layer breach
  - cross-layer leakage
  - governance violation
  - execution protocol violation

---

## 6. Output Requirements

Simulation output must include:

- Full execution trace summary
- Detected structural violations
- Cross-layer dependency graph
- Any detected feedback loops

Constraint:
- No probabilistic performance evaluation is produced
- No EV-based optimization is performed in simulation

---

## 7. Anti-Leakage Constraint

Constraint:
- Simulation outputs must not be used as training data unless explicitly versioned and declared outside the system boundary
- Simulation findings are strictly observational unless externally reintroduced via Governance Layer procedures

---

## 8. Role in Architecture

The Simulation Harness is the only permitted environment for:

- stress testing constraint violations
- detecting semantic leakage
- validating execution determinism

Constraint:
- It is not part of the decision system
- It is a verification-only subsystem