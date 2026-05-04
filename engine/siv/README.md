# engine/siv/

System Integrity Validator. Runs before execution begins. Blocks execution on any failure.

## Checks
- Outcome coverage (every RULES.md element maps to Outcome Space)
- Dependency direction (no forbidden flows)
- Cross-layer leakage detection
- Execution boundary integrity
- Cross-run contamination check
- GBC completeness

## Output
PASS → execution proceeds
FAIL → violated rule ID, affected nodes, dependency path, reason
