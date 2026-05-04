# Holdet v2 — Execution & Validation
# 05_execution_and_validation.md

---

## 1. Execution State Machine

Execution is a finite state machine. All computation must occur inside locked phases. No cross-phase mutation is permitted.

### S0 — INITIALIZATION

Actions:
- Load 02_rules_payoff.md (immutable)
- Load 03_outcome_space.md (immutable)
- Load system configuration
- Verify Governance Binding Certificate (GBC) — fail if missing or incomplete
- Initialize dependency graph

Constraints:
- No computation permitted
- No probabilistic or model activity permitted
- Execution blocked if GBC validation fails

### S1 — CONTEXT FREEZE

Actions:
- Load Rider-Intrinsic Layer (Layer 0) snapshot
- Load Race-State Layer (Layer 1) snapshot
- Freeze all upstream inputs

Constraints:
- Inputs become immutable
- Any modification after this point invalidates execution

---
**EXECUTION BOUNDARY** declared here — recorded in GBC, immutable from this point
---

### S2 — MODEL FREEZE

Actions:
- Load Interaction Layer parameters
- Load Probability model parameters
- Load EV model parameters

Constraints:
- All parameters become immutable
- No retraining, recalibration, or adjustment permitted

### S3 — INFERENCE EXECUTION

Actions:
- Compute Interaction Outputs (Layer 2)
- Compute Probability distributions (Layer 3)
- Compute Expected Value (Layer 4)
- SIV runs after each layer

Constraints:
- No new data sources permitted
- No structural modification permitted
- No external input permitted

### S4 — OUTPUT FINALIZATION

Actions:
- Compute final EV-ranked outputs
- Emit system outputs
- Freeze output artifact

Constraints:
- Outputs become immutable upon emission
- No feedback into any prior layer permitted

---

## 2. Execution Rules

**No cross-state leakage:** No state S(n) may access S(n+1). No backward modification permitted.

**Parameter isolation:** All parameters must be fixed prior to S2. No runtime or mid-execution adjustment permitted.

**Output integrity:** Outputs may depend only on frozen inputs (S1) and frozen parameters (S2).

**Invalidation:** Any protocol violation results in immediate invalidation of execution and discard of all outputs from the current run.

**Post-execution cleanup:** All temporary state destroyed. No runtime memory persists. Only versioned outputs may be stored externally. Interaction Outputs are discarded unless explicitly versioned and declared through Governance mechanisms.

**Cross-run isolation:** No execution state may influence future runs. All cross-run influence must pass through Governance Layer mechanisms only.

---

## 3. System Integrity Validator (SIV)

The SIV performs deterministic graph validation before execution. It blocks execution if any check fails. It performs no probabilistic reasoning or semantic interpretation.

**Validation graph:** G = (Nodes, Edges) where Nodes = layers, variables, outcomes, parameters, rules; Edges = permitted dependencies. Only explicit edges are valid. Implicit or inferred edges are invalid.

### Checks

**Outcome Coverage:** Every scoring element in 02_rules_payoff.md must map to ≥1 event in 03_outcome_space.md. Fail if any scoring rule has no corresponding outcome mapping.

**Outcome Isolation:** Outcome nodes must not contain EV values, ranking signals, or payoff information. Fail if any outcome encodes value or desirability.

**Dependency Direction:** Only permitted flows from 01_system_canonical.md Section 3 may exist.
Allowed edges only:
- Layer 0 → Layer 2
- Layer 1 → Layer 2
- Layer 2 → Layer 3
- Layer 3 → Layer 4
- RULES.md → Layer 4

Fail if: reverse edges exist, skipped-layer edges exist (unless explicitly declared), any forbidden flow from 01_system_canonical.md Section 3 is present.

**Cross-Layer Leakage:** No upstream layer may encode downstream objectives. Detect EV-correlated proxies in Layer 0 or Layer 1, ranking signals in Layer 2, payoff-encoded features upstream of EV. Fail if any upstream node contains downstream objective information.

**Transfer Integrity:** TransferFeeApplied must equal 0.01 × TransferBuy.price, strictly deterministic. Fail if fee depends on EV, probability, or external signals.

**LateArrivalMinutes integrity:** Must be a non-negative truncated integer. Must not exceed 30. Must only be defined for riders with FinishStatus = FINISH on non-TTT stages. Fail if defined for DNS/DNF/DSQ riders or on TTT stages.

**TTTTeamPlacement integrity:** Must only be emitted on TTT stages. Must not coexist with StageFinishPosition for team-level scoring on the same stage. Fail if both are used for team scoring on the same stage.

**CaptainSelection integrity:** Exactly one CaptainSelection per team_entry per stage_t. Fail if zero or more than one.

**CaptainPositiveValueGrowth integrity:** Must be ≥ 0. Must only be emitted for the rider where CaptainSelection = true for that stage. Fail if emitted for non-captain rider or if value is negative.

**StageDepthCount integrity:** count must be in {0…8}. Must not be defined for TTT stages. Fail if count exceeds number of active riders or is defined on TTT stage.

**DNSRemainingStagePenalty integrity:** Must not be emitted for the abandonment stage (that stage is covered by FinishStatus = DNF). Must only be emitted for stages after abandonment. Fail if emitted on abandonment stage.

**EV computability check:** Verify that total EV is computable using only probability outputs over 03_outcome_space.md events and payoff values in 02_rules_payoff.md. Fail if any EV computation path references logic outside these two sources.

**Temporal Boundary:** Execution boundary must be defined before S2 and immutable after S2 begins. Fail if boundary is undefined, modified post-freeze, or inferred post-hoc.

**Cross-Run Contamination:** No outputs from run N may appear in run N+1 inputs unless explicitly declared as persistent state. Fail if implicit reuse of prior run outputs is detected.

**GBC Completeness:** GBC must exist, be complete, and be version-consistent across all governance components. Fail if any component is missing or mismatched.

### Outputs

**PASS** — system is structurally valid for execution.

**FAIL** — includes: violated rule ID, affected nodes, dependency path trace, reason for invalidation.

---

## 4. System Simulation Harness

The Simulation Harness is a controlled testing environment. It is not part of the decision system. It is a verification-only subsystem.

**Scope:** Simulates Layer 0–4 computation flow, Execution Protocol phases, SIV checks, and Governance constraints as pre-validated inputs.

**Mode:** Diagnostic. Does not halt on first violation. Records all structural violations categorized by: layer breach, cross-layer leakage, governance violation, execution protocol violation.

**Input constraints:** All inputs must be frozen prior to simulation start. All Execution Protocol rules apply identically to production. SIV must run on every simulated execution.

**Outputs:** Full execution trace, detected structural violations, cross-layer dependency graph, detected feedback loops. No probabilistic performance evaluation. No EV-based optimization.

**Anti-leakage constraint:** Simulation outputs must not be used as training data unless explicitly versioned and declared outside the system boundary through Governance procedures. Simulation findings are strictly observational. Parameter updates based on simulation findings violate GI-8 from 01_system_canonical.md.

---

## 5. Operator Protocol

The operator (Claude Code or equivalent) acts as a deterministic executor of this specification. It is not a system designer and must not modify architecture unless explicitly instructed via Governance Layer approval.

**Role:** Deterministic executor of defined pipelines, validator of constraint compliance, reporter of structural violations.

**Non-ambiguation rule:** If any of the following are unclear — layer behavior, dependency rule, input provenance, execution order, governance authority — the operator must stop execution and request clarification. Proceeding with inferred behavior is prohibited.

**Execution fidelity:** Execute layers in strict order. Enforce all stated constraints verbatim. Treat all "must" statements as hard constraints. Treat all undefined terms as blocking conditions. No probabilistic interpretation of rules is allowed.

**No creative resolution:** The operator must not resolve contradictions, choose between conflicting constraints, infer missing definitions, or harmonize incompatible rules. All conflicts are escalated, not resolved.

**Violation handling:**
1. Classify: layer violation, cross-layer leakage, governance violation, or execution protocol violation
2. Mark execution INVALID
3. Produce structured violation report
4. Do not attempt correction

**System hierarchy:** The operator is subordinate to Governance Layer, Execution Protocol, SIV, and layer contracts, in that order.

**Provenance enforcement:** Verify declared input origin at each layer. Reject inputs without explicit layer provenance. Flag upstream contamination suspicion. Provenance ambiguity = execution halt or diagnostic mode only.

---

## 6. Failure Handling Summary

| Failure Type | Response |
|-------------|----------|
| GBC missing or invalid | Block at S0 |
| SIV validation fail | Block before S1→S2 |
| Input provenance violation | Halt, report, diagnostic mode |
| Cross-layer mutation detected | Invalidate run, discard outputs |
| Parameter updated post-boundary | Invalidate run, discard outputs |
| Constraint ambiguity | Halt, escalate, do not infer |
| Cross-run contamination detected | Invalidate run, forward to Simulation Harness |
