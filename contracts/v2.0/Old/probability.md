# Probability Layer — Holdet v2

---

## 1. Purpose of This Layer

This layer defines probability distributions over race outcomes.

Constraint:
- This layer is the only layer permitted to define probabilities
- All probabilistic modeling must occur exclusively within this layer
- This layer must not compute expected value (EV)

---

## 2. Definition: Probability Output

Probability Output is a set of probability distributions over defined outcome spaces.

Examples:
- probability of stage win
- probability of top-k finish
- probability of being in breakaway at finish

Constraint:
- All outputs must be valid probability distributions (sum to 1 where applicable)
- All probabilities must be explicitly represented (no implicit or embedded probabilities)

---

## 3. Input Constraints

This layer may depend only on:

- Interaction Layer outputs (Layer 2)

Constraint:
- No direct dependency on Rider-Intrinsic Layer (Layer 0)
- No direct dependency on Race-State Layer (Layer 1)
- No dependency on EV Layer (Layer 4)
- No dependency on Evaluation or Human Objective layers

---

## 4. Structural Independence Constraint

Probability must be structurally independent of EV.

Constraint:
- No EV values, signals, or transformations may be used in probability computation
- No parameter, weight, or model component may be derived from EV outputs
- Probability distributions must be definable without reference to payoff structure

---

## 5. Parameter Provenance Constraint

All parameters used in probability modeling must satisfy:

Constraint:
- Parameters must not be derived from:
  - EV outputs
  - evaluation metrics
  - simulation outputs
- Parameters must be fixed prior to execution
- Parameters must be versioned and reproducible
- Training data used for parameter estimation must not be selected, filtered, or weighted based on payoff structure or evaluation outcomes
- No training objective may optimize for EV, ranking performance, or competition outcomes
- Training procedures must target likelihood estimation or statistical fit to observed race events only
---

## 6. Computation Constraint

Constraint:
- Probability outputs must be computable from Interaction Outputs and fixed parameters only
- No simulation process may be invoked during execution
- No stochastic sampling (e.g. Monte Carlo) is permitted at runtime

---

## 7. Inspectability Constraint

Constraint:
- Probability outputs must be inspectable as explicit functions of inputs and parameters
- The mapping from inputs to probabilities must be transparent and reproducible
- No hidden or opaque transformations are permitted

---

## 8. Isolation Constraint

Constraint:
- Probability outputs must not be written back to any upstream layer
- Probability outputs must not influence Interaction Outputs
- No shared mutable state is permitted between this layer and any other layer

---

## 9. Non-Allowable Constructs

The following are explicitly prohibited:

- expected value calculations
- payoff structure inputs
- simulation-based probability estimation at runtime
- parameters trained on EV or evaluation signals
- feedback loops from EV layer

---

## 10. Role in System

This layer produces probability distributions used by the EV layer.

Constraint:
- This layer has no knowledge of payoff structure
- This layer does not optimize for outcomes or rankings
- This layer defines likelihoods only, not desirability

## Outcome Space Constraint

Outcome spaces must be defined independently of payoff structure and evaluation objectives.

Constraint:
- Outcome spaces must represent physically observable race events or states
- Outcome spaces must not be selected based on their relevance to scoring, rewards, or EV computation
- The definition of outcome spaces must be invariant across different payoff structures
- Outcome spaces must not collectively define an ordered ranking structure over riders
- Sets of outcomes must not be constructed as nested or cumulative rank thresholds (e.g. top-k sequences)
- Outcome definitions must not enable reconstruction of full or partial rider ordering without additional modeling assumptions

## Input Trust Constraint

The Probability Layer assumes that Interaction Layer outputs comply with their constraints.

Constraint:
- The Probability Layer does not validate upstream provenance
- Any violation originating in upstream layers is considered out of scope
- This layer must not introduce transformations that amplify or reinterpret potential upstream violations

## Functional Simplicity Constraint

Probability mappings must be structurally simple and interpretable.

Constraint:
- Mappings must not rely on high-dimensional lookup tables or exhaustive input-output mappings
- Functions must be expressible in a compact parametric form
- The number of parameters must be small relative to the dimensionality of inputs
- No construction may approximate a memorized mapping from inputs to probabilities