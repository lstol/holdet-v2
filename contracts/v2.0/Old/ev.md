# Expected Value Layer — Holdet v2

---

## 1. Purpose of This Layer

This layer computes expected value (EV) from probability distributions and payoff structure.

Constraint:
- This is the only layer permitted to compute EV
- EV is a descriptive metric, not a control signal
- EV must not influence any upstream layer

---

## 2. Definition: Expected Value

Expected Value is the weighted sum of outcomes based on probability distributions and payoff values.

Formally:
- EV = Σ (P(outcome) × payoff(outcome))

Constraint:
- EV is a derived quantity only
- EV does not define probabilities or outcomes

---

## 3. Input Constraints

This layer may depend only on:

- Probability Layer outputs (Layer 3)
- Payoff Structure (external static mapping)

Constraint:
- No dependency on Interaction Layer
- No dependency on Rider-Intrinsic Layer
- No dependency on Race-State Layer
- No dependency on Evaluation or Human Objective layers

---

## 4. Structural Directionality Constraint

Constraint:
- Information flow into EV is strictly unidirectional
- EV must not influence probability modeling, parameters, or feature construction
- EV must not be used as input to any upstream layer

---

## 5. Payoff Structure Constraint

Constraint:
- Payoff structure is static and externally defined
- Payoff structure must not be derived from:
  - EV outputs
  - probability outputs
  - evaluation signals
- Payoff structure must remain invariant across model execution runs

---

## 6. Computation Constraint

Constraint:
- EV must be computed deterministically from fixed probabilities and fixed payoff structure
- No simulation, sampling, or stochastic estimation is permitted
- No runtime learning or adaptation is permitted

---

## 7. Isolation Constraint

Constraint:
- EV outputs must not be stored as inputs to any upstream layer
- EV outputs must not modify Probability Layer parameters
- EV outputs must not be used in training, calibration, or feature generation

---

## 8. Non-Allowable Constructs

The following are explicitly prohibited:

- using EV as a feature in probability modeling
- using EV in parameter tuning or training
- feedback loops from EV to any lower layer
- adaptive payoff adjustments based on EV outputs

---

## 9. Role in System

This layer evaluates the output of the probabilistic model under a fixed payoff structure.

Constraint:
- EV is a scoring function, not a control mechanism
- EV is purely observational within the system
- EV exists only to compare expected outcomes under fixed assumptions

---

## 10. Feedback Suppression Constraint

Constraint:
- No information derived from EV may propagate backward into any layer below EV
- Any process that uses EV for decision-making must occur outside the contract system boundary


## System Boundary Definition

The system boundary includes all layers defined in this contract system:
- Rider-Intrinsic Layer
- Race-State Layer
- Interaction Layer
- Probability Layer
- Expected Value Layer

Constraint:
- Any process outside these layers is considered external to the system
- External processes must not be assumed to be independent or non-influential to system inputs or parameters

## Observability Constraint

Constraint:
- EV outputs may be logged only for observability and debugging purposes
- Logged EV data is explicitly classified as system-generated metadata
- System-generated metadata must not be used as training data, parameter input, or calibration signal within the system

## Payoff Structure Governance Constraint

Constraint:
- Payoff structure updates must be performed through an explicit versioning process
- Updates must be independent of EV outputs from any single run
- No direct or indirect optimization of payoff structure based on EV feedback is permitted
- Cross-run consistency of payoff structure is enforced by version control, not runtime evaluation