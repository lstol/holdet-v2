# models/

Probability model parameters. All parameters versioned. No binary blobs without accompanying version manifest.

| Subfolder | Phase | Contents |
|-----------|-------|----------|
| `baseline/` | Phase 3 | Rule-based probability model — no ML, inspectable logic |
| `v1/` | Phase 4 | First trained model — StageFinishPosition, GC, DNF risk |

## Constraints
- Parameters must be fixed before execution boundary
- Parameters must not be derived from EV outputs or evaluation metrics
- Each parameter set requires a version manifest declaring training data source and exclusion window version
