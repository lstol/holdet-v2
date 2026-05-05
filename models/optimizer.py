#!/usr/bin/env python3
"""
Greedy budget-constrained team optimizer for Giro 2026 Stage 1.

Selects 8 riders maximizing EV across stages 1-3 (lookahead window).
Constraints:
  - Total price ≤ 50,000,000 kr
  - Max 2 riders per real-world team
  - Exclude DNS riders (by holdet_id)
  - Must fill exactly 8 slots (budget-reserve guarantee)

Outputs: decisions/stage1_system_b.yaml
"""

import json, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

BUDGET        = 50_000_000
TEAM_SIZE     = 8
MAX_PER_TEAM  = 2
LOOKAHEAD     = [1, 2, 3]          # stages to include in EV sum
DNS_HOLDET_IDS = {47380, 47350}    # Germani, Conca

# How to weight each stage in the lookahead (equal weighting)
STAGE_WEIGHT  = {1: 1.0, 2: 1.0, 3: 1.0}


def load_riders() -> list[dict]:
    data = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())
    riders = data["riders"]
    active = [
        r for r in riders
        if r.get("status", "active") == "active"
        and r.get("holdet_id")
        and r.get("holdet_id") not in DNS_HOLDET_IDS
        and r.get("price", 0) > 0
    ]
    return active


def load_breakdowns(stage_ns: list[int]) -> dict[int, dict]:
    result = {}
    for n in stage_ns:
        path = BASE / f"models/ev_breakdown_stage{n}.json"
        if path.exists():
            data = json.loads(path.read_text())
            result[n] = data["riders"]
    return result


def compute_multi_stage_ev(rider_id: str, breakdowns: dict[int, dict]) -> float:
    total = 0.0
    for stage_n, riders_map in breakdowns.items():
        w  = STAGE_WEIGHT.get(stage_n, 1.0)
        bd = riders_map.get(rider_id)
        if bd:
            total += w * bd["total"]
    return total


def select_captain(team: list[dict], breakdowns: dict[int, dict]) -> dict:
    """Captain = rider with highest Stage 1 EV."""
    bd1_riders = breakdowns.get(1, {})
    best = max(team, key=lambda r: bd1_riders.get(r["rider_id"], {}).get("total", 0))
    return best


def greedy_select(
    candidates: list[dict],
    breakdowns: dict[int, dict],
    budget: int = BUDGET,
    n: int = TEAM_SIZE,
    max_per_team: int = MAX_PER_TEAM,
) -> list[dict]:
    scored = []
    for r in candidates:
        ev = compute_multi_stage_ev(r["rider_id"], breakdowns)
        scored.append({**r, "_ev": ev})

    # Sort by absolute EV (not EV/price) — fantasy game goal is max team EV, not
    # max return on price. Budget reserve ensures cheapest slots are filled last.
    scored.sort(key=lambda x: x["_ev"], reverse=True)

    team: list[dict]  = []
    spent             = 0
    team_counts: dict[str, int] = {}
    min_price = min(r["price"] for r in scored)

    for r in scored:
        if len(team) >= n:
            break

        slots_left     = n - len(team)
        budget_reserve = min_price * (slots_left - 1)

        if spent + r["price"] + budget_reserve > budget:
            continue
        if team_counts.get(r["team"], 0) >= max_per_team:
            continue

        team.append(r)
        spent += r["price"]
        team_counts[r["team"]] = team_counts.get(r["team"], 0) + 1

    return team


def build_yaml(team: list[dict], breakdowns: dict[int, dict], captain: dict) -> dict:
    bd1 = breakdowns.get(1, {})
    bd2 = breakdowns.get(2, {})
    bd3 = breakdowns.get(3, {})

    total_spent = sum(r["price"] for r in team)
    budget_remaining = BUDGET - total_spent

    riders_out = []
    for r in sorted(team, key=lambda x: -x["_ev"]):
        rid  = r["rider_id"]
        b1   = bd1.get(rid, {})
        b2   = bd2.get(rid, {})
        b3   = bd3.get(rid, {})
        s1_total = b1.get("total", 0)
        s2_total = b2.get("total", 0)
        s3_total = b3.get("total", 0)
        entry = {
            "name":           r["name"],
            "rider_id":       rid,
            "holdet_id":      r.get("holdet_id"),
            "team":           r["team"],
            "price":          r["price"],
            "terrain_type":   r.get("terrain_affinity", {}),
            "is_captain":     (r["rider_id"] == captain["rider_id"]),
            "ev_stage1":      s1_total,
            "ev_stage2":      s2_total,
            "ev_stage3":      s3_total,
            "ev_lookahead":   round(r["_ev"]),
            "ev_breakdown_s1": b1,
        }
        riders_out.append(entry)

    captain_data = next(r for r in riders_out if r["is_captain"])

    return {
        "meta": {
            "description": "Stage 1 System B selection — Phase 3c optimizer",
            "stage": 1,
            "lookahead_stages": LOOKAHEAD,
            "budget": BUDGET,
            "budget_spent": total_spent,
            "budget_remaining": budget_remaining,
        },
        "captain": captain["name"],
        "team": riders_out,
        "total_ev_stage1":    sum(r["ev_stage1"]    for r in riders_out),
        "total_ev_lookahead": sum(r["ev_lookahead"] for r in riders_out),
    }


def main():
    riders    = load_riders()
    breakdowns = load_breakdowns(LOOKAHEAD)

    team    = greedy_select(riders, breakdowns)
    captain = select_captain(team, breakdowns)

    if len(team) < TEAM_SIZE:
        print(f"WARNING: Only {len(team)} riders selected (budget too tight?)")
    else:
        print(f"✓ Selected {len(team)} riders")

    out_data = build_yaml(team, breakdowns, captain)

    out_path = BASE / "decisions" / "stage1_system_b.yaml"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(yaml.dump(out_data, allow_unicode=True, sort_keys=False, default_flow_style=False))
    print(f"✓ Wrote → {out_path}")

    print(f"\nTeam (budget used: {out_data['meta']['budget_spent']:,} / {BUDGET:,} kr):")
    print(f"  Captain: {out_data['captain']}")
    for r in out_data["team"]:
        cap_flag = " ★" if r["is_captain"] else ""
        print(f"  {r['name']:30s}  {r['price']:>10,} kr  S1={r['ev_stage1']:>8,}  3-stg={r['ev_lookahead']:>8,}{cap_flag}")
    print(f"\nTeam total EV (S1):        {out_data['total_ev_stage1']:>10,} kr")
    print(f"Team total EV (3-stage):   {out_data['total_ev_lookahead']:>10,} kr")


if __name__ == "__main__":
    main()
