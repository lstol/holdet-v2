#!/usr/bin/env python3
"""
Apply attribute overrides from data/overrides/rider_attribute_overrides.yaml
and rebuild all downstream artefacts:

  1. Re-compute EV breakdowns for all 21 stages (with overrides applied)
  2. Re-run optimizer → decisions/stage1_system_b.yaml
  3. Re-run risk profiles → decisions/stage1_risk_profiles.yaml
  4. Rebuild dashboard → interface/early/stage1_dashboard.html

Usage:
  python3 scripts/apply_corrections_and_rebuild.py
  python3 scripts/apply_corrections_and_rebuild.py --skip-dashboard
"""

import argparse, json, subprocess, sys, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from models.ev_breakdown import (
    build_all_breakdowns, load_rider_attributes,
)


def load_overrides() -> list[dict]:
    path = BASE / "data/overrides/rider_attribute_overrides.yaml"
    if not path.exists():
        print("No overrides file found — nothing to apply.")
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    return raw.get("overrides", [])


def count_researched(overrides: list[dict]) -> int:
    return len({o["holdet_id"] for o in overrides
                if o.get("source") in ("web_search", "copilot_research")})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dashboard", action="store_true",
                        help="Skip dashboard rebuild (faster for iteration)")
    parser.add_argument("--stages", nargs="+", type=int,
                        help="Rebuild only these stage numbers (default: all 1-21)")
    args = parser.parse_args()

    overrides = load_overrides()
    n_researched = count_researched(overrides)
    print(f"Loaded {len(overrides)} overrides covering {n_researched} researched riders.")

    # ── Load data ────────────────────────────────────────────────────────────────
    riders_raw  = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
    stages_data = json.loads((BASE / "data/stages/stages_giro2026.json").read_text())["stages"]
    roadbooks   = json.loads((BASE / "data/stages/stage_roadbook.json").read_text())

    active_base = [r for r in riders_raw
                   if r.get("status") == "active" and r.get("holdet_id")]

    # Apply overrides per stage (stage_first_applicable means some overrides
    # only kick in from a given stage onwards — e.g. after an injury/update).
    # For efficiency we compute once per unique override set; in practice nearly
    # all overrides have stage_first_applicable=1 so there's only one unique set.
    stages_to_build = args.stages or list(range(1, 22))

    print(f"\nStep 1: Rebuilding EV breakdowns for stages {stages_to_build}...")

    roadbook_map = {r["stage"]: r for r in roadbooks}
    stages_map   = {s["stage_number"]: s for s in stages_data}

    out_dir = BASE / "models"
    out_dir.mkdir(exist_ok=True)

    for stage_n in stages_to_build:
        rb = roadbook_map.get(stage_n, {})
        ft = rb.get("finish_type", "sprint")
        st = rb.get("stage_type",  "flat")

        # Apply overrides for this stage
        active = [load_rider_attributes(r, stage_n, overrides) for r in active_base]

        from models.ev_breakdown import make_win_probs, rider_stage_ev_breakdown, rider_stage_variance

        win_probs = make_win_probs(active, st, ft)

        stage_result: dict = {}
        for r in active:
            rid = r["rider_id"]
            wp  = win_probs.get(rid, 0)
            bd  = rider_stage_ev_breakdown(
                rider=r, stage_meta=stages_map.get(stage_n, {}),
                roadbook=rb, win_prob=wp, stage_n=stage_n,
            )
            bd["variance"] = round(rider_stage_variance(wp, ft, bd["jersey"], bd["sprint_kom"]))
            stage_result[rid] = bd

        out_path = out_dir / f"ev_breakdown_stage{stage_n}.json"
        out_path.write_text(json.dumps(
            {"stage": stage_n, "finish_type": ft, "stage_type": st, "riders": stage_result},
            indent=2, ensure_ascii=False
        ))
        print(f"  S{stage_n:2d} ✓  ({len(active)} riders, {len(overrides)} overrides applied)")

    # ── Step 2: Optimizer ────────────────────────────────────────────────────────
    print("\nStep 2: Running optimizer...")
    result = subprocess.run(
        [sys.executable, str(BASE / "models/optimizer.py")],
        capture_output=True, text=True, cwd=BASE,
    )
    if result.returncode == 0:
        print("  ✓ optimizer.py")
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    else:
        print(f"  ✗ optimizer.py failed:\n{result.stderr}")

    # ── Step 3: Risk profiles ─────────────────────────────────────────────────────
    print("\nStep 3: Running risk profiles...")
    result = subprocess.run(
        [sys.executable, str(BASE / "models/risk_profiles.py")],
        capture_output=True, text=True, cwd=BASE,
    )
    if result.returncode == 0:
        print("  ✓ risk_profiles.py")
    else:
        print(f"  ✗ risk_profiles.py failed:\n{result.stderr}")

    # ── Step 4: Dashboard ─────────────────────────────────────────────────────────
    if not args.skip_dashboard:
        print("\nStep 4: Rebuilding dashboard...")
        result = subprocess.run(
            [sys.executable, str(BASE / "interface/early/build_stage1.py")],
            capture_output=True, text=True, cwd=BASE,
        )
        if result.returncode == 0:
            print("  ✓ build_stage1.py")
            for line in result.stdout.strip().splitlines():
                print(f"  {line}")
        else:
            print(f"  ✗ build_stage1.py failed:\n{result.stderr}")
    else:
        print("\nStep 4: Skipped (--skip-dashboard)")

    print(f"\n✓ Done. {n_researched} researched riders, {len(overrides)} override entries applied.")


if __name__ == "__main__":
    main()
