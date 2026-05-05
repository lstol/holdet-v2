"""
EV breakdown model — Giro 2026.

Computes per-component expected value for each rider on each stage:
  stage_finish, gc, jersey, sprint_kom, team_bonus, captain_bonus, total

All values in kr (int). Rule-based baseline — no ML model.

⚠️  Probability model: rule-based baseline (Phase 3a/3b)
Win probability is derived from terrain_affinity (Layer 0) only.
Sprint/KOM points are estimated from stage image parsing (stage_profiles_parsed.json).
These are structural estimates, not trained model outputs.
Replace in Phase 4 with trained StageFinishPosition model.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# ── Payoff tables (from contracts/v2.0/02_rules_payoff.md) ───────────────────
STAGE_PAYOFFS = [
    200_000, 150_000, 130_000, 120_000, 110_000,
    100_000,  95_000,  90_000,  85_000,  80_000,
     70_000,  55_000,  40_000,  30_000,  15_000,
]
GC_PAYOFFS = [100_000, 90_000, 80_000, 70_000, 60_000,
               50_000, 40_000, 30_000, 20_000, 10_000]
POINT_VALUE = 3_000   # kr per sprint or KOM point

# Geometric placement weights: P(position k) ≈ win_prob × WEIGHTS[k-1]
# Empirically calibrated so total EV ≈ 1.8–2.0× win_prob × 200,000
WEIGHTS = [1.00, 0.72, 0.57, 0.46, 0.38,
           0.33, 0.28, 0.25, 0.22, 0.20,
           0.18, 0.15, 0.12, 0.10, 0.08]


# ── Rider classification ─────────────────────────────────────────────────────
def classify(r: dict) -> str:
    ta  = r.get("terrain_affinity", {})
    cp  = r.get("consistency_profile", {})
    sp  = ta.get("sprint",   0)
    cl  = ta.get("climbing", 0)
    rel = cp.get("reliability", "medium")
    if sp >= 0.80:                  return "elite_sprinter"
    if sp >= 0.60:                  return "good_sprinter"
    if sp >= 0.40 and cl >= 0.50:  return "punchy"
    if cl >= 0.80:                  return "climber"
    if cl >= 0.70:                  return "gc_rider"
    if rel == "high" and sp < 0.60: return "breakaway"
    return "domestique"


# ── Raw score functions (not normalised) ─────────────────────────────────────
def _raw_flat(r: dict) -> float:
    sp = r.get("terrain_affinity", {}).get("sprint", 0)
    boost = {
        "elite_sprinter": 2.0, "good_sprinter": 1.2, "punchy": 0.45,
        "gc_rider": 0.10, "climber": 0.06, "breakaway": 0.30, "domestique": 0.04,
    }.get(classify(r), 0.04)
    return (sp ** 2.0) * boost

def _raw_hilly(r: dict) -> float:
    ta = r.get("terrain_affinity", {})
    sp = ta.get("sprint", 0); cl = ta.get("climbing", 0); mx = ta.get("mixed", 0)
    boost = {
        "elite_sprinter": 0.30, "good_sprinter": 0.45, "punchy": 1.40,
        "gc_rider": 1.10, "climber": 1.00, "breakaway": 1.60, "domestique": 0.08,
    }.get(classify(r), 0.08)
    return ((cl * 0.45 + mx * 0.35 + sp * 0.20) ** 2.0) * boost

def _raw_mountain(r: dict) -> float:
    ta = r.get("terrain_affinity", {})
    cl = ta.get("climbing", 0); mx = ta.get("mixed", 0)
    boost = {
        "elite_sprinter": 0.05, "good_sprinter": 0.07, "punchy": 0.60,
        "gc_rider": 1.20, "climber": 1.80, "breakaway": 0.80, "domestique": 0.05,
    }.get(classify(r), 0.05)
    return ((cl * 0.70 + mx * 0.20) ** 2.0) * boost

def _raw_uphill(r: dict) -> float:
    """Uphill/puncheur finish — between hilly and mountain."""
    ta = r.get("terrain_affinity", {})
    sp = ta.get("sprint", 0); cl = ta.get("climbing", 0); mx = ta.get("mixed", 0)
    boost = {
        "elite_sprinter": 0.20, "good_sprinter": 0.30, "punchy": 1.50,
        "gc_rider": 1.10, "climber": 1.30, "breakaway": 1.20, "domestique": 0.06,
    }.get(classify(r), 0.06)
    return ((cl * 0.40 + mx * 0.35 + sp * 0.25) ** 2.0) * boost

def _raw_tt(r: dict) -> float:
    tt = r.get("terrain_affinity", {}).get("time_trial", 0)
    return tt ** 2.0


FINISH_RAW = {
    "sprint":  _raw_flat,
    "flat":    _raw_flat,
    "hilly":   _raw_hilly,
    "uphill":  _raw_uphill,
    "summit":  _raw_mountain,
    "mountain":_raw_mountain,
    "tt":      _raw_tt,
    "ttt":     _raw_tt,
}


def make_win_probs(riders: list[dict], stage_terrain: str, finish_type: str) -> dict:
    """Return {rider_id: win_prob} normalised to sum=1."""
    fn = FINISH_RAW.get(finish_type) or FINISH_RAW.get(stage_terrain) or _raw_flat
    raw = {r["rider_id"]: fn(r) for r in riders}
    total = sum(raw.values()) or 1.0
    return {rid: v / total for rid, v in raw.items()}


# ── Stage finish EV ──────────────────────────────────────────────────────────
def _finish_ev(win_prob: float) -> int:
    return round(win_prob * sum(w * p for w, p in zip(WEIGHTS, STAGE_PAYOFFS)))


# ── GC EV ────────────────────────────────────────────────────────────────────
def _gc_ev(rider: dict, win_prob: float, stage: dict) -> int:
    """
    GC bonuses accumulate every stage regardless of stage type.
    Only GC riders / climbers have meaningful GC position probability.
    Approximation: GC prob ≈ mountain_win_prob × 4 (they score when they're competitive).
    On flat stages GC rarely changes → weight by stage climbing gain.
    """
    rtype = classify(rider)
    if rtype not in ("gc_rider", "climber", "punchy"):
        return 0
    # Weight by how much this stage affects GC (elevation-indexed)
    elev = stage.get("elevation_gain_m", 0) if isinstance(stage, dict) else 0
    gc_stage_weight = min(1.0, elev / 3000)  # 3000m+ = full GC relevance

    gc_win_prob = win_prob * 4 * gc_stage_weight
    gc_win_prob = min(gc_win_prob, 0.25)  # cap at 25%
    return round(gc_win_prob * sum(w * p for w, p in zip(WEIGHTS[:10], GC_PAYOFFS)))


# ── Jersey EV ────────────────────────────────────────────────────────────────
def _jersey_ev(rider: dict, win_prob: float, stage: dict) -> int:
    """
    Simplified jersey EV per stage:
    - Yellow (+25,000): stage winner on early stages; negligible for non-GC later
    - Green (+25,000): sprint-stage winner accumulates green standings
    - Polka dot (+25,000): climbers on mountain stages
    - Most Aggressive (+50,000): breakaway riders biased
    - White (+15,000): young GC riders
    """
    ta     = rider.get("terrain_affinity", {})
    sp_aff = ta.get("sprint",   0)
    cl_aff = ta.get("climbing", 0)
    age    = rider.get("age") or 28
    cp     = rider.get("consistency_profile", {})
    rel    = cp.get("reliability", "medium")
    rtype  = classify(rider)
    finish = stage.get("finish_type", "sprint") if isinstance(stage, dict) else "sprint"
    stype  = stage.get("stage_type", "flat")     if isinstance(stage, dict) else "flat"

    # Yellow jersey: stage winner holds it
    yellow_ev = win_prob * 25_000

    # Green jersey: meaningful for sprinters on sprint stages
    if finish in ("sprint",):
        green_ev = (sp_aff ** 1.5) * win_prob * 25_000 * 1.5
    elif finish in ("uphill", "summit"):
        green_ev = sp_aff * win_prob * 25_000 * 0.3
    else:
        green_ev = sp_aff * win_prob * 25_000 * 0.8

    # Polka dot: climbers on mountain/hilly stages
    if stype in ("mountain",):
        polka_ev = (cl_aff ** 2.0) * 25_000 * 0.25
    elif stype in ("hilly",):
        polka_ev = (cl_aff ** 2.0) * 25_000 * 0.08
    else:
        polka_ev = 0

    # Most aggressive: breakaway specialists biased; ~0.5–2% base
    agg_base = 0.015 if (rel == "high" and rtype in ("breakaway", "gc_rider", "climber")) else 0.004
    aggressive_ev = 50_000 * agg_base

    # White: young GC riders
    white_ev = 0
    if age <= 25 and rtype in ("gc_rider", "climber", "punchy"):
        white_ev = cl_aff * 15_000 * 0.12

    return round(yellow_ev + green_ev + polka_ev + aggressive_ev + white_ev)


# ── Sprint / KOM EV ──────────────────────────────────────────────────────────
def sprint_kom_ev(rider: dict, stage: dict) -> int:
    """
    Expected kr from sprint and KOM points on a stage.
    Based on parsed stage_profiles_parsed.json data.

    Calibration constants:
    - Sprint: 0.15 × sprint_affinity × points_available
      (An elite sprinter wins ~30% of intermediate sprints → 0.3 of 3pts × 0.5 positional weight ≈ 0.15)
    - KOM: 0.10 × climbing_affinity × points_available
      (Climbers contest KOMs realistically at ~10% of available points weight)

    These are PLACEHOLDER rule-based estimates. Not trained model outputs.
    """
    ta = rider.get("terrain_affinity", {})
    sp_aff = ta.get("sprint",   0)
    cl_aff = ta.get("climbing", 0)

    ev = 0.0
    for s in stage.get("intermediate_sprints", []):
        pts = s.get("points_available", 0) or 0
        ev += pts * sp_aff * 0.15 * POINT_VALUE

    for k in stage.get("kom_climbs", []):
        pts = k.get("points_available", 0) or 0
        ev += pts * cl_aff * 0.10 * POINT_VALUE

    return round(ev)


# ── Team bonus EV ────────────────────────────────────────────────────────────
def team_bonus_ev(rider: dict, teammates: list[dict], team_win_probs: dict) -> int:
    """
    Expected team bonus from teammates finishing top 3.
    Payoff: 1st→60,000 | 2nd→30,000 | 3rd→20,000 per active same-team rider.
    rider must be active (non-DNF) to receive team bonus.
    """
    ev = 0.0
    for t in teammates:
        tid = t["rider_id"]
        wp = team_win_probs.get(tid, 0)
        ev += wp * 60_000                    # teammate wins
        ev += (wp * WEIGHTS[1]) * 30_000     # teammate 2nd
        ev += (wp * WEIGHTS[2]) * 20_000     # teammate 3rd
    return round(ev)


# ── Captain bonus EV ─────────────────────────────────────────────────────────
def captain_bonus_ev(
    stage_finish: int, gc: int, jersey: int, sk: int
) -> int:
    """
    Captain earns positive-value growth deposited to bank.
    E[captain_bonus] = E[max(stage_ev_sum, 0)]
    Approximation: 0.6 × positive component sum (captures upside asymmetry,
    ignores negative days which the captain rule excludes).
    """
    positive = max(stage_finish + gc + jersey + sk, 0)
    return round(0.6 * positive)


# ── Full per-stage EV breakdown ───────────────────────────────────────────────
def rider_stage_ev_breakdown(
    rider: dict,
    stage: dict,
    win_prob: float,
    teammates: list[dict] | None = None,
    team_win_probs: dict | None = None,
    is_captain: bool = False,
) -> dict:
    """
    Returns dict:
      stage_finish, gc, jersey, sprint_kom, team_bonus, captain_bonus, total
    All in kr (int).
    """
    sf  = _finish_ev(win_prob)
    gc  = _gc_ev(rider, win_prob, stage)
    jer = _jersey_ev(rider, win_prob, stage)
    sk  = sprint_kom_ev(rider, stage)

    tb  = 0
    if teammates and team_win_probs:
        tb = team_bonus_ev(rider, teammates, team_win_probs)

    cb  = captain_bonus_ev(sf, gc, jer, sk) if is_captain else 0

    total = sf + gc + jer + sk + tb + cb
    return {
        "stage_finish":    sf,
        "gc":              gc,
        "jersey":          jer,
        "sprint_kom":      sk,
        "team_bonus":      tb,
        "captain_bonus":   cb,
        "total":           total,
    }


# ── Bulk computation and save ─────────────────────────────────────────────────
def build_all_breakdowns(
    riders: list[dict],
    stage_profiles: list[dict],
    stages_meta: list[dict],
    team_composition: list[dict] | None = None,
    output_dir: Path | None = None,
) -> dict:
    """
    Compute EV breakdown for all riders × all stages.
    Returns dict: {stage_number: {rider_id: breakdown_dict}}
    Also writes models/ev_breakdown_stage{N}.json if output_dir is set.
    """
    profiles_by_stage = {p["stage"]: p for p in stage_profiles}
    meta_by_stage     = {s["stage_number"]: s for s in stages_meta}

    # Precompute recommended team real-world team grouping for team bonus
    team_groups: dict[str, list[dict]] = {}
    if team_composition:
        for r in team_composition:
            team_groups.setdefault(r["team"], []).append(r)

    all_results: dict[int, dict] = {}

    for stage_n in range(1, 22):
        profile = profiles_by_stage.get(stage_n, {})
        meta    = meta_by_stage.get(stage_n, {})

        finish_type  = profile.get("finish_type", "sprint")
        stage_type   = profile.get("stage_type",  "flat")

        # Stage elevation from meta (for GC weighting)
        stage_with_elev = dict(profile)
        stage_with_elev["elevation_gain_m"] = meta.get("elevation_gain_m", 0)

        win_probs = make_win_probs(riders, stage_type, finish_type)

        stage_result: dict[str, dict] = {}

        for r in riders:
            rid = r["rider_id"]
            wp  = win_probs.get(rid, 0)

            # Teammates from team_composition with same real-world team
            teammates: list[dict] = []
            twp: dict = {}
            if team_composition:
                rt = r.get("team", "")
                teammates = [t for t in team_composition
                             if t["team"] == rt and t["rider_id"] != rid]
                twp = {t["rider_id"]: win_probs.get(t["rider_id"], 0) for t in teammates}

            bd = rider_stage_ev_breakdown(
                rider=r,
                stage=stage_with_elev,
                win_prob=wp,
                teammates=teammates,
                team_win_probs=twp,
                is_captain=False,
            )
            stage_result[rid] = bd

        all_results[stage_n] = stage_result

        if output_dir:
            out_path = output_dir / f"ev_breakdown_stage{stage_n}.json"
            out_path.write_text(
                json.dumps(
                    {"stage": stage_n, "riders": stage_result},
                    indent=2, ensure_ascii=False
                )
            )

    return all_results


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    riders_data   = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
    stages_data   = json.loads((BASE / "data/stages/stages_giro2026.json").read_text())["stages"]
    profiles_data = json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())

    active = [r for r in riders_data if r.get("status") != "dns" and r.get("holdet_id")]
    out_dir = BASE / "models"
    out_dir.mkdir(exist_ok=True)

    results = build_all_breakdowns(
        riders=active,
        stage_profiles=profiles_data,
        stages_meta=stages_data,
        output_dir=out_dir,
    )

    # Quick sanity check
    s1 = results[1]
    milan = next((bd for rid, bd in s1.items() if "milan" in rid), None)
    if milan:
        print(f"Milan S1 breakdown: {milan}")
    total_files = sum(1 for _ in out_dir.glob("ev_breakdown_stage*.json"))
    print(f"\n✓ Built {total_files} stage breakdown files → {out_dir}")
