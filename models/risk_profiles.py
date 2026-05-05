#!/usr/bin/env python3
"""
Stage-type-conditional risk profiles for Giro 2026 — Phase 3f.

Three profiles with rider archetype classification:
  Conservative — EV/σ maximisation; excludes breakaway artists entirely
  Balanced     — EV maximisation across window (same as optimizer output)
  All-In       — Maximum upside; locks breakaway artists on hilly stages

Archetypes are derived from terrain_affinity (post-override), not synthetic
classification. This makes them responsive to manual + expert intel overrides.

Outputs: decisions/stage1_risk_profiles.yaml
"""

import json, math, yaml
from pathlib import Path

BASE           = Path(__file__).resolve().parent.parent
BUDGET         = 50_000_000
TEAM_SIZE      = 8
MAX_PER_TEAM   = 2
DNS_HOLDET_IDS = {47380, 47350}
LOOKAHEAD      = [1, 2, 3]


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


def load_overrides() -> list[dict]:
    path = BASE / "data/overrides/rider_attribute_overrides.yaml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    return raw.get("overrides", [])


def load_stage_profiles() -> dict:
    """Returns {stage_n: stage_type_str}"""
    profiles = json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())
    return {p["stage"]: p["stage_type"] for p in profiles}


def apply_overrides(rider: dict, overrides: list[dict]) -> dict:
    """Apply rider_attribute_overrides to terrain_affinity (Stage 1 only for profiling)."""
    import copy
    ATTR_MAP  = {"sprint_affinity": "sprint", "climbing_affinity": "climbing",
                 "puncheur_affinity": "mixed", "gc_affinity": "gc",
                 "breakaway_affinity": "breakaway", "tt_affinity": "time_trial"}
    PRIORITY  = {"manual": 3, "expert_intel": 2, "copilot_research": 1, "web_search": 1}

    rid = rider.get("holdet_id")
    ovs = [o for o in overrides
           if o.get("holdet_id") == rid
           and o.get("stage_first_applicable", 1) <= 1
           and o.get("stage_last_applicable", 99) >= 1]
    if not ovs:
        return rider

    r  = copy.copy(rider)
    ta = dict(r.get("terrain_affinity", {}))
    for ov in sorted(ovs, key=lambda o: PRIORITY.get(o.get("source", ""), 0)):
        mapped = ATTR_MAP.get(ov["attribute"])
        if mapped:
            if ov.get("mode") == "adjust":
                adj = float(ov.get("adjustment", ov.get("value", 0.0)))
                ta[mapped] = round(min(1.0, max(0.0, ta.get(mapped, 0.5) + adj)), 3)
            else:
                ta[mapped] = round(min(1.0, max(0.0, float(ov["value"]))), 3)
    r["terrain_affinity"] = ta
    return r


# ── Archetype classification ──────────────────────────────────────────────────

def get_rider_archetype(rider: dict) -> str:
    """
    Classify rider based on terrain_affinity (post-override).
    Order matters — more specific before more general.
    """
    ta = rider.get("terrain_affinity", {})
    s  = ta.get("sprint",     0)
    c  = ta.get("climbing",   0)
    p  = ta.get("mixed",      0)   # puncheur
    g  = ta.get("gc",         0)
    b  = ta.get("breakaway",  0)
    t  = ta.get("time_trial", 0)

    if g >= 0.65 and (c >= 0.60 or t >= 0.55):
        return "gc_leader"
    if b >= 0.65 and s < 0.55 and c < 0.55:
        return "breakaway_artist"
    if s >= 0.65:
        return "sprinter"
    if c >= 0.65:
        return "climber"
    if p >= 0.55:
        return "puncheur"
    if t >= 0.65:
        return "tt_specialist"
    return "all_rounder"


def get_stage_type(stage_n: int, stage_types: dict) -> str:
    return stage_types.get(stage_n, "flat")


# ── Shared team builder ───────────────────────────────────────────────────────

def greedy_select(
    candidates: list[dict],
    ev_by_stage: dict,
    stage_ns: list[int],
    budget: int = BUDGET,
    max_size: int = TEAM_SIZE,
    exclude_ids: set = None,
) -> list[dict]:
    """Greedy budget + team-constraint selection from a pre-sorted candidate list."""
    exclude_ids = exclude_ids or set()
    eligible = [r for r in candidates if r["rider_id"] not in exclude_ids]
    team: list[dict] = []
    spent = 0
    team_counts: dict = {}
    min_price = min((r["price"] for r in eligible), default=1)

    for r in eligible:
        if len(team) >= max_size:
            break
        real_team = r.get("team", "")
        if team_counts.get(real_team, 0) >= MAX_PER_TEAM:
            continue
        slots_left = max_size - len(team)
        if spent + r["price"] + min_price * (slots_left - 1) > budget:
            continue
        team.append(r)
        spent += r["price"]
        team_counts[real_team] = team_counts.get(real_team, 0) + 1

    return team


def total_ev(rider: dict, ev_by_stage: dict, stage_ns: list[int]) -> float:
    return sum(ev_by_stage.get(rider["rider_id"], {}).get(n, {}).get("total", 0)
               for n in stage_ns)


def total_variance(rider: dict, ev_by_stage: dict, stage_ns: list[int]) -> float:
    return sum(ev_by_stage.get(rider["rider_id"], {}).get(n, {}).get("variance", 0)
               for n in stage_ns)


def ev_per_sigma(rider: dict, ev_by_stage: dict, stage_ns: list[int]) -> float:
    ev  = total_ev(rider, ev_by_stage, stage_ns)
    var = max(total_variance(rider, ev_by_stage, stage_ns), 1)
    return ev / math.sqrt(var)


# ── Three profile builders ────────────────────────────────────────────────────

def build_conservative_team(
    riders: list[dict],
    ev_by_stage: dict,
    stage_ns: list[int],
    stage_types: dict,
) -> list[dict]:
    """
    Goal: minimise exposure to unpredictable outcomes across the lookahead.
    - Excludes breakaway artists entirely
    - Ranks by EV/σ across window
    """
    eligible = [
        r for r in riders
        if get_rider_archetype(r) != "breakaway_artist"
    ]
    eligible.sort(key=lambda r: ev_per_sigma(r, ev_by_stage, stage_ns), reverse=True)
    return greedy_select(eligible, ev_by_stage, stage_ns)


def build_balanced_team(
    riders: list[dict],
    ev_by_stage: dict,
    stage_ns: list[int],
    stage_types: dict,
) -> list[dict]:
    """
    Goal: maximise total EV across window. No additional constraints.
    This matches the optimizer output (greedy by total EV, no archetype filter).
    """
    scored = sorted(riders, key=lambda r: sum(
        ev_by_stage.get(r["rider_id"], {}).get(n, {}).get("total", 0) for n in stage_ns
    ), reverse=True)
    return greedy_select(scored, ev_by_stage, stage_ns)


def build_allin_team(
    riders: list[dict],
    ev_by_stage: dict,
    stage_ns: list[int],
    stage_types: dict,
) -> list[dict]:
    """
    Goal: maximise upside. Accept maximum variance.
    - Locks top-3 riders by total EV
    - On hilly/mountain stages: includes 1 breakaway artist
    - Fills remaining by EV/price from above-median variance pool
    """
    has_hilly = any(
        stage_types.get(n, "flat") in ("hilly", "mountain")
        for n in stage_ns
    )

    active = [r for r in riders if not r.get("isOut", False)]
    all_evs = {r["rider_id"]: total_ev(r, ev_by_stage, stage_ns) for r in active}

    top3 = sorted(active, key=lambda r: all_evs.get(r["rider_id"], 0), reverse=True)[:3]
    locked_ids = {r["rider_id"] for r in top3}

    breakaway_picks: list[dict] = []
    if has_hilly:
        hilly_stages = [n for n in stage_ns
                        if stage_types.get(n, "flat") in ("hilly", "mountain")]
        artists = [
            r for r in active
            if get_rider_archetype(r) == "breakaway_artist"
            and r["rider_id"] not in locked_ids
        ]
        if artists and hilly_stages:
            best = max(
                artists,
                key=lambda r: ev_by_stage.get(r["rider_id"], {})
                                         .get(hilly_stages[0], {}).get("total", 0)
            )
            breakaway_picks = [best]
            locked_ids.add(best["rider_id"])

    locked = top3 + breakaway_picks
    remaining_budget = BUDGET - sum(r["price"] for r in locked)
    remaining_slots  = TEAM_SIZE - len(locked)

    remaining = [r for r in active if r["rider_id"] not in locked_ids]
    remaining.sort(
        key=lambda r: all_evs.get(r["rider_id"], 0) / max(r["price"], 1),
        reverse=True,
    )
    fill = greedy_select(
        remaining, ev_by_stage, stage_ns,
        budget=remaining_budget,
        max_size=remaining_slots,
        exclude_ids=locked_ids,
    )
    return locked + fill


# ── Captain selection per profile ─────────────────────────────────────────────

def select_profile_captain(
    team: list[dict],
    ev_by_stage: dict,
    stage_n: int,
    profile: str,
    stage_types: dict,
) -> dict:
    """
    Conservative: highest EV/σ rider; never a breakaway_artist
    Balanced:     highest E[max(ΔV,0)] = highest positive EV on stage_n
    All-In:       breakaway_artist on hilly stages; highest EV otherwise
    """
    stage_type = stage_types.get(stage_n, "flat")

    if profile == "conservative":
        eligible = [r for r in team if get_rider_archetype(r) != "breakaway_artist"]
        pool = eligible or team
        return max(pool,
                   key=lambda r: max(
                       ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("total", 0), 0
                   ))

    if profile == "allin" and stage_type in ("hilly", "mountain"):
        artists = [r for r in team if get_rider_archetype(r) == "breakaway_artist"]
        if artists:
            return max(artists,
                       key=lambda r: ev_by_stage.get(r["rider_id"], {})
                                                .get(stage_n, {}).get("total", 0))

    return max(team,
               key=lambda r: max(
                   ev_by_stage.get(r["rider_id"], {}).get(stage_n, {}).get("total", 0), 0
               ))


# ── Profile output builder ────────────────────────────────────────────────────

def build_profile_output(
    name: str,
    team: list[dict],
    ev_by_stage: dict,
    stage_ns: list[int],
    stage_types: dict,
    profile_key: str,
) -> dict:
    captain = select_profile_captain(team, ev_by_stage, stage_ns[0], profile_key, stage_types)

    riders_out = []
    for r in sorted(team,
                    key=lambda x: -total_ev(x, ev_by_stage, stage_ns)):
        rid = r["rider_id"]
        var = total_variance(r, ev_by_stage, stage_ns)
        sd  = math.sqrt(var) if var > 0 else 0
        ev  = total_ev(r, ev_by_stage, stage_ns)
        riders_out.append({
            "name":        r["name"],
            "rider_id":    rid,
            "holdet_id":   r.get("holdet_id"),
            "team":        r["team"],
            "price":       r["price"],
            "archetype":   get_rider_archetype(r),
            "captain":     rid == captain["rider_id"],
            "ev_lookahead": round(ev),
            "stddev":       round(sd),
            "ev_per_sigma": round(ev / max(sd, 1), 3),
            **{f"ev_stage_{n}": ev_by_stage.get(rid, {}).get(n, {}).get("total", 0)
               for n in stage_ns},
        })

    return {
        "profile":           name,
        "captain":           captain["name"],
        "budget_spent":      sum(r["price"] for r in team),
        "team_ev_lookahead": sum(r["ev_lookahead"] for r in riders_out),
        "team_ev_sigma":     round(math.sqrt(
            sum(total_variance(r, ev_by_stage, stage_ns) for r in team)
        )),
        "riders": riders_out,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    riders      = load_riders()
    overrides   = load_overrides()
    riders      = [apply_overrides(r, overrides) for r in riders]
    ev_by_stage = load_ev_by_stage(LOOKAHEAD)
    stage_types = load_stage_profiles()

    profiles: dict = {}

    con_team = build_conservative_team(riders, ev_by_stage, LOOKAHEAD, stage_types)
    profiles["conservative"] = build_profile_output(
        "Conservative", con_team, ev_by_stage, LOOKAHEAD, stage_types, "conservative"
    )

    bal_team = build_balanced_team(riders, ev_by_stage, LOOKAHEAD, stage_types)
    profiles["balanced"] = build_profile_output(
        "Balanced", bal_team, ev_by_stage, LOOKAHEAD, stage_types, "balanced"
    )

    ai_team = build_allin_team(riders, ev_by_stage, LOOKAHEAD, stage_types)
    profiles["all_in"] = build_profile_output(
        "All-In", ai_team, ev_by_stage, LOOKAHEAD, stage_types, "allin"
    )

    out_path = BASE / "decisions" / "stage1_risk_profiles.yaml"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(yaml.dump(profiles, allow_unicode=True, sort_keys=False,
                                  default_flow_style=False))
    print(f"✓ Wrote → {out_path}")

    for key, p in profiles.items():
        print(f"\n── {p['profile']} (budget {p['budget_spent']:,}) ──")
        print(f"   Captain: {p['captain']}")
        print(f"   EV 3-stage: {p['team_ev_lookahead']:,}  |  σ: {p['team_ev_sigma']:,}")
        for r in p["riders"]:
            cap = " ★" if r["captain"] else ""
            print(f"   {r['name']:35s}  [{r['archetype']:18s}]"
                  f"  EV={r['ev_lookahead']:>8,}  σ={r['stddev']:>8,}"
                  f"  EV/σ={r['ev_per_sigma']:.2f}"
                  f"  {r['price']:>10,} kr{cap}")


if __name__ == "__main__":
    main()
