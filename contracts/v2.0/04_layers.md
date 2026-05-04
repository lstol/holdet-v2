# Holdet v2 — Layer Contracts
# 04_layers.md

All definitions in 01_system_canonical.md apply throughout this file.

---

## Layer 0 — Rider-Intrinsic

**Definition:** The set of rider properties describing a rider independently of any specific race event. Properties are stable or slowly evolving. Strictly descriptive. No evaluative or predictive authority.

### Permitted Attributes

**Physiological Capacity**
Sustained power output capacity, anaerobic capacity, fatigue resistance profile.
- Must be derived from non-race-outcome data sources or externally measured physiological data
- Must not be inferred from race timing, gaps, splits, positional deltas, or finishing positions through any number of transformation steps

**Terrain Affinity Profile**
Climbing suitability, sprint suitability, time-trial suitability, mixed terrain suitability.
- Must be computed independently of race outcome data
- Must not encode ranking or finishing position information

**Consistency Profile**
Performance variance across comparable efforts, stability of output under repeated conditions.
- Must be computed only from non-race-derived performance measurements
- Any metric derived from race timing, gaps, splits, or positional changes is classified as race-derived and prohibited

**Recovery Dynamics**
Fatigue accumulation rate, recovery rate between efforts, multi-stage endurance characteristics.
- Must be derived only from training load data, physiological measurements, or controlled non-competitive performance tests
- A non-competitive performance test: a controlled measurement event not conducted under sanctioned race conditions, not producing published results, not classified as a competitive event by any governing body
- Multi-stage race data is classified as race-derived and prohibited
- If sufficient non-race data is unavailable, the attribute must be treated as unobserved rather than inferred

### Constraints

**Freeze constraint:** Values must be frozen at race initialization. Cannot be recomputed, updated, or replaced during race execution. Any change constitutes a contract violation.

**Provenance constraint:** All inputs must originate from data outside the exclusion window. No data from any part of the current race may be included. Any aggregation whose input domain intersects the exclusion window is prohibited regardless of weighting.

**Time horizon constraint:** Updates must use aggregation windows strictly greater than the exclusion window plus the system-defined safety margin declared in the GBC. The safety margin must be greater than zero and is not runtime-adjustable.

**Information source constraint:** Attributes may not be derived from any transformation of race data regardless of representation, intermediate variables, or processing steps. Data from race events — splits, pacing, gaps, positional deltas — is race-derived and prohibited even if transformed, normalized, or aggregated.

**Stage result constraint:** All stage results are prohibited regardless of timing relative to the exclusion window. Historical data indexed or conditioned on specific races or stages is prohibited.

### Prohibited Constructs

Race finishing positions, leaderboard rankings, stage results of any kind, evaluation metrics, simulation-derived performance outputs, external proxy signals (betting markets, rankings, odds).

### Ontological Separation

This layer must remain independent of the Evaluation Objective, System Objective, Payoff Structure, simulation outputs, and all external proxy signals. No transformation of external or evaluation data may enter Rider-Intrinsic State under any representation.

---

## Layer 1 — Race-State

**Definition:** The set of variables describing the current race environment and its evolution over time. All variables are tied to a specific race event or stage and do not persist beyond that scope.

### Permitted Components

**Course Structure**
Elevation profile, distance, segment classification (climb, flat, descent), technical characteristics.
- Must be derived from course design data, not rider outcomes

**Environmental Conditions**
Weather conditions (wind, temperature, precipitation), road surface conditions.
- Must be exogenous to rider performance
- Must not be inferred from race outcomes

**Race Progression State**
Current race phase (early, mid, final), breakaway presence and structure, peloton composition and fragmentation, time gaps between groups.
- May be derived from race telemetry and observation
- Must not be stored or reused outside the current race context
- Peloton composition and time gaps encode cumulative performance differentials; downstream layers must not use them to reconstruct GC standings or evaluation signals

**Temporal Position**
Elapsed distance, remaining distance, time since race start.
- Must be strictly tied to current race instance
- Must not reference historical race timelines

### Constraints

**Read-only:** Layer 1 is read-only for all consuming layers. No downstream layer — including Layers 2, 3, and 4 — may modify Race-State.

**Isolation:** Race-State must remain fully isolated from Rider-Intrinsic State. Race-State data must not be written to or used to update Rider-Intrinsic attributes. No aggregation of Race-State data may be persisted beyond the race event. Derived outputs must be discarded after race completion. This constraint binds all consuming layers, not only Layer 2.

### Prohibited Constructs

Evaluation metrics, EV outputs or derived signals, simulation outputs used as runtime inputs, data originating from Rider-Intrinsic updates.

---

## Layer 2 — Interaction

**Definition:** Derived variables representing how rider-intrinsic characteristics interact with current race conditions. Purely transformational. No evaluative or predictive authority. Does not define probabilities, EV, or outcomes.

### Permitted Inputs

Layer 0 and Layer 1 only. No external data sources permitted.

### Output Constraints

All outputs must be computable solely from Rider-Intrinsic and Race-State inputs and contain no hidden state, learned parameters, or opaque transformations.

**Expectation prohibition:** Outputs must not encode probability-weighted outcomes. "Expectations," "expected performance," and similar labels are prohibited. Outputs represent capability-condition matching only.

**Ranking prohibition (individual):** Outputs must not be individually equivalent to predicted finishing position or rank.

**Ranking prohibition (joint):** Outputs must not produce an orderable ranking of riders when computed across the rider set, even if no individual output constitutes a rank.

**Proxy prohibition:** Outputs must not construct proxies for prohibited variables — including evaluation metrics, rankings, or EV — explicitly or implicitly.

### Structural Constraints

**No state mutation:** Must not modify Rider-Intrinsic State or Race-State. Must not persist any derived data beyond execution scope.

**No temporal feedback:** Outputs must not update Rider-Intrinsic attributes. Outputs must not be reused across race events. No cross-race aggregation permitted.

**Isolation:** Outputs must not be stored, cached, or reused beyond the current computation. No artifact containing Interaction Outputs may persist across runs.

**Input provenance:** This layer cannot validate the provenance of its inputs at runtime. Provenance compliance for Layer 0 and Layer 1 is enforced by the SIV before execution begins.

### Prohibited Constructs

Probability estimates, expected value calculations, ranking or scoring systems, learned parameters influenced by evaluation outcomes, simulation outputs.

---

## Layer 3 — Probability

**Definition:** The only layer permitted to define probability distributions over race outcomes. All probabilistic modeling occurs exclusively within this layer. Does not compute expected value.

### Permitted Inputs

Interaction Layer outputs (Layer 2) only.
- No direct dependency on Layer 0 or Layer 1
- No dependency on Layer 4
- No dependency on Evaluation or Human Objective layers

### Output Constraints

All outputs must be valid probability distributions over the defined Outcome Space. Probabilities must sum to 1 where applicable. All probabilities must be explicitly represented — no implicit or embedded probabilities permitted.

### Independence Constraints

**EV independence:** No EV values, signals, or transformations may be used in probability computation. No parameter, weight, or model component may be derived from EV outputs. Probability distributions must be definable without reference to payoff structure.

**Outcome space independence:** The set of outcomes for which probabilities are computed must not be determined by which outcomes are rewarded under RULES.md. Outcome space selection is declared in the GBC.

### Parameter Constraints

- Must not be derived from EV outputs, evaluation metrics, or simulation outputs
- Must be fixed prior to the execution boundary
- Must be versioned and reproducible

### Simulation Constraint

Layer 3 parameters must not be derived from simulation outputs. Simulation may be used for post-hoc validation of fixed parameters only. Simulation outputs must not be used as inputs, features, or parameter sources.

### Computation Constraint

Outputs must be computable from Interaction Outputs and fixed parameters only. No simulation process may be invoked during execution. No stochastic sampling at runtime.

### Inspectability

The mapping from inputs to probabilities must be transparent, explicit, and reproducible. No hidden or opaque transformations permitted.

### Isolation

Probability outputs must not be written back to any upstream layer. No shared mutable state between this layer and any other layer.

---

## Layer 4 — EV (Expected Value)

**Definition:** The only layer permitted to compute expected value. EV is a descriptive metric, not a control signal.

**Formula:** EV = Σ(P(outcome) × payoff(outcome)) over all events in Outcome Space.

### Permitted Inputs

Probability Layer outputs (Layer 3) and Payoff Structure (02_rules_payoff.md) only.
- No dependency on Interaction Layer
- No dependency on Rider-Intrinsic Layer
- No dependency on Race-State Layer
- No dependency on Evaluation or Human Objective layers

**Rider-Intrinsic independence:** EV must not depend on Rider-Intrinsic inputs through any path. All Rider-Intrinsic influence must be mediated exclusively through Layer 3 probabilities.

### Directionality

Information flow into EV is strictly unidirectional. EV must not influence probability modeling, parameters, or feature construction. EV must not be used as input to any upstream layer.

### Output Constraints

- EV outputs must not be stored as inputs to any upstream layer
- EV outputs must not modify Probability Layer parameters
- EV outputs must not be used in training, calibration, or feature generation — in the current run or any future run
- EV outputs logged for any purpose are available at training time; any use in subsequent parameter training constitutes a dependency violation; this constraint spans all future runs

### Computation

EV must be computed deterministically from fixed probabilities and fixed payoff structure. No simulation, sampling, or stochastic estimation permitted. No runtime learning or adaptation permitted.

### Feedback Suppression

No information derived from EV may propagate backward into any layer — including through logging, caching, analyst interpretation, or governance processes.
