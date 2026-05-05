#!/usr/bin/env python3
"""
Ingest Copilot-researched rider attributes into the override system.
Matches riders by name to holdet_id from riders_giro2026_v1.json.
Writes results to data/overrides/rider_attribute_overrides.yaml.

Usage:
  python3 scripts/ingest_copilot_attributes.py
  python3 scripts/ingest_copilot_attributes.py --dry-run
"""

import json, yaml, argparse, unicodedata
from pathlib import Path
from datetime import date
from difflib import get_close_matches

BASE = Path(__file__).resolve().parent.parent

ATTRIBUTE_KEYS = [
    "sprint_affinity", "climbing_affinity", "puncheur_affinity",
    "gc_affinity", "breakaway_affinity", "tt_affinity",
]


def normalise(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return name.lower().strip()


def match_riders(copilot_riders: list, holdet_riders: list):
    holdet_by_name = {normalise(r["name"]): r for r in holdet_riders}
    holdet_names   = list(holdet_by_name.keys())

    matched   = []
    unmatched = []

    for cr in copilot_riders:
        norm = normalise(cr["rider_name"])

        # 1. Exact
        if norm in holdet_by_name:
            matched.append((cr, holdet_by_name[norm], "exact"))
            continue

        # 2. Last-name exact (handles first-name order differences)
        cr_parts = norm.split()
        if len(cr_parts) >= 2:
            last = cr_parts[-1]
            candidates = [n for n in holdet_names if n.split()[-1] == last]
            if len(candidates) == 1:
                matched.append((cr, holdet_by_name[candidates[0]], "last_name"))
                continue
            if len(candidates) > 1:
                # Break tie with first-name prefix
                first3 = cr_parts[0][:3]
                candidates2 = [n for n in candidates if n.startswith(first3)]
                if len(candidates2) == 1:
                    matched.append((cr, holdet_by_name[candidates2[0]], "fuzzy"))
                    continue

        # 3. Copilot name is a prefix of Holdet name (e.g. "Enric Mas" → "Enric Mas Nicolau")
        prefix_candidates = [n for n in holdet_names if n.startswith(norm + " ") or n == norm]
        if len(prefix_candidates) == 1:
            matched.append((cr, holdet_by_name[prefix_candidates[0]], "prefix"))
            continue

        # 4. Copilot name words all appear in Holdet name ("Jhonatan Narváez" ⊆ "Jhonatan Manuel Narvaez Prado")
        norm_words = set(norm.split())
        subset_candidates = [
            n for n in holdet_names
            if norm_words.issubset(set(n.split())) and len(norm.split()) >= 2
        ]
        if len(subset_candidates) == 1:
            matched.append((cr, holdet_by_name[subset_candidates[0]], "subset"))
            continue

        # 5. Difflib fallback
        close = get_close_matches(norm, holdet_names, n=1, cutoff=0.75)
        if close:
            matched.append((cr, holdet_by_name[close[0]], "difflib"))
        else:
            unmatched.append(cr)

    return matched, unmatched


def build_overrides(matched: list) -> list:
    today     = date.today().isoformat()
    overrides = []

    for copilot_rider, holdet_rider, match_type in matched:
        holdet_id = int(holdet_rider["holdet_id"])
        name      = holdet_rider["name"]

        for attr in ATTRIBUTE_KEYS:
            if attr not in copilot_rider:
                continue
            overrides.append({
                "holdet_id":              holdet_id,
                "name":                   name,
                "attribute":              attr,
                "value":                  round(float(copilot_rider[attr]), 2),
                "reason": (
                    f"Copilot research. "
                    f"rider_type={copilot_rider.get('rider_type', '?')}, "
                    f"team_role={copilot_rider.get('team_role', '?')}. "
                    f"{copilot_rider.get('notable_results', '')}"
                ),
                "giro_role_2026":         copilot_rider.get("giro_role_2026", ""),
                "rider_type":             copilot_rider.get("rider_type", ""),
                "team_role":              copilot_rider.get("team_role", ""),
                "source":                 "copilot_research",
                "confidence":             copilot_rider.get("confidence", "medium"),
                "match_type":             match_type,
                "stage_first_applicable": 1,
                "date":                   today,
            })

    return overrides


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    copilot_riders = json.loads((BASE / "data/external/riders_copilot.json").read_text())
    holdet_data    = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())
    # Accept both flat list and {"riders": [...]} structure
    if isinstance(holdet_data, dict):
        holdet_data = holdet_data["riders"]
    active_holdet = [r for r in holdet_data if r.get("holdet_id")]

    print(f"Copilot riders:        {len(copilot_riders)}")
    print(f"Active Holdet riders:  {len(active_holdet)}")

    matched, unmatched = match_riders(copilot_riders, active_holdet)

    # Match quality summary
    by_type: dict[str, int] = {}
    for _, _, mt in matched:
        by_type[mt] = by_type.get(mt, 0) + 1

    print(f"\nMatched:   {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")
    for mt, count in sorted(by_type.items()):
        print(f"  {mt}: {count}")

    # Flag fuzzy matches for manual review
    fuzzy = [(cr, hr, mt) for cr, hr, mt in matched if mt in ("fuzzy", "difflib")]
    if fuzzy:
        print(f"\nFuzzy / difflib matches — verify these:")
        for cr, hr, mt in fuzzy:
            print(f"  '{cr['rider_name']}' → '{hr['name']}' [{mt}]")

    if unmatched:
        print(f"\n⚠  Unmatched riders (DNS or name variant):")
        for r in unmatched:
            print(f"  {r['rider_name']} ({r['team']})")

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return

    new_overrides = build_overrides(matched)

    # Load existing overrides, preserve manual entries
    overrides_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
    existing = {"overrides": []}
    if overrides_path.exists():
        existing = yaml.safe_load(overrides_path.read_text()) or {"overrides": []}

    manual_kept = [o for o in existing.get("overrides", [])
                   if o.get("source") == "manual"]

    merged = {"overrides": manual_kept + new_overrides}
    overrides_path.parent.mkdir(exist_ok=True)
    overrides_path.write_text(
        yaml.dump(merged, allow_unicode=True, sort_keys=False, default_flow_style=False)
    )

    print(f"\n✓ {len(new_overrides)} attribute overrides written")
    if manual_kept:
        print(f"  {len(manual_kept)} manual overrides preserved")
    print(f"  File: {overrides_path}")

    if unmatched:
        report_path = BASE / "data/reviews/unmatched_copilot_riders.yaml"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(
            yaml.dump({"unmatched": unmatched}, allow_unicode=True, sort_keys=False)
        )
        print(f"  Unmatched report: {report_path}")

    print("\nNext: python3 scripts/apply_corrections_and_rebuild.py")


if __name__ == "__main__":
    main()
