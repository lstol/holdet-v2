# interface/

User interfaces. Two phases.

| Subfolder | Phase | Purpose |
|-----------|-------|---------|
| `early/` | Phase 3 | Inspection UI — rider cards, stage profiles, interaction diagnostics, EV table, override panel |
| `operational/` | Phase 6 | Full dashboard — pre-stage briefing, live diagnostic mode, post-stage review |

## Design constraint
Interface renders system outputs for human inspection and override. It does not compute probabilities or EV — it consumes engine outputs only.
