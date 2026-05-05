#!/usr/bin/env python3
"""
Update stage_roadbook.json with official 2026 Giro d'Italia Holdet point scales.

Changes:
- Adds `stage_group` field (flat / hilly / mountain) to each stage
- Adds `finish_points` list (Holdet scoring, position 1 → last)
- Replaces `intermediate_sprints` list + `finish_sprint` with single `intermediate_sprint`
  (one intermediate sprint per non-TT stage, points [12, 8, 5, 3, 1], top 5 only)
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

STAGE_GROUPS = {
    "flat": {
        "stages": [1, 3, 4, 6, 12, 15, 18, 21],
        "finish_points": [50, 35, 25, 18, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1],
    },
    "hilly": {
        "stages": [2, 5, 8, 9, 11, 13, 17],
        "finish_points": [25, 18, 12, 8, 6, 5, 4, 3, 2, 1],
    },
    "mountain": {
        "stages": [7, 10, 14, 16, 19, 20],
        "finish_points": [15, 12, 9, 7, 6, 5, 4, 3, 2, 1],
    },
    "mountain_itt": {
        "stages": [],   # placeholder — assign manually if any ITT is in a mountain context
        "finish_points": [15, 12, 9, 7, 6, 5, 4, 3, 2, 1],
    },
}

# Stage 8 is a TTT; Stage 14 is ITT — override stage_group after the loop
ITT_STAGES = {8, 14}   # no intermediate sprint for ITTs

STAGE_TO_GROUP: dict[int, str] = {
    n: group
    for group, data in STAGE_GROUPS.items()
    for n in data["stages"]
}

# One intermediate sprint per non-TT stage, top-5 points
SPRINT_POINTS = [12, 8, 5, 3, 1]


def main():
    roadbook_path = BASE / "data/stages/stage_roadbook.json"
    roadbook = json.loads(roadbook_path.read_text())

    for entry in roadbook:
        n = entry["stage"]
        group = STAGE_TO_GROUP.get(n)

        if group is None:
            print(f"  ⚠️  Stage {n} not assigned to a group — defaulting to 'hilly'")
            group = "hilly"

        entry["stage_group"] = group
        entry["finish_points"] = STAGE_GROUPS[group]["finish_points"]

        # Single intermediate sprint (no sprint in ITTs)
        existing_sprints = entry.get("intermediate_sprints", [])
        if n in ITT_STAGES:
            entry.pop("intermediate_sprint", None)
        elif existing_sprints:
            entry["intermediate_sprint"] = {
                "km": existing_sprints[0].get("km"),
                "points": SPRINT_POINTS,
            }
        else:
            entry["intermediate_sprint"] = {
                "km": None,
                "points": SPRINT_POINTS,
                "note": "km location not parsed from image",
            }

        # Remove old fields
        entry.pop("intermediate_sprints", None)
        entry.pop("finish_sprint", None)

    roadbook_path.write_text(json.dumps(roadbook, indent=2, ensure_ascii=False))
    print(f"✓ Wrote {len(roadbook)} stages → {roadbook_path}")

    # Validation
    s1 = next(e for e in roadbook if e["stage"] == 1)
    assert s1["stage_group"] == "flat", f"Stage 1 should be flat, got {s1['stage_group']}"
    max_pts_s1 = s1["finish_points"][0] + SPRINT_POINTS[0]
    assert max_pts_s1 == 62, f"Stage 1 max pts should be 62, got {max_pts_s1}"
    print(f"  ✓ Stage 1: group=flat, max pts={max_pts_s1} (expected 62)")

    s2 = next(e for e in roadbook if e["stage"] == 2)
    assert s2["stage_group"] == "hilly", f"Stage 2 should be hilly, got {s2['stage_group']}"
    max_pts_s2 = s2["finish_points"][0] + SPRINT_POINTS[0]
    print(f"  ✓ Stage 2: group=hilly, max pts={max_pts_s2} (expected 37)")

    s7 = next(e for e in roadbook if e["stage"] == 7)
    assert s7["stage_group"] == "mountain"
    print(f"  ✓ Stage 7: group=mountain, finish top={s7['finish_points'][0]} (expected 15)")

    for e in roadbook:
        assert "intermediate_sprints" not in e, f"Stage {e['stage']} still has old list field"
    print("  ✓ All stages: old 'intermediate_sprints' list removed")

    non_itt_stages = [e for e in roadbook if e["stage"] not in ITT_STAGES]
    for e in non_itt_stages:
        assert "intermediate_sprint" in e, f"Stage {e['stage']} missing intermediate_sprint"
    print(f"  ✓ {len(non_itt_stages)} non-ITT stages have single intermediate_sprint field")


if __name__ == "__main__":
    main()
