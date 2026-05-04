# Interaction Layer — Holdet v2

---

## 1. Purpose of This Layer

This layer defines how Rider-Intrinsic attributes and Race-State variables are combined to produce race-specific interaction features.

Constraint:
- This layer is purely transformational
- This layer does not define probabilities, EV, or outcomes
- This layer has no authority to rank, score, or evaluate riders

---

## 2. Definition: Interaction Output

Interaction Output is a set of derived variables representing how a rider’s intrinsic characteristics interact with the current race conditions.

Examples:
- climbing demand vs rider climbing capacity
- sprint suitability under current race fatigue
- terrain-adjusted performance differentials

Constraint:
- All Interaction Outputs must be computable solely from Rider-Intrinsic and Race-State inputs
- No external data sources are permitted
- Interaction Outputs must not represent expectations, likelihoods, or any probability-weighted quantities
---

## 3. Functional Constraints

---

### 3.1 No State Mutation

Constraint:
- This layer must not modify Rider-Intrinsic State
- This layer must not modify Race-State
- This layer must not persist any derived data beyond execution scope

---

### 3.2 No Temporal Feedback

Constraint:
- Interaction Outputs must not be used to update Rider-Intrinsic attributes
- Interaction Outputs must not be reused across race events
- No cross-race aggregation is permitted

---

### 3.3 No Outcome Encoding

Constraint:
- Interaction Outputs must not encode race outcomes, rankings, or evaluation signals
- No transformation may produce variables equivalent to predicted finishing position or rank

---

### 3.4 No Proxy Construction

Constraint:
- Interaction Outputs must not construct proxies for prohibited variables
- Any transformation that reconstructs evaluation signals (explicitly or implicitly) is prohibited

---

## 4. Dependency Constraints

Interaction Layer depends only on:

- Rider-Intrinsic Layer (Layer 0)
- Race-State Layer (Layer 1)

Constraint:
- No dependency on Probability Layer
- No dependency on EV Layer
- No dependency on Evaluation or Human Objective layers

---

## 5. Output Structure Constraint

Interaction Outputs must be:

- deterministic given inputs
- fully recomputable
- free of hidden state or learned parameters
- normalized or relative metrics computed across riders within the same race

Constraint:
- No parameterization based on past runs
- No learned weights derived from evaluation signals

---

## 6. Isolation Constraint

Constraint:
- Interaction Outputs must not be stored, cached, or reused beyond the current computation
- No artifact containing Interaction Outputs may persist across runs

---

## 7. Non-Allowable Constructs

The following are explicitly prohibited:

- probability estimates
- expected value calculations
- ranking or scoring systems
- learned parameters influenced by evaluation outcomes
- any use of simulation outputs

---

## 8. Role in System

This layer provides structured, context-specific features for downstream modeling layers.

It enables:
- probability estimation (Layer 3)
- EV computation (Layer 4)

Constraint:
- This layer has no predictive authority
- This layer only defines structured inputs

## Set-Level Constraint

Interaction Outputs must not enable consistent ordering of riders within a race through any single variable or combination of variables.

Constraint:
- Outputs must not be monotonic transformations of a shared latent scalar across riders
- Outputs must not be normalized, standardized, or scaled relative to other riders in the same race
- No transformation may encode a rider’s relative position within the field (e.g. percentile, rank-equivalent, or distribution-relative metric)
- No combination of outputs may produce a stable total ordering without introducing external modeling assumptions in downstream layers

## Input Trust Constraint

The Interaction Layer assumes that all upstream inputs comply with their respective layer constraints.

Constraint:
- The Interaction Layer does not validate input provenance
- Any violation originating in upstream layers is considered out of scope for this layer
- This layer must not introduce additional transformations that obscure or reinterpret input provenance
