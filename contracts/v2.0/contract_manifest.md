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

Rider-Intrinsic values must be derived from data outside a fixed exclusion window prior to race start.

Exclusion Window:
- A globally defined, versioned duration
- Must be greater than zero
- Must be consistent across all riders and runs

Exclusion Window Constraint:

The exclusion window must exceed the total duration of the current race.

Constraint:
- No data from any part of the current race may be included

Constraint:
- No data within the exclusion window may be used directly or indirectly

Aggregation Constraint:

Any aggregation whose input domain intersects the exclusion window is prohibited, regardless of weighting.

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
* Probabilities must be computable from declared inputs and fixed parameters only.
* No runtime dependency on simulation outputs is allowed.

Simulation Influence Constraint:

Layer 3 parameters must not be derived from simulation outputs.

Constraint:
- Simulation may be used for validation or comparison only
- Simulation outputs must not be used as inputs, features, or parameter sources

⸻

Layer 4 — EV

Definition: Expected value computed from probabilities and payoff structure.

Constraints:

* Must not depend on simulation paths
* Must not influence probabilities
* EV must not depend on Rider-Intrinsic inputs.

All Rider-Intrinsic influence must be mediated through Layer 3 probabilities.

* All Rider-Intrinsic influence must be mediated through Layer 3 probabilities.

⸻

Payoff Structure Definition:

Payoff structure is a static mapping defined outside the system from outcomes to value.

Constraints:
- Must not depend on Rider-Intrinsic, Race-State, or system outputs
- Must be versioned and fixed prior to execution
- Must not be updated using EV outputs or derived signals

Payoff Governance Constraint:

Changes to payoff structure must not be informed by:
- EV outputs
- patterns observed in EV outputs
- any analysis derived from system outputs

This includes both direct and indirect influence, including human judgment based on system behavior.

⸻

Global Invariants

No Downward Mutation (General Rule):

No layer may modify any lower-numbered layer.

This applies to all layers without exception.

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

State Isolation Constraint:

No mutable state may be shared across layers.

All inter-layer communication must occur through explicit, immutable outputs.

Dependency Closure Constraint:

A layer is considered dependent on another layer if it consumes any artifact that encodes, aggregates, or transforms outputs from that layer, regardless of where the artifact is produced.

Constraint:
- Indirect access via intermediate artifacts does not break dependency
- All such dependencies are treated as direct dependencies

External Proxy Constraint:

Inputs that are statistically or structurally correlated with system outputs must not be used in any layer.

Constraint:
- External signals that encode outcome expectations (e.g. market prices, odds, rankings, model outputs) are prohibited in:
  - Layer 0 (Rider-Intrinsic)
  - Layer 3 (Probability)
  - Payoff Structure

- Derived variables that incorporate such signals are also prohibited

This constraint applies to ALL layers (Layer 0 through Layer 4).

No layer may consume inputs that encode or approximate outcome expectations derived from external systems (e.g. betting markets, rankings, predictive scores, odds).

Execution Authority Constraint:

The execution boundary must be established by an external, pre-defined process independent of model training or parameter updates.

Requirements:
- The boundary must be recorded before any parameter training or updates for the run
- The boundary record must include identifiers of all inputs, parameters, and configurations to be used
- Any parameter updated after the boundary record is invalid for that run
- The boundary record cannot be created, modified, or validated by the same process that performs parameter training or updates

Simulation Steering Constraint:

Simulation outputs must not influence parameter selection for any execution run.

Constraint:
- Simulation results may only be used within the same training phase in which parameters are finalized
- Simulation findings may not persist across execution boundaries or influence future runs

Run Isolation Constraint:

Each execution run is independent.

Constraint:
- Outputs, parameters, and evaluations from any previous run may not be used to update or select parameters for a new run
- Cross-run learning or adjustment is prohibited unless explicitly performed in a separate training phase outside execution

⸻

Definitions

Definition — Dependency:
A component A depends on component B if:
- A reads values derived from B
- A uses parameters trained on data derived from B
- A shares mutable state with B

"derived from" includes:
- direct use
- aggregation
- transformation
- parameter training influence

Definition — Raw Inputs:

Raw inputs are external observations that:

- are not generated by this system or any prior run of this system
- are recorded independently of system computation
- are time-indexed and snapshotted

Constraint:
- Outputs from prior system runs are explicitly forbidden as raw inputs

Definition — Simulation:

A process that generates outcome distributions through iterative or path-dependent state evolution.

Simulation Usage Constraint:

Simulation may only be used prior to the execution boundary.

Any artifacts produced by simulation must be:
- finalized
- versioned
- and immutable before execution begins

Definition — Context-Independent:

A variable is context-independent if it can be computed without access to:

- race-specific inputs (past or present)
- stage-specific inputs (past or present)
- time-indexed race data within the exclusion window

Constraint:
- Historical data that is indexed or conditioned on specific races or stages is prohibited

Definition — Execution Boundary:

The execution boundary is a declared checkpoint that marks the transition from configuration phase to execution phase.

Constraint:
- The boundary is declared before any parameter training or execution begins
- Once declared, no training, parameter updates, or configuration changes may occur for that run
