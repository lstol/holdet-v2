#!/usr/bin/env python3
"""
Review contender pool for a given stage, showing which riders are
research-grounded vs synthetic, so garbage-in-garbage-out risk is visible.

Usage:
  python3 scripts/review_contender_pool.py 1      # Sprint stage
  python3 scripts/review_contender_pool.py 7      # Mountain stage (Blockhaus)
  python3 scripts/review_contender_pool.py        # Prompts for stage number
"""

import json, sys, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# How the stage finish_type maps to the affinity we care about.
# Uses roadbook finish_type (sprint/uphill/summit/mountain/hilly/tt/ttt).
FINISH_TYPE_ATTR = {
    "sprint":   ("sprint",    0.65),
    "hilly":    ("mixed",     0.45),   # puncheur_affinity maps to mixed
    "uphill":   ("mixed",     0.45),
    "summit":   ("climbing",  0.55),
    "mountain": ("climbing",  0.55),
    "tt":       ("time_trial", 0.55),
    "ttt":      ("time_trial", 0.40),
}


def apply_overrides(rider: dict, stage_n: int, overrides: list[dict]) -> dict:
    """
    Apply attribute overrides to rider, returning a shallow-copy with
    terrain_affinity updated. Also attaches _giro_role_2026 if present.

    Override attribute names → terrain_affinity keys:
      sprint_affinity    → sprint
      climbing_affinity  → climbing
      puncheur_affinity  → mixed
      gc_affinity        → gc          (new key, not in original data)
      breakaway_affinity → breakaway   (new key)
      tt_affinity        → time_trial
    """
    ATTR_MAP = {
        "sprint_affinity":    "sprint",
        "climbing_affinity":  "climbing",
        "puncheur_affinity":  "mixed",
        "gc_affinity":        "gc",
        "breakaway_affinity": "breakaway",
        "tt_affinity":        "time_trial",
    }

    rider_ovs = [
        o for o in overrides
        if o.get("holdet_id") == rider.get("holdet_id")
        and o.get("stage_first_applicable", 1) <= stage_n
    ]
    if not rider_ovs:
        return rider

    import copy
    r  = copy.copy(rider)
    ta = dict(r.get("terrain_affinity", {}))

    for ov in rider_ovs:
        mapped = ATTR_MAP.get(ov["attribute"])
        if mapped:
            ta[mapped] = ov["value"]
        if ov.get("giro_role_2026"):
            r["_giro_role_2026"] = ov["giro_role_2026"]

    r["terrain_affinity"] = ta
    return r


def review_contender_pool(stage_n: int) -> None:
    roadbooks = {r["stage"]: r
                 for r in json.loads((BASE / "data/stages/stage_roadbook.json").read_text())}

    rb = roadbooks.get(stage_n)
    if not rb:
        print(f"Stage {stage_n} not found in stage_roadbook.json")
        return

    finish_type = rb.get("finish_type", "sprint")
    stage_type  = rb.get("stage_type",  "flat")

    ta_key, threshold = FINISH_TYPE_ATTR.get(finish_type, ("sprint", 0.65))

    riders_raw  = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
    active      = [r for r in riders_raw
                   if r.get("status") == "active" and r.get("holdet_id")]

    overrides_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
    overrides: list[dict] = []
    if overrides_path.exists():
        raw = yaml.safe_load(overrides_path.read_text()) or {}
        overrides = raw.get("overrides", [])

    enriched = [apply_overrides(r, stage_n, overrides) for r in active]

    researched_ids = {o["holdet_id"] for o in overrides if o.get("source") == "web_search"}

    contenders = [r for r in enriched
                  if r.get("terrain_affinity", {}).get(ta_key, 0) >= threshold]
    contenders.sort(key=lambda r: -r["terrain_affinity"].get(ta_key, 0))

    print(f"\n=== Stage {stage_n} contender pool ===")
    print(f"    Stage type: {stage_type}  |  Finish: {finish_type}")
    print(f"    Ranked by {ta_key} ≥ {threshold}\n")
    print(f"{'Name':<30} {'Team':<28} {ta_key:<12}  Source         Role")
    print("─" * 110)

    for r in contenders:
        val    = r["terrain_affinity"].get(ta_key, 0)
        source = "✓ researched" if r["holdet_id"] in researched_ids else "⚠ synthetic "
        role   = (r.get("_giro_role_2026", "") or "")[:35]
        print(f"{r['name']:<30} {r.get('team',''):<28} {val:.2f}{'':>8}  {source}   {role}")

    synthetic_count = sum(1 for r in contenders if r["holdet_id"] not in researched_ids)
    total = len(contenders)

    print(f"\n{total} riders in pool — {total - synthetic_count} researched, "
          f"{synthetic_count} synthetic")

    if synthetic_count > 0:
        stage_arg = {"sprint": "sprint", "hilly": "hilly",
                     "summit": "mountain", "mountain": "mountain",
                     "uphill": "hilly", "tt": "itt", "ttt": "itt"}.get(finish_type, "sprint")
        print(f"\n⚠  {synthetic_count} riders still using synthetic attributes.")
        print(f"   Run: python3 scripts/gather_rider_intelligence.py --stage-type {stage_arg}")


if __name__ == "__main__":
    stage_n = int(sys.argv[1]) if len(sys.argv) > 1 else int(input("Stage number: "))
    review_contender_pool(stage_n)
