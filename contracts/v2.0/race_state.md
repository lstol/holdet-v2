# Race-State Ontology — Holdet v2

---

## 1. Purpose of This Layer

This layer defines race-specific state variables used to model the current race event.

Constraint:
- This layer may include data derived from organized race events
- This layer must not define rider-intrinsic properties
- This layer must not influence Rider-Intrinsic State through any path

---

## 2. Definition: Race-State

Race-State is the set of variables describing the current race environment and its evolution over time.

Includes:
- stage profile
- course characteristics
- environmental conditions
- race progression state

Constraint:
- All variables must be tied to a specific race event or stage
- No variable may persist beyond the scope of a race event

---

## 3. Core Race-State Components

---

### 3.1 Course Structure

Describes the physical structure of the race.

Includes:
- elevation profile
- distance
- segment classification (climb, flat, descent)
- technical characteristics

Constraint:
- Must be derived from course design data, not rider outcomes

---

### 3.2 Environmental Conditions

Describes external conditions affecting performance.

Includes:
- weather conditions (wind, temperature, precipitation)
- road surface conditions

Constraint:
- Must be exogenous to rider performance
- Must not be inferred from race outcomes

---

### 3.3 Race Progression State

Describes the dynamic state of the race as it unfolds.

Includes:
- current race phase (early, mid, final)
- breakaway presence and structure
- peloton composition and fragmentation
- time gaps between groups

Constraint:
- May be derived from race telemetry and observation
- Must not be stored or reused outside the current race context
- Race progression variables (including time gaps, group structure, and composition) are observational only
- These variables must not be interpreted as outcome labels, rankings, or evaluation targets
- No transformation of these variables may produce explicit or implicit ranking signals
---

### 3.4 Temporal Position

Represents position within the race timeline.

Includes:
- elapsed distance
- remaining distance
- time since race start

Constraint:
- Must be strictly tied to current race instance
- Must not reference historical race timelines

---

## 4. Race-State Isolation Constraint

Race-State must remain fully isolated from Rider-Intrinsic State.

Constraint:
- Race-State data must not be written to or used to update Rider-Intrinsic attributes
- No aggregation of Race-State data may be persisted beyond the race event
- Any derived outputs must be discarded after race completion

---

## 5. Non-Allowable Constructs

The following are prohibited within Race-State:

- evaluation metrics (e.g. ranking, leaderboard position)
- EV outputs or derived signals
- simulation outputs used as runtime inputs
- any data originating from Rider-Intrinsic updates
- any explicit or derived representation of rider ranking, general classification 
position, or expected race outcome

---

## 6. Cross-Layer Interaction Constraint

Race-State may be consumed by downstream layers (Interaction, Probability, EV), but:

Constraint:
- Race-State must not be modified by any downstream layer
- Race-State must not receive feedback from Probability or EV layers
- All interactions must be read-only and one-directional

---

## 7. Output Role of This Layer

Race-State provides contextual inputs for modeling race dynamics.

It enables:
- interaction modeling between riders and environment
- conditional probability estimation

Constraint:
- This layer does not compute probabilities or EV
- This layer has no evaluative authority

## 8. Cross-Layer Persistence Constraint

Constraint:
- No data derived from Race-State may be persisted, stored, or reused beyond the scope of the current race event
- This constraint applies to all layers that consume Race-State
- Any artifact, parameter, or intermediate output containing Race-State information must be discarded after race completion