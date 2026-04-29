Holdet v2 — Contract Manifest v2.0 (Draft)

Layer Definitions

Layer 0 — Rider-Intrinsic

Definition: Rider properties independent of any race context.

Constraints:

* Must not depend on Race-State variables
* Must not include time-indexed variables within a race
* Rider-Intrinsic values must be frozen at race initialization.

Constraint:
- Values cannot be recomputed, updated, or replaced during race execution
- Any change constitutes a contract violation

Provenance Constraint — Rider-Intrinsic:

Rider-Intrinsic values must not be derived from:
- race-specific data
- recent race outcomes within a defined recency window

All inputs must be:
- longitudinal
- context-independent

⸻

Layer 1 — Race-State

Definition: All dynamic, time-indexed race context.

Constraints:

* Must be recomputable from raw inputs
* Must not define rider identity

⸻

Layer 2 — Interaction

Definition: Derived logic combining Rider-Intrinsic and Race-State.

Constraints:

* May depend on Layer 0 and Layer 1 only
* Must not write back into Layer 0
* Layer 2 must not modify Layer 1.
* Layer 1 is read-only during execution.

⸻

Layer 3 — Probability

Definition: Outcome likelihoods derived from Interaction.

Constraints:

* Must not depend on EV
* Must be inspectable independent of simulation

⸻

Layer 4 — EV

Definition: Expected value computed from probabilities and payoff structure.

Constraints:

* Must not depend on simulation paths
* Must not influence probabilities

⸻

Global Invariants

1. No downward mutation:
A higher-numbered layer must not modify any lower-numbered layer.

Allowed:
Layer 0 → Layer 4 (read flow)

Forbidden:
Layer 4 → Layer 0
Layer 2 → Layer 1
Layer 3 → Layer 2

2. All outputs must be reproducible from inputs
3. All variables must declare layer origin
4. Any violation invalidates the computation

Reproducibility Constraint:

All Race-State computations must reference a fixed snapshot of raw inputs.

Live or streaming data sources must be versioned or snapshotted.

Parameter Independence Constraint:

Parameters used in Layer 3 (Probability) must not be trained on:
- EV outputs
- signals derived from Layer 4

Violation constitutes indirect dependency.

⸻

Definitions

Definition — Dependency:
A component A depends on component B if:
- A reads values derived from B
- A uses parameters trained on data derived from B
- A shares mutable state with B

Definition — Raw Inputs:
Raw inputs are external, time-indexed observations that:
- are not derived from system outputs
- are recorded independently of the system
- can be snapshotted for reproducibility

Definition — Simulation:
A process that generates outcome distributions through iterative or path-dependent state evolution.

Constraint:
- Simulation outputs may inform probability estimation
- Simulation paths must not define EV structure or outcomes
