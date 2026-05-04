# Objective Layer — Holdet v2

---

## 1. System Objective (Internal Mechanistic Objective)

The system models cycling race outcomes as probability distributions over a defined outcome space, derived strictly from rider and race state inputs defined in the contract system.

Constraint:
- The system objective is limited to producing internally consistent probability distributions over defined outcomes
- “Structural correctness” is defined as internal consistency of probability distributions under the rules of Layer 3 and Layer 4
- “EV consistency” is defined as arithmetic consistency between probability outputs and payoff structure inputs
- No external performance metric, ranking, or evaluation result is part of this definition

---

## 2. Evaluation Objective (External Measurement Layer)

The evaluation objective defines how system outputs are assessed externally.

Examples include:
- competition ranking (e.g., Holdet leaderboard position)
- predictive accuracy against realized race outcomes
- comparative performance vs other participants

Constraint:
- No data derived from Evaluation Objective (including prior-run outcomes, rankings, or performance metrics) may be used in any training, calibration, or parameterization process at any time
- This includes delayed, cached, or externally stored evaluation outputs

---

## 3. Human Objective (External Intent Layer)

The human objective represents user or operator goals external to the system.

Example:
- Achieve top 100 ranking in the Holdet competition

Constraint:
- Human Objective may not influence any system inputs, configurations, parameters, or payoff structure definitions
- All system-affecting decisions are part of the contract system and are therefore prohibited as influence channels for Human Objective

---

## 4. Separation Invariants

The following invariants apply globally:

1. System Objective is independent of Evaluation Objective
2. Evaluation Objective is independent of system computation
3. Human Objective is external to both system and evaluation
4. No feedback loops are permitted between layers