#!/usr/bin/env python3
"""
Build data/stages/stage_roadbook.json with official Giro sprint/KOM point scales.

Sprint and KOM point values are fixed, public, and deterministic per the
official Giro d'Italia roadbook. No estimation or calibration constants.

Sources:
  - km locations: data/stages/stage_profiles_parsed.json (vision-parsed)
  - point scales: official Giro rules (see constants below)
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT  = BASE / "data" / "stages" / "stage_roadbook.json"

# ── Official Giro d'Italia point scales (fixed) ───────────────────────────────
SPRINT_POINTS_INTERMEDIATE = [20, 17, 15, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]  # 15 positions
SPRINT_POINTS_FINISH       = [50, 30, 20, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1, 1]  # flat finish, 15 pos

KOM_POINTS = {
    "HC": [40, 20, 12, 8, 6, 4, 2, 1],
    1:    [25, 16, 10, 7, 5, 3, 2, 1],
    2:    [15, 10,  6, 4, 2, 1],
    3:    [ 8,  5,  3, 1],
    4:    [ 4,  2,  1],
}


def build_roadbook() -> list[dict]:
    profiles = json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())

    roadbook = []
    for p in sorted(profiles, key=lambda x: x["stage"]):
        stage_n   = p["stage"]
        stage_type = p["stage_type"]
        finish    = p["finish_type"]

        # Intermediate sprints
        int_sprints = [
            {"km": sp["km"], "label": sp.get("label", ""), "points": SPRINT_POINTS_INTERMEDIATE}
            for sp in p.get("intermediate_sprints", [])
        ]

        # Finish line sprint: only on sprint-finish stages (not summit/uphill/tt)
        finish_sprint = None
        if finish == "sprint":
            finish_sprint = {"points": SPRINT_POINTS_FINISH}

        # KOM climbs with official point scales by category
        kom_climbs = []
        for k in p.get("kom_climbs", []):
            cat = k.get("category")
            pts = KOM_POINTS.get(cat, KOM_POINTS[4])  # default to Cat 4 if unknown
            kom_climbs.append({
                "km":       k["km"],
                "category": cat,
                "name":     k.get("name", ""),
                "points":   pts,
            })

        entry = {
            "stage":                stage_n,
            "stage_type":           stage_type,
            "finish_type":          finish,
            "intermediate_sprints": int_sprints,
            "kom_climbs":           kom_climbs,
        }
        if finish_sprint:
            entry["finish_sprint"] = finish_sprint
        else:
            entry["finish_sprint"] = None

        roadbook.append(entry)

    return roadbook


def main():
    roadbook = build_roadbook()
    OUT.write_text(json.dumps(roadbook, indent=2, ensure_ascii=False))
    print(f"✓ Wrote {len(roadbook)} stages → {OUT}")
    # Quick summary
    for r in roadbook:
        sp = len(r["intermediate_sprints"])
        km = len(r["kom_climbs"])
        fs = "finish_sprint" if r.get("finish_sprint") else "no_finish_sprint"
        print(f"  S{r['stage']:2d} {r['stage_type']:8s} {r['finish_type']:7s} "
              f"int_sprints={sp} koms={km} {fs}")


if __name__ == "__main__":
    main()
