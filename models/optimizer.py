#!/usr/bin/env python3
"""
Multi-stage optimizer for Giro 2026 — Phase 3h (Fix D).

True multi-stage optimization: per-stage optimal team selection with
transfer cost vs EV gain decision for each stage transition.

Fix D: team bonus recomputed per proposed team during swap evaluation
       (not cached standalone EV).

Outputs: decisions/stage1_system_b.yaml
"""

import json, yaml, sys
from pathlib import Path

# allow importing ev_breakdown from models/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ev_breakdown import compute_team_bonus_ev, STAGE_TYPE_DEFAULTS

BASE = Path(__file__).resolve().parent.parent

TRANSFER_FEE_RATE = 0.01   # 1% of buyer price (buy fee only)
MAX_PER_TEAM      = 2
TEAM_SIZE         = 8
BUDGET            = 50_000_000
BANK              = 4_500_000
LOOKAHEAD         = [1, 2, 3]
DNS_HOLDET_IDS    = {47380, 47350}

DEPTH_BONUS    = {0: 0, 1: 4_000, 2: 8_000, 3: 15_000,
                  4: 35_000, 5: 65_000, 6: 120_000, 7: 220_000, 8: 400_000}
AVG_TOP15_PAYOFF = 71_000


# ── Data loading ──────────────────────────────────────────────────────────────

def load_riders() -> list[dict]:
    data = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())
    return [
        r for r in data["riders"]
        if r.get("status", "active") == "active"
        and r.get("holdet_id")
        and r.get("holdet_id") not in DNS_HOLDET_IDS
        and r.get("price", 0) > 0
    ]


def load_ev_by_stage(stage_ns: list[int]) -> dict:
    """Returns {rider_id: {stage_n: breakdown_dict}}"""
    result: dict = {}
    for n in stage_ns:
        path = BASE / f"models/ev_breakdown_stage{n}.json"
        if not path.exists():
            continue
        for rider_id, bd in json.loads(path.read_text())["riders"].items():
            result.setdefault(rider_id, {})[n] = bd
    return result


def load_stage_roadbook() -> dict:
    """Returns {stage_n: roadbook_entry} for looking up stage_group."""
    data = json.loads((BASE / "data/stages/stage_roadbook.json").read_text())
    return {e["stage"]: e for e in data}


# ── Core computation ──────────────────────────────────────────────────────────

def expected_depth_bonus(team: list[dict], ev_by_stage: dict, stage_n: int) -> int:
    """E[StageDepthCount bonus] via independence approximation over P(top-15)."""
    p_top15 = []
    for r in team:
        sf_ev = ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("stage_finish", 0)
        p_top15.append(min(max(sf_ev / AVG_TOP15_PAYOFF, 0), 0.95))

    dist = {0: 1.0}
    for p in p_top15:
        new_dist: dict = {}
        for k, prob in dist.items():
            new_dist[k]     = new_dist.get(k, 0)     + prob * (1 - p)
            new_dist[k + 1] = new_dist.get(k + 1, 0) + prob * p
        dist = new_dist

    return int(sum(DEPTH_BONUS.get(k, 0) * prob for k, prob in dist.items()))


def compute_team_ev(team: list[dict], ev_by_stage: dict, stage_n: int) -> int:
    base = sum(
        ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("total", 0)
        for r in team
    )
    return base + expected_depth_bonus(team, ev_by_stage, stage_n)


def select_captain(team: list[dict], ev_by_stage: dict, stage_n: int) -> dict:
    return max(
        team,
        key=lambda r: max(
            ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("total", 0), 0
        )
    )


# ── Team selection ────────────────────────────────────────────────────────────

def select_optimal_team(
    riders: list[dict],
    ev_by_stage: dict,
    stage_n: int,
    budget: int,
    exclude_ids: set = None,
) -> list[dict]:
    """Greedy selection maximising EV for stage_n within budget and team constraints."""
    exclude_ids = exclude_ids or set()
    eligible = [
        r for r in riders
        if not r.get("isOut", False) and r["rider_id"] not in exclude_ids
    ]
    eligible.sort(
        key=lambda r: ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("total", 0),
        reverse=True,
    )

    team: list[dict] = []
    spent = 0
    team_counts: dict = {}
    min_price = min((r["price"] for r in eligible), default=1)

    for r in eligible:
        if len(team) >= TEAM_SIZE:
            break
        real_team = r.get("team", "")
        if team_counts.get(real_team, 0) >= MAX_PER_TEAM:
            continue
        slots_left = TEAM_SIZE - len(team)
        if spent + r["price"] + min_price * (slots_left - 1) > budget:
            continue
        team.append(r)
        spent += r["price"]
        team_counts[real_team] = team_counts.get(real_team, 0) + 1

    return team


def rider_ev_in_team(
    rider: dict,
    proposed_team: list[dict],
    ev_by_stage: dict,
    stage_n: int,
    all_riders: list[dict],
    scenario_weights: dict,
) -> int:
    """EV for rider in proposed_team: cached base (stage_finish+sprint_kom) + fresh team bonus."""
    base_ev = ev_by_stage.get(rider["rider_id"], {}).get(stage_n, {}).get("total", 0)
    team_bonus = compute_team_bonus_ev(rider, proposed_team, all_riders, scenario_weights)
    return base_ev + team_bonus


def optimize_transfers(
    current_team: list[dict],
    riders: list[dict],
    ev_by_stage: dict,
    stage_n: int,
    budget: int,
    bank: int,
    all_riders: list[dict],
    scenario_weights: dict,
) -> tuple:
    """
    For each rider in current_team, find the best swap.
    Execute greedily from highest net_gain (ev_gain − fee), stop at net_gain ≤ 0.
    Fix D: in_ev computed with team bonus for proposed team, not cached standalone EV.
    Returns: (new_team, transfers_in, transfers_out, total_fee)
    """
    team = list(current_team)
    current_ids = {r["rider_id"] for r in team}
    transfers_in:  list = []
    transfers_out: list = []
    total_fee = 0

    swap_candidates = []
    for out_rider in team:
        out_ev = ev_by_stage.get(out_rider["rider_id"], {}).get(stage_n, {}).get("total", 0)
        for in_rider in riders:
            if in_rider["rider_id"] in current_ids or in_rider.get("isOut", False):
                continue
            fee = int(in_rider["price"] * TRANSFER_FEE_RATE)
            if bank - total_fee < fee:
                continue

            temp = [r for r in team if r["rider_id"] != out_rider["rider_id"]] + [in_rider]
            counts: dict = {}
            for r in temp:
                counts[r.get("team", "")] = counts.get(r.get("team", ""), 0) + 1
            if counts.get(in_rider.get("team", ""), 0) > MAX_PER_TEAM:
                continue
            if sum(r["price"] for r in temp) > budget:
                continue

            in_ev = rider_ev_in_team(in_rider, temp, ev_by_stage, stage_n,
                                      all_riders, scenario_weights)
            swap_candidates.append({
                "out": out_rider, "in": in_rider,
                "net_gain": in_ev - out_ev - fee,
                "fee": fee,
                "ev_gain": in_ev - out_ev,
            })

    swap_candidates.sort(key=lambda s: s["net_gain"], reverse=True)
    swapped_out: set = set()
    swapped_in:  set = set()

    for swap in swap_candidates:
        if swap["net_gain"] <= 0:
            break
        out_id = swap["out"]["rider_id"]
        in_id  = swap["in"]["rider_id"]
        if out_id in swapped_out or in_id in swapped_in:
            continue
        team = [r for r in team if r["rider_id"] != out_id] + [swap["in"]]
        transfers_out.append(swap["out"])
        transfers_in.append(swap["in"])
        total_fee += swap["fee"]
        swapped_out.add(out_id)
        swapped_in.add(in_id)

    return team, transfers_in, transfers_out, total_fee


# ── Multi-stage orchestration ─────────────────────────────────────────────────

def optimize_multistage(
    stage_numbers: list[int],
    riders: list[dict],
    ev_by_stage: dict,
    roadbook: dict,
    budget: int = BUDGET,
    bank: int = BANK,
) -> dict:
    """
    True multi-stage optimizer.
    For each stage, finds the optimal team given transfer costs from prior stage.

    Returns:
      {
        "stage_plans": [
          {
            "stage": N,
            "team": [...],
            "captain": {...},
            "transfers_in": [...],
            "transfers_out": [...],
            "transfer_fee_total": int,
            "stage_ev_gross": int,
            "stage_ev_net": int,
            "depth_bonus": int,
            "hold_vs_transfer": "HOLD"|"TRANSFER",
            "hold_rationale": str,
          }
        ],
        "total_ev_gross": int,
        "total_ev_net": int,
        "total_transfer_cost": int,
      }
    """
    stage_plans = []
    current_team = None
    current_budget = budget
    current_bank = bank

    for i, stage_n in enumerate(stage_numbers):
        stage_group = roadbook.get(stage_n, {}).get("stage_group", "hilly")
        scenario_weights = STAGE_TYPE_DEFAULTS.get(stage_group, STAGE_TYPE_DEFAULTS["hilly"])

        if i == 0:
            team = select_optimal_team(riders, ev_by_stage, stage_n, current_budget)
            transfers_in, transfers_out, fee = team, [], 0
        else:
            team, transfers_in, transfers_out, fee = optimize_transfers(
                current_team, riders, ev_by_stage, stage_n, current_budget, current_bank,
                riders, scenario_weights,
            )

        stage_ev     = compute_team_ev(team, ev_by_stage, stage_n)
        depth_bonus  = expected_depth_bonus(team, ev_by_stage, stage_n)
        captain      = select_captain(team, ev_by_stage, stage_n)
        hold_rationale = (
            "" if transfers_in
            else "Transfer cost exceeds EV gain for all candidate swaps"
        )

        stage_plans.append({
            "stage": stage_n,
            "team": team,
            "captain": captain,
            "transfers_in": transfers_in,
            "transfers_out": transfers_out,
            "transfer_fee_total": fee,
            "stage_ev_gross": stage_ev,
            "stage_ev_net": stage_ev - fee,
            "depth_bonus": depth_bonus,
            "hold_vs_transfer": "TRANSFER" if transfers_in else "HOLD",
            "hold_rationale": hold_rationale,
        })

        current_team   = team
        current_budget = sum(r["price"] for r in team)
        current_bank   = current_bank - fee

    return {
        "stage_plans":        stage_plans,
        "total_ev_gross":     sum(p["stage_ev_gross"]       for p in stage_plans),
        "total_ev_net":       sum(p["stage_ev_net"]         for p in stage_plans),
        "total_transfer_cost":sum(p["transfer_fee_total"]   for p in stage_plans),
    }


# ── YAML output ───────────────────────────────────────────────────────────────

def build_yaml(result: dict, ev_by_stage: dict) -> dict:
    plans    = result["stage_plans"]
    stage_ns = [p["stage"] for p in plans]
    plan1    = plans[0]
    team     = plan1["team"]
    captain  = plan1["captain"]

    riders_out = []
    for r in sorted(team,
                    key=lambda x: -ev_by_stage.get(x["rider_id"], {})
                                              .get(stage_ns[0], {}).get("total", 0)):
        rid = r["rider_id"]
        entry: dict = {
            "name":      r["name"],
            "rider_id":  rid,
            "holdet_id": r.get("holdet_id"),
            "team":      r["team"],
            "price":     r["price"],
            "captain":   rid == captain["rider_id"],
        }
        for n in stage_ns:
            entry[f"stage_{n}_ev"] = ev_by_stage.get(rid, {}).get(n, {}).get("total", 0)
        entry[f"{len(stage_ns)}stage_ev"] = sum(
            ev_by_stage.get(rid, {}).get(n, {}).get("total", 0) for n in stage_ns
        )
        riders_out.append(entry)

    team_ev_summary: dict = {}
    for p in plans:
        team_ev_summary[f"stage_{p['stage']}_gross"] = p["stage_ev_gross"]
    team_ev_summary.update({
        "total_gross":          result["total_ev_gross"],
        "total_transfer_cost":  result["total_transfer_cost"],
        "total_net":            result["total_ev_net"],
        f"depth_bonus_stage_{stage_ns[0]}": plan1["depth_bonus"],
    })

    transfer_plan: dict = {}
    for p in plans[1:]:
        n = p["stage"]
        transfer_plan[f"stage_{n}"] = {
            "decision":       p["hold_vs_transfer"],
            "hold_rationale": p["hold_rationale"],
            "transfers_in":   [{"name": r["name"], "rider_id": r["rider_id"]}
                                for r in p["transfers_in"]],
            "transfers_out":  [{"name": r["name"], "rider_id": r["rider_id"]}
                                for r in p["transfers_out"]],
            "transfer_fee":   p["transfer_fee_total"],
            "ev_gain_gross":  p["stage_ev_gross"],
            "ev_gain_net":    p["stage_ev_net"],
        }

    return {
        "meta": {
            "description":    "Phase 3f multi-stage optimizer — true per-stage optimization",
            "stage":          stage_ns[0],
            "lookahead_stages": stage_ns,
            "budget":         BUDGET,
            "budget_spent":   sum(r["price"] for r in team),
        },
        "captain":          captain["name"],
        "captain_rationale": f"Highest E[max(ΔV,0)] on stage {stage_ns[0]}",
        "team":             riders_out,
        "transfer_plan":    transfer_plan,
        "team_ev_summary":  team_ev_summary,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    riders      = load_riders()
    ev_by_stage = load_ev_by_stage(LOOKAHEAD)
    roadbook    = load_stage_roadbook()
    result      = optimize_multistage(LOOKAHEAD, riders, ev_by_stage, roadbook)
    out_data    = build_yaml(result, ev_by_stage)

    out_path = BASE / "decisions" / "stage1_system_b.yaml"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(yaml.dump(out_data, allow_unicode=True, sort_keys=False,
                                  default_flow_style=False))
    print(f"✓ Wrote → {out_path}")

    plan1  = result["stage_plans"][0]
    team   = plan1["team"]
    spent  = sum(r["price"] for r in team)
    print(f"\nTeam (budget: {spent:,} / {BUDGET:,} kr):")
    print(f"  Captain: {plan1['captain']['name']}")
    for r in sorted(team,
                    key=lambda x: -ev_by_stage.get(x["rider_id"], {})
                                              .get(LOOKAHEAD[0], {}).get("total", 0)):
        cap = " ★" if r["rider_id"] == plan1["captain"]["rider_id"] else ""
        ev1 = ev_by_stage.get(r["rider_id"], {}).get(1, {}).get("total", 0)
        ev3 = sum(ev_by_stage.get(r["rider_id"], {}).get(n, {}).get("total", 0)
                  for n in LOOKAHEAD)
        print(f"  {r['name']:35s}  S1={ev1:>8,}  3-stg={ev3:>8,}{cap}")

    print(f"\nTotal EV gross:  {result['total_ev_gross']:,} kr")
    print(f"Total EV net:    {result['total_ev_net']:,} kr")
    print(f"Transfer cost:   {result['total_transfer_cost']:,} kr")
    print(f"Depth bonus S1:  {plan1['depth_bonus']:,} kr")

    for p in result["stage_plans"][1:]:
        n = p["stage"]
        if p["hold_vs_transfer"] == "HOLD":
            print(f"\nStage {n}: HOLD — {p['hold_rationale']}")
        else:
            ins  = ", ".join(r["name"] for r in p["transfers_in"])
            outs = ", ".join(r["name"] for r in p["transfers_out"])
            print(f"\nStage {n}: TRANSFER | In: {ins} | Out: {outs} | Fee: {p['transfer_fee_total']:,} kr")


if __name__ == "__main__":
    main()
