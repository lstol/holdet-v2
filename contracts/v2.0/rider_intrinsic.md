# Rider-Intrinsic Ontology — Holdet v2

---

## 1. Purpose of This Layer

This layer defines rider-intrinsic properties used by the system to model race outcomes.

It is strictly descriptive.

Constraint:
- This layer does not define probabilities, EV, or ranking logic
- This layer only defines the structure of rider-intrinsic variables
- No variable in this layer may encode race outcomes or evaluation signals

---

## 2. Definition: Rider-Intrinsic State

Rider-Intrinsic State is the set of properties that describe a rider independent of a specific race event.

These properties are intended to represent stable or slowly evolving characteristics.

Constraint:
- Rider-Intrinsic State must not include any variable derived from race results within the exclusion window
- Rider-Intrinsic State must not include evaluation-derived signals or competition outcomes

---

## 3. Core Rider Attributes

The system permits the following categories of rider-intrinsic attributes:

### 3.1 Physiological Capacity

Represents physical capabilities relevant to cycling performance.

Includes:
- sustained power output capacity
- anaerobic capacity
- fatigue resistance profile

Constraint:
- Must be derived from non-race outcome data sources or externally measured physiological data
- Must not be inferred directly from race finishing positions

---

### 3.2 Terrain Affinity Profile

Represents relative rider suitability across terrain types.

Includes:
- climbing suitability
- sprint suitability
- time-trial suitability
- mixed terrain suitability

Constraint:
- Must be computed independently of race outcome data within the exclusion window
- Must not encode ranking or finishing position information

---

### 3.3 Consistency Profile

Represents variability in rider performance under similar conditions.

Includes:
- performance variance across comparable efforts
- stability of output under repeated conditions

Constraint:
- Consistency Profile must be computed only from non-race-derived performance measurements
- Any metric derived from race timing, gaps, splits, or positional changes is classified as race-derived and prohibited

---

### 3.4 Recovery Dynamics

Represents how rider performance degrades or recovers over time.

Includes:
- fatigue accumulation rate
- recovery rate between efforts
- multi-stage endurance characteristics

Constraint:
- Recovery Dynamics must be derived only from:
  - training load data
  - physiological measurements
  - controlled laboratory or training measurements not derived from organized race events
- Any data originating from organized race events is classified as race-derived and prohibited
- If sufficient non-race data is unavailable, the attribute must be treated as unobserved rather than inferred

---

## 4. Time Behavior Constraints

Rider-Intrinsic attributes evolve over time.

Time Horizon Constraint:

Rider-Intrinsic updates must use aggregation windows that strictly exclude all data within the exclusion window.

Constraint:
- Aggregation windows must not intersect the exclusion window
- No additional safety margin parameter is permitted

---

## 5. Non-Allowable Constructs

The following are explicitly prohibited in Rider-Intrinsic Ontology:

- any data originating from organized race events, regardless of timing
- race finishing positions
- stage results
- leaderboard rankings
- evaluation metrics of any kind
- simulation-derived performance outputs

These are classified as non-intrinsic signals.

---

## 6. Ontological Separation Invariant

The Rider-Intrinsic layer must remain independent of:

- Evaluation Objective Layer
- System Objective Layer
- Payoff Structure
- Simulation outputs
- External proxy signals (e.g. betting markets, rankings, odds)

Constraint:
- No transformation of external or evaluation data may enter Rider-Intrinsic State under any representation

---

## 7. Output Role of This Layer

This layer does not compute probabilities or EV.

It provides structured inputs for downstream modeling layers that:
- estimate race-specific performance distributions
- compute conditional probabilities
- derive EV from payoff structure

Constraint:
- This layer is input-only and has no evaluative or predictive authority

---

## Information Source Constraint

Rider-Intrinsic attributes may not be derived from any transformation of race data, regardless of representation, intermediate variables, or processing steps.

Constraint:
- Any data originating from race events (including splits, pacing, gaps, positional deltas) is classified as race-derived and prohibited
- Prohibition applies even if the data is transformed, normalized, aggregated, or not explicitly labeled as race outcome data
