"""
EV breakdown model — Giro 2026  (Phase 3c — scoring fixes applied)

Per-component expected value for each rider × stage:
  stage_finish, gc, jersey, sprint_kom, team_bonus, captain_bonus, total

All values in kr (int). Rule-based baseline — no ML model.

⚠️  Probability model: rule-based baseline (Phase 3c)
Win probability derived from terrain_affinity (Layer 0 attributes) only.
Sprint/KOM point values are the OFFICIAL fixed Giro scales — not estimated.
Position probabilities (p_sprint_position, p_kom_position) are rule-based.
Captain bonus = E[max(ΔV, 0)] from full position distribution.
Replace in Phase 4 with trained StageFinishPosition model.
"""

import json, argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# ── Payoff tables (contracts/v2.0/02_rules_payoff.md) ───────────────────────
STAGE_PAYOFFS = [
    200_000, 150_000, 130_000, 120_000, 110_000,
    100_000,  95_000,  90_000,  85_000,  80_000,
     70_000,  55_000,  40_000,  30_000,  15_000,
]  # positions 1–15; position 16+ = 0

GC_PAYOFFS = [100_000, 90_000, 80_000, 70_000, 60_000,
               50_000,  40_000, 30_000, 20_000, 10_000]  # positions 1–10

POINT_VALUE = 3_000   # kr per sprint or KOM point

# Official Giro sprint/KOM point scales (fixed — not estimated)
SPRINT_POINTS_INT    = [20,17,15,13,11,10,9,8,7,6,5,4,3,2,1]
SPRINT_POINTS_FINISH = [50,30,20,14,12,10,8,7,6,5,4,3,2,1,1]
KOM_POINTS = {
    "HC": [40,20,12,8,6,4,2,1],
    1:    [25,16,10,7,5,3,2,1],
    2:    [15,10,6,4,2,1],
    3:    [8,5,3,1],
    4:    [4,2,1],
}

# Geometric placement weights for stage finish EV
# P(position k) ≈ win_prob × WEIGHTS[k-1]
WEIGHTS = [1.00, 0.72, 0.57, 0.46, 0.38,
           0.33, 0.28, 0.25, 0.22, 0.20,
           0.18, 0.15, 0.12, 0.10, 0.08]


# ── Override application ──────────────────────────────────────────────────────
_ATTR_MAP = {
    "sprint_affinity":    "sprint",
    "climbing_affinity":  "climbing",
    "puncheur_affinity":  "mixed",
    "gc_affinity":        "gc",
    "breakaway_affinity": "breakaway",
    "tt_affinity":        "time_trial",
}

def load_rider_attributes(rider: dict, stage_n: int, overrides: list[dict]) -> dict:
    """
    Apply attribute overrides to a rider dict.
    Returns a copy with terrain_affinity updated for any matching overrides.
    Override keys (sprint_affinity, climbing_affinity, ...) map to terrain_affinity subkeys.
    """
    import copy
    rider_ovs = [
        o for o in overrides
        if o.get("holdet_id") == rider.get("holdet_id")
        and o.get("stage_first_applicable", 1) <= stage_n
    ]
    if not rider_ovs:
        return rider

    r  = copy.copy(rider)
    ta = dict(r.get("terrain_affinity", {}))
    for ov in rider_ovs:
        mapped = _ATTR_MAP.get(ov["attribute"])
        if mapped:
            ta[mapped] = ov["value"]
        if ov.get("giro_role_2026"):
            r["_giro_role_2026"] = ov["giro_role_2026"]
    r["terrain_affinity"] = ta
    return r


# ── Rider helpers ─────────────────────────────────────────────────────────────
def _ta(r: dict) -> dict:
    return r.get("terrain_affinity", {})

def classify(r: dict) -> str:
    ta  = _ta(r)
    cp  = r.get("consistency_profile", {})
    sp  = ta.get("sprint",   0)
    cl  = ta.get("climbing", 0)
    rel = cp.get("reliability", "medium")
    if sp >= 0.80:                   return "elite_sprinter"
    if sp >= 0.60:                   return "good_sprinter"
    if sp >= 0.40 and cl >= 0.50:   return "punchy"
    if cl >= 0.80:                   return "climber"
    if cl >= 0.70:                   return "gc_rider"
    if rel == "high" and sp < 0.60: return "breakaway"
    return "domestique"


# ── Raw score functions (unnormalised) ───────────────────────────────────────
def _raw_flat(r):
    sp = _ta(r).get("sprint", 0)
    b = {"elite_sprinter":2.0,"good_sprinter":1.2,"punchy":0.45,
         "gc_rider":0.10,"climber":0.06,"breakaway":0.30,"domestique":0.04}.get(classify(r), 0.04)
    return sp**2.0 * b

def _raw_hilly(r):
    ta = _ta(r); sp=ta.get("sprint",0); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.30,"good_sprinter":0.45,"punchy":1.40,
         "gc_rider":1.10,"climber":1.00,"breakaway":1.60,"domestique":0.08}.get(classify(r), 0.08)
    return ((cl*0.45 + mx*0.35 + sp*0.20)**2.0) * b

def _raw_mountain(r):
    ta = _ta(r); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.05,"good_sprinter":0.07,"punchy":0.60,
         "gc_rider":1.20,"climber":1.80,"breakaway":0.80,"domestique":0.05}.get(classify(r), 0.05)
    return ((cl*0.70 + mx*0.20)**2.0) * b

def _raw_uphill(r):
    ta = _ta(r); sp=ta.get("sprint",0); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.20,"good_sprinter":0.30,"punchy":1.50,
         "gc_rider":1.10,"climber":1.30,"breakaway":1.20,"domestique":0.06}.get(classify(r), 0.06)
    return ((cl*0.40 + mx*0.35 + sp*0.25)**2.0) * b

def _raw_tt(r):
    return _ta(r).get("time_trial", 0)**2.0

FINISH_RAW = {
    "sprint":"flat","flat":"flat","hilly":"hilly","uphill":"uphill",
    "summit":"mountain","mountain":"mountain","tt":"tt","ttt":"tt",
}
_RAW_FN = {"flat":_raw_flat,"hilly":_raw_hilly,"mountain":_raw_mountain,
           "uphill":_raw_uphill,"tt":_raw_tt}


def make_win_probs(riders: list[dict], stage_terrain: str, finish_type: str) -> dict:
    key = FINISH_RAW.get(finish_type) or FINISH_RAW.get(stage_terrain) or "flat"
    fn  = _RAW_FN[key]
    raw = {r["rider_id"]: fn(r) for r in riders}
    total = sum(raw.values()) or 1.0
    return {rid: v/total for rid, v in raw.items()}


# ── Position probability distribution ────────────────────────────────────────
def finish_probs(win_prob: float) -> list[float]:
    """
    Return P(position k) for k=1..15 using geometric decay off win_prob.
    P(k) = win_prob × WEIGHTS[k-1]   (not normalised to sum<1; interpretable
    as marginal probability of finishing at exactly that position).
    """
    return [win_prob * w for w in WEIGHTS]


# ── Fix 1: Sprint/KOM EV with official point scales ───────────────────────────
def p_sprint_position(affinity: float, position: int) -> float:
    """
    P(rider finishes at `position` in sprint context).
    Geometric decay: P(1) = affinity × 0.12, decay = 0.75.
    Rule-based — not a trained model output.
    """
    return (affinity * 0.12) * (0.75 ** (position - 1))

def p_kom_position(affinity: float, position: int) -> float:
    """
    P(rider finishes at `position` in KOM context).
    Geometric decay: P(1) = affinity × 0.08, decay = 0.70.
    Rule-based — not a trained model output.
    """
    return (affinity * 0.08) * (0.70 ** (position - 1))


def sprint_kom_ev(rider: dict, roadbook: dict) -> int:
    """
    Expected kr from sprint and KOM points using official Giro point scales.
    Point values are FIXED per official roadbook — not estimated.
    Position probabilities are rule-based (see p_sprint_position, p_kom_position).
    """
    ta      = _ta(rider)
    sp_aff  = ta.get("sprint",   0)
    cl_aff  = ta.get("climbing", 0)
    ev      = 0.0

    for s in roadbook.get("intermediate_sprints", []):
        for pos, pts in enumerate(s["points"], start=1):
            ev += p_sprint_position(sp_aff, pos) * pts * POINT_VALUE

    fs = roadbook.get("finish_sprint")
    if fs:
        for pos, pts in enumerate(fs["points"], start=1):
            ev += p_sprint_position(sp_aff, pos) * pts * POINT_VALUE

    for k in roadbook.get("kom_climbs", []):
        for pos, pts in enumerate(k["points"], start=1):
            ev += p_kom_position(cl_aff, pos) * pts * POINT_VALUE

    return round(ev)


# ── Fix 2: Stage finish EV ────────────────────────────────────────────────────
def finish_ev(win_prob: float) -> int:
    return round(win_prob * sum(w * p for w, p in zip(WEIGHTS, STAGE_PAYOFFS)))


# ── Fix 2: GC EV — non-zero on flat stages ───────────────────────────────────
def gc_ev(rider: dict, win_prob: float, stage_n: int, finish_type: str) -> int:
    """
    GC EV has two components:

    1. GC position bonus from stage result.
       On flat/sprint stages the entire peloton finishes same time, so
       GC position = stage finish position → GC payoffs apply to positions 1–10.
       On mountain/summit stages GC is determined by accumulated time gaps.

    2. After early mountain stages GC contenders accumulate GC position value
       independently of individual stage finish.
    """
    rtype = classify(rider)
    ta    = _ta(rider)
    cl    = ta.get("climbing", 0)

    ev = 0.0

    if finish_type in ("sprint", "flat"):
        # Full peloton arrives together: GC pos = stage finish pos for top 10
        # E[GC value] = sum_{k=1}^{10} P(finish at k) × GC_PAYOFFS[k-1]
        probs = finish_probs(win_prob)
        for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
            ev += prob * gc_pay

    elif finish_type in ("uphill", "summit", "mountain"):
        # Mountain stage: GC contenders gain time; others lose or neutral
        if rtype in ("gc_rider", "climber"):
            # GC contenders can improve GC standing on mountain stages
            # P(top 5 GC) ≈ climbing_affinity × win_prob × 3
            p_top5  = min(cl * win_prob * 3.0, 0.20)
            p_top10 = min(cl * win_prob * 7.0, 0.40)
            ev += p_top5  * GC_PAYOFFS[4]   # ~60,000 kr (5th GC pos)
            ev += (p_top10 - p_top5) * GC_PAYOFFS[7]  # ~30,000 kr (8th GC pos)
        elif rtype in ("punchy",):
            p_top10 = min(cl * win_prob * 2.0, 0.10)
            ev += p_top10 * GC_PAYOFFS[7]
        # Sprinters / breakaway / domestiques: 0 GC EV on mountain stages

    elif finish_type in ("hilly",):
        # Hilly: mix — sprinters lose a bit; puncheurs/GC competitive
        if finish_type == "hilly":
            probs = finish_probs(win_prob)
            for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
                ev += prob * gc_pay * 0.6   # reduced — time gaps are smaller on hilly

    elif finish_type in ("tt", "ttt"):
        # ITT: top TT specialists improve GC; others neutral
        tt_aff = ta.get("time_trial", 0)
        if tt_aff >= 0.65:
            probs = finish_probs(win_prob)
            for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
                ev += prob * gc_pay

    return round(ev)


# ── Jersey EV ────────────────────────────────────────────────────────────────
def jersey_ev(rider: dict, win_prob: float, finish_type: str, stage_type: str) -> int:
    ta     = _ta(rider)
    sp_aff = ta.get("sprint",   0)
    cl_aff = ta.get("climbing", 0)
    age    = rider.get("age") or 28
    cp     = rider.get("consistency_profile", {})
    rel    = cp.get("reliability", "medium")
    rtype  = classify(rider)

    # Yellow jersey: stage winner holds it
    yellow = win_prob * 25_000

    # Green jersey: meaningful for sprinters on sprint stages
    if finish_type == "sprint":
        green = (sp_aff ** 1.5) * win_prob * 25_000 * 1.5
    else:
        green = sp_aff * win_prob * 25_000 * 0.3

    # Polka dot: climbers on mountain stages
    if stage_type == "mountain":
        polka = (cl_aff ** 2.0) * 25_000 * 0.25
    elif stage_type == "hilly":
        polka = (cl_aff ** 2.0) * 25_000 * 0.06
    else:
        polka = 0

    # Most aggressive
    agg_base = 0.015 if (rel == "high" and rtype in ("breakaway","gc_rider","climber")) else 0.004
    aggressive = 50_000 * agg_base

    # White: young GC riders
    white = 0
    if age <= 25 and rtype in ("gc_rider", "climber", "punchy"):
        white = cl_aff * 15_000 * 0.12

    return round(yellow + green + polka + aggressive + white)


# ── Fix 3: Captain bonus = E[max(ΔV, 0)] ─────────────────────────────────────
def captain_bonus_ev(
    win_prob: float,
    finish_type: str,
    je: int,
    sk: int,
) -> int:
    """
    E[CaptainPositiveValueGrowth] = E[max(ΔV, 0)]

    ΔV at position k = stage_finish_payoff(k) + gc_payoff_at_k + jersey + sprint_kom
    jersey and sprint_kom treated as deterministic (position-independent approximation).
    gc_payoff_at_k: on flat stages GC follows stage position; on others set to 0 here
    (gc is already captured separately; adding it here would double-count).

    Captain receives positive ΔV into bank; negative days not amplified.
    """
    expected_positive = 0.0
    probs = finish_probs(win_prob)
    p_outside_top15 = max(0.0, 1.0 - sum(probs))

    # For positions 1–15
    for k, (p, stage_pay) in enumerate(zip(probs, STAGE_PAYOFFS), start=1):
        # GC payoff at this position (flat stage: GC = stage order)
        gc_at_k = GC_PAYOFFS[k-1] if (finish_type == "sprint" and k <= 10) else 0
        delta_v = stage_pay + gc_at_k + je + sk
        if delta_v > 0:
            expected_positive += p * delta_v

    # Position 16+: stage_pay = 0, gc = 0 (outside top 10)
    delta_v_outside = 0 + je + sk   # only jersey and sprint/KOM
    if delta_v_outside > 0:
        expected_positive += p_outside_top15 * delta_v_outside

    return round(expected_positive)


# ── Team bonus EV ────────────────────────────────────────────────────────────
def team_bonus_ev(rider: dict, teammates: list[dict], team_win_probs: dict) -> int:
    ev = 0.0
    for t in teammates:
        wp = team_win_probs.get(t["rider_id"], 0)
        ev += wp * 60_000 + wp * WEIGHTS[1] * 30_000 + wp * WEIGHTS[2] * 20_000
    return round(ev)


# ── Full per-stage breakdown ──────────────────────────────────────────────────
def rider_stage_ev_breakdown(
    rider: dict,
    stage_meta: dict,
    roadbook: dict,
    win_prob: float,
    stage_n: int,
    teammates: list[dict] | None = None,
    team_win_probs: dict | None = None,
    is_captain: bool = False,
) -> dict:
    finish_type = roadbook.get("finish_type", "sprint")
    stage_type  = roadbook.get("stage_type",  "flat")

    sf  = finish_ev(win_prob)
    gc  = gc_ev(rider, win_prob, stage_n, finish_type)
    jer = jersey_ev(rider, win_prob, finish_type, stage_type)
    sk  = sprint_kom_ev(rider, roadbook)

    tb = 0
    if teammates and team_win_probs:
        tb = team_bonus_ev(rider, teammates, team_win_probs)

    cb = 0
    if is_captain:
        cb = captain_bonus_ev(win_prob, finish_type, jer, sk)

    total = sf + gc + jer + sk + tb + cb
    return {
        "stage_finish":  sf,
        "gc":            gc,
        "jersey":        jer,
        "sprint_kom":    sk,
        "team_bonus":    tb,
        "captain_bonus": cb,
        "total":         total,
    }


# ── Variance estimate (for risk profiles) ────────────────────────────────────
def rider_stage_variance(win_prob: float, finish_type: str, je: int, sk: int) -> float:
    """
    σ² = E[ΔV²] − (E[ΔV])²
    Computed over position distribution 1..15 + outside-top-15.
    """
    probs = finish_probs(win_prob)
    p_out = max(0.0, 1.0 - sum(probs))

    ev  = 0.0
    ev2 = 0.0
    for k, (p, pay) in enumerate(zip(probs, STAGE_PAYOFFS), start=1):
        gc_k = GC_PAYOFFS[k-1] if (finish_type == "sprint" and k <= 10) else 0
        dv   = pay + gc_k + je + sk
        ev  += p * dv
        ev2 += p * dv * dv

    # Outside top 15
    dv_out = je + sk
    ev  += p_out * dv_out
    ev2 += p_out * dv_out * dv_out

    return max(0.0, ev2 - ev * ev)


# ── Bulk build ────────────────────────────────────────────────────────────────
def build_all_breakdowns(
    riders: list[dict],
    stages_meta: list[dict],
    roadbooks: list[dict],
    output_dir: Path | None = None,
) -> dict[int, dict]:
    meta_by_n     = {s["stage_number"]: s for s in stages_meta}
    roadbook_by_n = {r["stage"]: r for r in roadbooks}

    all_results: dict[int, dict] = {}

    for stage_n in range(1, 22):
        meta     = meta_by_n.get(stage_n, {})
        roadbook = roadbook_by_n.get(stage_n, {})
        finish_t = roadbook.get("finish_type", "sprint")
        stage_t  = roadbook.get("stage_type",  "flat")

        win_probs = make_win_probs(riders, stage_t, finish_t)

        stage_result: dict[str, dict] = {}
        for r in riders:
            rid = r["rider_id"]
            wp  = win_probs.get(rid, 0)
            bd  = rider_stage_ev_breakdown(
                rider=r, stage_meta=meta, roadbook=roadbook,
                win_prob=wp, stage_n=stage_n,
            )
            # Also compute variance
            je = bd["jersey"]
            sk = bd["sprint_kom"]
            bd["variance"] = round(rider_stage_variance(wp, finish_t, je, sk))
            stage_result[rid] = bd

        all_results[stage_n] = stage_result

        if output_dir:
            out = output_dir / f"ev_breakdown_stage{stage_n}.json"
            out.write_text(json.dumps(
                {"stage": stage_n, "finish_type": finish_t,
                 "stage_type": stage_t, "riders": stage_result},
                indent=2, ensure_ascii=False
            ))

    return all_results


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    riders_raw  = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
    stages_data = json.loads((BASE / "data/stages/stages_giro2026.json").read_text())["stages"]
    roadbooks   = json.loads((BASE / "data/stages/stage_roadbook.json").read_text())

    active  = [r for r in riders_raw if r.get("status") != "dns" and r.get("holdet_id")]
    out_dir = BASE / "models"
    out_dir.mkdir(exist_ok=True)

    results = build_all_breakdowns(
        riders=active, stages_meta=stages_data, roadbooks=roadbooks, output_dir=out_dir
    )

    # Validation output
    s1    = results[1]
    milan = next((bd for rid, bd in s1.items() if "milan" in rid), None)
    if milan:
        print("\nMilan Stage 1 breakdown (Phase 3c):")
        for k, v in milan.items():
            print(f"  {k:20s}: {v:>10,}")

    # Quick cross-stage summary for Milan
    print("\nMilan multi-stage EV summary:")
    for n in [1, 2, 3, 7, 14, 19]:
        bd = results[n]
        m  = next((v for k, v in bd.items() if "milan" in k), None)
        if m:
            print(f"  S{n:2d}: total={m['total']:>8,}  sf={m['stage_finish']:>7,}"
                  f"  gc={m['gc']:>7,}  sk={m['sprint_kom']:>7,}")

    total_files = sum(1 for _ in out_dir.glob("ev_breakdown_stage*.json"))
    print(f"\n✓ {total_files} stage breakdown files written → {out_dir}")
