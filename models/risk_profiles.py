#!/usr/bin/env python3
"""
Risk profiles for Giro 2026 Stage 1 team selection.

Three profiles using (EV, variance) from stage 1 breakdown:
  Conservative  — maximize EV/σ (Sharpe-like; reward per unit risk)
  Balanced      — maximize EV - 0.5 × σ (mild risk penalty)
  All-In        — maximize EV (pure upside, ignores variance)

Outputs printed to stdout + saved to decisions/stage1_risk_profiles.yaml
"""

import json, yaml, math
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

BUDGET        = 50_000_000
TEAM_SIZE     = 8
MAX_PER_TEAM  = 2
DNS_HOLDET_IDS = {47380, 47350}
LOOKAHEAD     = [1, 2, 3]


def load_riders() -> list[dict]:
    data = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())
    return [
        r for r in data["riders"]
        if r.get("status", "active") == "active"
        and r.get("holdet_id")
        and r.get("holdet_id") not in DNS_HOLDET_IDS
        and r.get("price", 0) > 0
    ]


def load_breakdowns(stage_ns: list[int]) -> dict[int, dict]:
    result = {}
    for n in stage_ns:
        path = BASE / f"models/ev_breakdown_stage{n}.json"
        if path.exists():
            result[n] = json.loads(path.read_text())["riders"]
    return result


def compute_multi_stage_ev(rider_id: str, breakdowns: dict[int, dict]) -> float:
    return sum(riders.get(rider_id, {}).get("total", 0) for riders in breakdowns.values())


def compute_s1_stddev(rider_id: str, breakdowns: dict[int, dict]) -> float:
    bd = breakdowns.get(1, {}).get(rider_id, {})
    var = bd.get("variance", 0)
    return math.sqrt(var) if var > 0 else 1.0


def greedy_select(
    candidates: list[dict],
    score_fn,
    budget: int = BUDGET,
    n: int = TEAM_SIZE,
    max_per_team: int = MAX_PER_TEAM,
) -> list[dict]:
    scored = sorted(candidates, key=score_fn, reverse=True)
    team: list[dict]      = []
    spent                 = 0
    team_counts: dict[str, int] = {}
    min_price             = min(r["price"] for r in scored)

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


def build_profile_output(name: str, team: list[dict], breakdowns: dict[int, dict]) -> dict:
    bd1 = breakdowns.get(1, {})
    riders_out = []
    for r in sorted(team, key=lambda x: -bd1.get(x["rider_id"], {}).get("total", 0)):
        rid = r["rider_id"]
        b1  = bd1.get(rid, {})
        ev  = sum(riders.get(rid, {}).get("total", 0) for riders in breakdowns.values())
        sd  = math.sqrt(b1.get("variance", 0)) if b1.get("variance", 0) > 0 else 0
        riders_out.append({
            "name":       r["name"],
            "rider_id":   rid,
            "holdet_id":  r.get("holdet_id"),
            "team":       r["team"],
            "price":      r["price"],
            "ev_stage1":  b1.get("total", 0),
            "ev_lookahead": round(ev),
            "stddev_s1":  round(sd),
        })
    return {
        "profile":            name,
        "budget_spent":       sum(r["price"] for r in team),
        "team_ev_stage1":     sum(r["ev_stage1"] for r in riders_out),
        "team_ev_lookahead":  sum(r["ev_lookahead"] for r in riders_out),
        "riders":             riders_out,
    }


def main():
    riders     = load_riders()
    breakdowns = load_breakdowns(LOOKAHEAD)

    for r in riders:
        r["_ev"] = compute_multi_stage_ev(r["rider_id"], breakdowns)
        r["_sd"] = compute_s1_stddev(r["rider_id"], breakdowns)

    profiles = {}

    # Conservative: maximize EV/σ (Sharpe-like)
    # σ floored at 50,000 kr so riders with near-zero EV don't dominate by having 0 variance
    conservative_team = greedy_select(
        riders,
        score_fn=lambda r: r["_ev"] / max(r["_sd"], 50_000),
    )
    profiles["conservative"] = build_profile_output("Conservative", conservative_team, breakdowns)

    # Balanced: maximize EV − 0.5σ
    balanced_team = greedy_select(
        riders,
        score_fn=lambda r: r["_ev"] - 0.5 * r["_sd"],
    )
    profiles["balanced"] = build_profile_output("Balanced", balanced_team, breakdowns)

    # All-In: maximize EV (identical to optimizer.py)
    allin_team = greedy_select(
        riders,
        score_fn=lambda r: r["_ev"],
    )
    profiles["all_in"] = build_profile_output("All-In", allin_team, breakdowns)

    out_path = BASE / "decisions" / "stage1_risk_profiles.yaml"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(yaml.dump(profiles, allow_unicode=True, sort_keys=False, default_flow_style=False))
    print(f"✓ Wrote → {out_path}")

    for key, p in profiles.items():
        print(f"\n── {p['profile']} (budget {p['budget_spent']:,}) ──")
        print(f"   EV Stage 1: {p['team_ev_stage1']:,}  |  3-stage: {p['team_ev_lookahead']:,}")
        for r in p["riders"]:
            print(f"   {r['name']:30s} S1={r['ev_stage1']:>7,}  σ={r['stddev_s1']:>8,}  {r['price']:>10,} kr")


if __name__ == "__main__":
    main()
