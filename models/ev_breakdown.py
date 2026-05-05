"""
EV breakdown model — Giro 2026  (Phase 3h — scenario-based, AFFINITY_POWER)

Per-component expected value for each rider × stage:
  stage_finish, sprint_kom, gc, jersey, team_bonus, captain_bonus, total

Per-scenario EV and P(win) for dashboard sliders:
  scenario_ev:   {bunch_sprint, reduced_sprint, breakaway, gc_day}
  scenario_p_win:{bunch_sprint, reduced_sprint, breakaway, gc_day}

All monetary values in kr (int). AFFINITY_POWER=4 gives Milan ~30% P(win) on flat stages.

Fix A: P(win) recomputed per stage using stage_dict (holdet_type → scenario weights)
Fix B: sprint_kom_ev <= stage_finish_ev assertion + conservation check
Fix C: Team bonus as proper expectation Σ P(teammate at pos k) × bonus(k)
"""

import json, argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# ── Constants ─────────────────────────────────────────────────────────────────

AFFINITY_POWER = 8     # power-weighting to amplify elite vs journeyman differences
POINT_VALUE    = 3_000 # kr per Holdet point

HOLDET_FINISH_POINTS = {
    "flat":     [50, 35, 25, 18, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1],
    "hilly":    [25, 18, 12, 8, 6, 5, 4, 3, 2, 1],
    "mountain": [15, 12, 9, 7, 6, 5, 4, 3, 2, 1],
}

SPRINT_POINTS = [12, 8, 5, 3, 1]  # one intermediate sprint per stage, top 5

SCENARIO_CONFIGS = {
    "bunch_sprint": {
        "label": "Bunch Sprint",
        "description": "Full peloton sprint — pure sprinters dominate",
        "attr": "sprint_affinity",
        "threshold": 0.85,  # only elite GT sprinters (Milan, Groves, De Lie tier)
        "contender_mass": 0.95,  # non-sprinters genuinely can't win GT flat stages
        "color": "#2ecc71",
    },
    "reduced_sprint": {
        "label": "Reduced Sprint",
        "description": "Small group sprint — puncheurs and versatile riders",
        "attr": "puncheur_affinity",
        "threshold": 0.65,  # puncheurs and competent finishers
        "contender_mass": 0.85,
        "color": "#f39c12",
    },
    "breakaway": {
        "label": "Breakaway",
        "description": "Escape group survives — breakaway artists win",
        "attr": "breakaway_affinity",
        "threshold": 0.75,  # committed breakaway specialists
        "contender_mass": 0.80,
        "color": "#e74c3c",
    },
    "gc_day": {
        "label": "GC Day",
        "description": "GC selection — climbers and GC leaders take time",
        "attr": "gc_affinity",
        "threshold": 0.70,  # genuine GC contenders
        "contender_mass": 0.90,
        "color": "#9b59b6",
    },
}

STAGE_TYPE_DEFAULTS = {
    "flat": {
        "bunch_sprint": 0.70, "reduced_sprint": 0.20,
        "breakaway": 0.10, "gc_day": 0.00,
    },
    "hilly": {
        "bunch_sprint": 0.15, "reduced_sprint": 0.35,
        "breakaway": 0.35, "gc_day": 0.15,
    },
    "mountain": {
        "bunch_sprint": 0.00, "reduced_sprint": 0.05,
        "breakaway": 0.25, "gc_day": 0.70,
    },
    "mountain_itt": {
        "bunch_sprint": 0.00, "reduced_sprint": 0.00,
        "breakaway": 0.00, "gc_day": 1.00,
    },
}

PURE_SCENARIOS = {
    "bunch_sprint":   {"bunch_sprint": 1.0, "reduced_sprint": 0.0, "breakaway": 0.0, "gc_day": 0.0},
    "reduced_sprint": {"bunch_sprint": 0.0, "reduced_sprint": 1.0, "breakaway": 0.0, "gc_day": 0.0},
    "breakaway":      {"bunch_sprint": 0.0, "reduced_sprint": 0.0, "breakaway": 1.0, "gc_day": 0.0},
    "gc_day":         {"bunch_sprint": 0.0, "reduced_sprint": 0.0, "breakaway": 0.0, "gc_day": 1.0},
}

# Team bonus payoffs (kr) for teammate at positions 1–3
TEAM_BONUS_PAYOFFS = {1: 60_000, 2: 30_000, 3: 20_000}

# ── Attribute mapping: override key → terrain_affinity subkey ────────────────
_ATTR_MAP = {
    "sprint_affinity":    "sprint",
    "climbing_affinity":  "climbing",
    "puncheur_affinity":  "mixed",
    "gc_affinity":        "gc",
    "breakaway_affinity": "breakaway",
    "tt_affinity":        "time_trial",
}

# SCENARIO_CONFIGS.attr values → terrain_affinity subkeys
_SCENARIO_TA_MAP = {
    "sprint_affinity":    "sprint",
    "puncheur_affinity":  "mixed",
    "gc_affinity":        "gc",
    "breakaway_affinity": "breakaway",
}

_PRIORITY = {"manual": 3, "expert_intel": 2, "copilot_research": 1, "web_search": 1}


# ── Override application ──────────────────────────────────────────────────────

def load_rider_attributes(rider: dict, stage_n: int, overrides: list[dict]) -> dict:
    """
    Apply attribute overrides to a rider dict.
    Returns a copy with terrain_affinity updated for any matching overrides.

    Override keys (sprint_affinity, climbing_affinity, ...) map to terrain_affinity subkeys.
    mode='replace' (default): sets the attribute to `value`.
    mode='adjust': adds `adjustment` (or fallback `value`) to the current value.

    Priority (lower applied first, so higher wins): manual=3 > expert_intel=2 > copilot/web=1.
    stage_last_applicable: override only applies up to and including that stage.

    All results clamped to [0, 1].
    """
    import copy
    rider_ovs = [
        o for o in overrides
        if o.get("holdet_id") == rider.get("holdet_id")
        and o.get("stage_first_applicable", 1) <= stage_n
        and o.get("stage_last_applicable", 99) >= stage_n
    ]
    if not rider_ovs:
        return rider

    r  = copy.copy(rider)
    ta = dict(r.get("terrain_affinity", {}))
    overridden: list[str] = []

    sorted_ovs = sorted(rider_ovs, key=lambda o: _PRIORITY.get(o.get("source", ""), 0))
    for ov in sorted_ovs:
        mapped = _ATTR_MAP.get(ov["attribute"])
        if mapped:
            mode   = ov.get("mode", "replace")
            source = ov.get("source", "")
            if mode == "adjust":
                base       = ta.get(mapped, 0.5)
                adjustment = float(ov.get("adjustment", ov.get("value", 0.0)))
                ta[mapped] = round(min(1.0, max(0.0, base + adjustment)), 3)
            else:
                ta[mapped] = round(min(1.0, max(0.0, float(ov["value"]))), 3)
            overridden.append(f"{mapped}({source})")
        if ov.get("giro_role_2026"):
            r["_giro_role_2026"] = ov["giro_role_2026"]

    r["terrain_affinity"] = ta
    if overridden:
        r["_overridden"] = overridden
    return r


# ── Affinity helpers ──────────────────────────────────────────────────────────

def _ta(r: dict) -> dict:
    return r.get("terrain_affinity", {})

def get_affinity(rider: dict, attr_key: str) -> float:
    """Read an affinity value using scenario attr key (e.g. 'sprint_affinity')."""
    ta_key = _SCENARIO_TA_MAP.get(attr_key)
    if ta_key:
        return rider.get("terrain_affinity", {}).get(ta_key, 0)
    return 0.0


# ── Scenario-based win probability (Fix A) ───────────────────────────────────

def compute_conditional_win_prob(rider: dict, scenario_key: str,
                                  all_riders: list[dict]) -> float:
    """
    P(win | scenario) using power-weighted contender pool.

    Below-threshold riders return 0 (scenario-specific: non-contenders
    in this scenario genuinely cannot win). The contender_mass is scenario-
    specific so probabilities sum to ≈ contender_mass across the full field.
    """
    cfg           = SCENARIO_CONFIGS[scenario_key]
    attr          = cfg["attr"]
    threshold     = cfg["threshold"]
    contender_mass = cfg["contender_mass"]

    rider_attr = get_affinity(rider, attr)
    if rider_attr < threshold:
        return 0.0  # non-contender in this scenario

    contenders = [
        r for r in all_riders
        if get_affinity(r, attr) >= threshold and not r.get("isOut", False)
    ]
    total_weight = sum(get_affinity(r, attr) ** AFFINITY_POWER for r in contenders)
    if total_weight == 0:
        return 0.0

    rider_weight = rider_attr ** AFFINITY_POWER
    return contender_mass * (rider_weight / total_weight)


def compute_blended_win_prob(rider: dict, scenario_weights: dict,
                              all_riders: list[dict]) -> float:
    """
    P(win) = Σ_s weight(s) × P(win | scenario s).
    scenario_weights must sum to ~1.0.
    """
    p_win = 0.0
    for scenario_key, weight in scenario_weights.items():
        if weight <= 0:
            continue
        p_win += weight * compute_conditional_win_prob(rider, scenario_key, all_riders)
    return p_win


# ── Stage finish EV (Fix A — uses Holdet points) ─────────────────────────────

def compute_stage_finish_ev(rider: dict, stage_roadbook_entry: dict,
                             p_win: float) -> int:
    """Stage finish EV using official Holdet point scale (HOLDET_FINISH_POINTS)."""
    group = stage_roadbook_entry.get("stage_group", "hilly")
    finish_pts = HOLDET_FINISH_POINTS.get(group, HOLDET_FINISH_POINTS["mountain"])

    ev = 0.0
    for k, pts in enumerate(finish_pts, start=1):
        p_pos = p_win * ((1 - p_win) ** (k - 1))
        ev += p_pos * pts * POINT_VALUE
    return round(ev)


# ── Sprint EV (Fix B — one intermediate sprint, correct points) ───────────────

def compute_sprint_ev(rider: dict, stage_roadbook_entry: dict,
                       p_win: float, all_riders: list[dict],
                       scenario_weights: dict) -> int:
    """
    One intermediate sprint per stage.
    E[points] = p_win × total_sprint_pts × POINT_VALUE

    Conservation: Σ sprint_ev ≈ total_sprint_pts × POINT_VALUE × Σ p_win
    Σ p_win ≈ contender_mass (0.80–0.95 depending on scenario), so total
    sprint EV ≈ 70–95% of the full sprint prize — correct, as outsiders
    realistically have zero chance in this scenario model.
    """
    if "intermediate_sprint" not in stage_roadbook_entry:
        return 0
    total_sprint_pts = sum(SPRINT_POINTS)  # = 29
    return round(p_win * total_sprint_pts * POINT_VALUE)


# ── Team bonus EV (Fix C — proper expectation) ───────────────────────────────

def compute_team_bonus_ev(rider: dict, team: list[dict],
                           all_riders: list[dict],
                           scenario_weights: dict) -> int:
    """
    E[team bonus for rider X] =
      Σ_teammate T: Σ_k=1..3: P(T at position k) × bonus(k)

    P(T at position k) = p_win_T × (1 − p_win_T)^(k-1)
    """
    ev = 0.0
    for teammate in team:
        if teammate.get("holdet_id") == rider.get("holdet_id"):
            continue
        if teammate.get("rider_id") == rider.get("rider_id"):
            continue
        p_win_t = compute_blended_win_prob(teammate, scenario_weights, all_riders)
        for pos, bonus in TEAM_BONUS_PAYOFFS.items():
            p_pos = p_win_t * ((1 - p_win_t) ** (pos - 1))
            ev += p_pos * bonus
    return round(ev)


# ── Rider archetype ───────────────────────────────────────────────────────────

def get_rider_archetype(rider: dict) -> str:
    ta = rider.get("terrain_affinity", {})
    s  = ta.get("sprint",    0)
    c  = ta.get("climbing",  0)
    p  = ta.get("mixed",     0)
    g  = ta.get("gc",        0)
    b  = ta.get("breakaway", 0)
    t  = ta.get("time_trial",0)
    if g >= 0.65 and (c >= 0.60 or t >= 0.55): return "gc_leader"
    if b >= 0.65 and s < 0.55 and c < 0.55:    return "breakaway_artist"
    if s >= 0.65:                                return "sprinter"
    if c >= 0.65:                                return "climber"
    if p >= 0.55:                                return "puncheur"
    if t >= 0.65:                                return "tt_specialist"
    return "all_rounder"


# ── Per-scenario EV builder (for dashboard sliders) ──────────────────────────

def build_rider_scenario_data(riders: list[dict], roadbook_entry: dict,
                               all_riders: list[dict]) -> list[dict]:
    """
    For each rider, compute EV and P(win) under each pure scenario.
    Returns list of dicts for embedding in dashboard HTML as RIDER_SCENARIO_DATA.
    """
    result = []
    for rider in riders:
        row = {
            "id":       rider.get("holdet_id"),
            "rider_id": rider.get("rider_id"),
            "name":     rider["name"],
            "team":     rider.get("team", ""),
            "price":    rider.get("price", 0) or rider.get("startPrice", 0),
            "is_out":   rider.get("isOut", False),
            "archetype": get_rider_archetype(rider),
            "scenario_ev":    {},
            "scenario_p_win": {},
        }
        for scenario_key, weights in PURE_SCENARIOS.items():
            p_win = compute_blended_win_prob(rider, weights, all_riders)
            ev = (compute_stage_finish_ev(rider, roadbook_entry, p_win)
                  + compute_sprint_ev(rider, roadbook_entry, p_win,
                                      all_riders, weights))
            row["scenario_ev"][scenario_key]    = ev
            row["scenario_p_win"][scenario_key] = round(p_win, 4)
        result.append(row)
    return result


# ── Legacy helpers (kept for backward compat with existing build scripts) ─────

def _ta_legacy(r: dict) -> dict:
    return r.get("terrain_affinity", {})

def classify(r: dict) -> str:
    ta  = _ta_legacy(r)
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


STAGE_PAYOFFS = [
    200_000, 150_000, 130_000, 120_000, 110_000,
    100_000,  95_000,  90_000,  85_000,  80_000,
     70_000,  55_000,  40_000,  30_000,  15_000,
]

GC_PAYOFFS = [100_000, 90_000, 80_000, 70_000, 60_000,
               50_000,  40_000, 30_000, 20_000, 10_000]

WEIGHTS = [1.00, 0.72, 0.57, 0.46, 0.38,
           0.33, 0.28, 0.25, 0.22, 0.20,
           0.18, 0.15, 0.12, 0.10, 0.08]


def finish_probs(win_prob: float) -> list[float]:
    return [win_prob * w for w in WEIGHTS]


def finish_ev(win_prob: float) -> int:
    return round(win_prob * sum(w * p for w, p in zip(WEIGHTS, STAGE_PAYOFFS)))


def gc_ev(rider: dict, win_prob: float, stage_n: int, finish_type: str) -> int:
    rtype = classify(rider)
    ta    = _ta_legacy(rider)
    cl    = ta.get("climbing", 0)
    ev    = 0.0

    if finish_type in ("sprint", "flat"):
        probs = finish_probs(win_prob)
        for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
            ev += prob * gc_pay
    elif finish_type in ("uphill", "summit", "mountain"):
        if rtype in ("gc_rider", "climber"):
            p_top5  = min(cl * win_prob * 3.0, 0.20)
            p_top10 = min(cl * win_prob * 7.0, 0.40)
            ev += p_top5  * GC_PAYOFFS[4]
            ev += (p_top10 - p_top5) * GC_PAYOFFS[7]
        elif rtype in ("punchy",):
            p_top10 = min(cl * win_prob * 2.0, 0.10)
            ev += p_top10 * GC_PAYOFFS[7]
    elif finish_type in ("hilly",):
        probs = finish_probs(win_prob)
        for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
            ev += prob * gc_pay * 0.6
    elif finish_type in ("tt", "ttt"):
        tt_aff = ta.get("time_trial", 0)
        if tt_aff >= 0.65:
            probs = finish_probs(win_prob)
            for k, (prob, gc_pay) in enumerate(zip(probs[:10], GC_PAYOFFS)):
                ev += prob * gc_pay

    return round(ev)


def jersey_ev(rider: dict, win_prob: float, finish_type: str, stage_type: str) -> int:
    ta     = _ta_legacy(rider)
    sp_aff = ta.get("sprint",   0)
    cl_aff = ta.get("climbing", 0)
    age    = rider.get("age") or 28
    cp     = rider.get("consistency_profile", {})
    rel    = cp.get("reliability", "medium")
    rtype  = classify(rider)

    yellow = win_prob * 25_000

    if finish_type == "sprint":
        green = (sp_aff ** 1.5) * win_prob * 25_000 * 1.5
    else:
        green = sp_aff * win_prob * 25_000 * 0.3

    if stage_type == "mountain":
        polka = (cl_aff ** 2.0) * 25_000 * 0.25
    elif stage_type == "hilly":
        polka = (cl_aff ** 2.0) * 25_000 * 0.06
    else:
        polka = 0

    agg_base = 0.015 if (rel == "high" and rtype in ("breakaway","gc_rider","climber")) else 0.004
    aggressive = 50_000 * agg_base

    white = 0
    if age <= 25 and rtype in ("gc_rider", "climber", "punchy"):
        white = cl_aff * 15_000 * 0.12

    return round(yellow + green + polka + aggressive + white)


def captain_bonus_ev(win_prob: float, finish_type: str, je: int, sk: int) -> int:
    expected_positive = 0.0
    probs = finish_probs(win_prob)
    p_outside_top15 = max(0.0, 1.0 - sum(probs))

    for k, (p, stage_pay) in enumerate(zip(probs, STAGE_PAYOFFS), start=1):
        gc_at_k = GC_PAYOFFS[k-1] if (finish_type == "sprint" and k <= 10) else 0
        delta_v = stage_pay + gc_at_k + je + sk
        if delta_v > 0:
            expected_positive += p * delta_v

    delta_v_outside = 0 + je + sk
    if delta_v_outside > 0:
        expected_positive += p_outside_top15 * delta_v_outside

    return round(expected_positive)


def team_bonus_ev(rider: dict, teammates: list[dict], team_win_probs: dict) -> int:
    """Legacy team bonus (uses pre-computed win probs dict). Kept for build_stage1 compat."""
    ev = 0.0
    for t in teammates:
        wp = team_win_probs.get(t["rider_id"], 0)
        ev += wp * 60_000 + wp * WEIGHTS[1] * 30_000 + wp * WEIGHTS[2] * 20_000
    return round(ev)


def rider_stage_variance(win_prob: float, finish_type: str, je: int, sk: int) -> float:
    probs = finish_probs(win_prob)
    p_out = max(0.0, 1.0 - sum(probs))
    ev  = 0.0
    ev2 = 0.0
    for k, (p, pay) in enumerate(zip(probs, STAGE_PAYOFFS), start=1):
        gc_k = GC_PAYOFFS[k-1] if (finish_type == "sprint" and k <= 10) else 0
        dv   = pay + gc_k + je + sk
        ev  += p * dv
        ev2 += p * dv * dv
    dv_out = je + sk
    ev  += p_out * dv_out
    ev2 += p_out * dv_out * dv_out
    return max(0.0, ev2 - ev * ev)


FINISH_RAW = {
    "sprint":"flat","flat":"flat","hilly":"hilly","uphill":"uphill",
    "summit":"mountain","mountain":"mountain","tt":"tt","ttt":"tt",
}

def _raw_flat(r):
    sp = _ta_legacy(r).get("sprint", 0)
    b = {"elite_sprinter":2.0,"good_sprinter":1.2,"punchy":0.45,
         "gc_rider":0.10,"climber":0.06,"breakaway":0.30,"domestique":0.04}.get(classify(r), 0.04)
    return sp**2.0 * b

def _raw_hilly(r):
    ta = _ta_legacy(r); sp=ta.get("sprint",0); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.30,"good_sprinter":0.45,"punchy":1.40,
         "gc_rider":1.10,"climber":1.00,"breakaway":1.60,"domestique":0.08}.get(classify(r), 0.08)
    return ((cl*0.45 + mx*0.35 + sp*0.20)**2.0) * b

def _raw_mountain(r):
    ta = _ta_legacy(r); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.05,"good_sprinter":0.07,"punchy":0.60,
         "gc_rider":1.20,"climber":1.80,"breakaway":0.80,"domestique":0.05}.get(classify(r), 0.05)
    return ((cl*0.70 + mx*0.20)**2.0) * b

def _raw_uphill(r):
    ta = _ta_legacy(r); sp=ta.get("sprint",0); cl=ta.get("climbing",0); mx=ta.get("mixed",0)
    b = {"elite_sprinter":0.20,"good_sprinter":0.30,"punchy":1.50,
         "gc_rider":1.10,"climber":1.30,"breakaway":1.20,"domestique":0.06}.get(classify(r), 0.06)
    return ((cl*0.40 + mx*0.35 + sp*0.25)**2.0) * b

def _raw_tt(r):
    return _ta_legacy(r).get("time_trial", 0)**2.0

_RAW_FN = {"flat":_raw_flat,"hilly":_raw_hilly,"mountain":_raw_mountain,
           "uphill":_raw_uphill,"tt":_raw_tt}


def make_win_probs(riders: list[dict], stage_terrain: str, finish_type: str) -> dict:
    """Legacy win prob function (raw-score based). Kept for backward compat."""
    key = FINISH_RAW.get(finish_type) or FINISH_RAW.get(stage_terrain) or "flat"
    fn  = _RAW_FN[key]
    raw = {r["rider_id"]: fn(r) for r in riders}
    total = sum(raw.values()) or 1.0
    return {rid: v/total for rid, v in raw.items()}


def rider_stage_ev_breakdown(
    rider: dict, stage_meta: dict, roadbook: dict, win_prob: float,
    stage_n: int, teammates: list[dict] | None = None,
    team_win_probs: dict | None = None, is_captain: bool = False,
) -> dict:
    """Legacy breakdown (kept for build_stage1 backward compat)."""
    finish_type = roadbook.get("finish_type", "sprint")
    stage_type  = roadbook.get("stage_type",  "flat")

    sf  = finish_ev(win_prob)
    gc  = gc_ev(rider, win_prob, stage_n, finish_type)
    jer = jersey_ev(rider, win_prob, finish_type, stage_type)

    # Sprint/KOM: use new formula if roadbook has intermediate_sprint, else old
    if "intermediate_sprint" in roadbook:
        # New single-sprint format — estimate via simple approach
        sprint_pts = sum(roadbook["intermediate_sprint"].get("points", SPRINT_POINTS))
        sk = round(win_prob * sprint_pts * POINT_VALUE * 0.12)
    else:
        # Old format fallback
        sprint_pts_old = sum(
            sum(s.get("points",[0]) for s in roadbook.get("intermediate_sprints",[]))
        )
        sk = round(win_prob * sprint_pts_old * POINT_VALUE * 0.12)

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


# ── New bulk build (Phase 3h) ─────────────────────────────────────────────────

def build_all_breakdowns(
    riders: list[dict],
    roadbooks: list[dict],
    output_dir: Path | None = None,
) -> dict[int, dict]:
    """
    Build per-rider per-stage EV breakdowns using new scenario model.

    Fix A: P(win) recomputed per stage using that stage's scenario defaults.
    Fix B: sprint_kom ≤ stage_finish × 1.5 assertion per rider.

    Output JSON per stage includes:
      stage_finish, sprint_kom, total, scenario_ev{}, scenario_p_win{}
    """
    roadbook_by_n = {r["stage"]: r for r in roadbooks}
    all_results: dict[int, dict] = {}

    for stage_n in range(1, 22):
        rb = roadbook_by_n.get(stage_n, {})
        stage_group = rb.get("stage_group", "hilly")
        default_weights = STAGE_TYPE_DEFAULTS.get(stage_group,
                                                   STAGE_TYPE_DEFAULTS["hilly"])

        stage_result: dict[str, dict] = {}
        total_sprint_ev = 0.0
        all_evs: dict[str, dict] = {}

        for r in riders:
            rid = r.get("rider_id") or str(r.get("holdet_id"))

            # Fix A: blended P(win) with this stage's default weights
            p_win = compute_blended_win_prob(r, default_weights, riders)

            sf = compute_stage_finish_ev(r, rb, p_win)
            sk = compute_sprint_ev(r, rb, p_win, riders, default_weights)

            # Fix B: assertion
            if sf > 0:
                assert sk <= sf * 1.5, (
                    f"{r['name']} Stage {stage_n}: sprint_kom ({sk:,}) "
                    f"> 1.5 × stage_finish ({sf:,})"
                )

            # Per-scenario EVs (for sliders)
            scenario_ev: dict[str, int]   = {}
            scenario_p_win: dict[str, float] = {}
            for scenario_key, weights in PURE_SCENARIOS.items():
                p_s = compute_blended_win_prob(r, weights, riders)
                ev_s = (compute_stage_finish_ev(r, rb, p_s)
                        + compute_sprint_ev(r, rb, p_s, riders, weights))
                scenario_ev[scenario_key]    = ev_s
                scenario_p_win[scenario_key] = round(p_s, 4)

            total = sf + sk
            total_sprint_ev += sk

            stage_result[rid] = {
                "name":           r["name"],
                "stage_finish":   sf,
                "sprint_kom":     sk,
                "total":          total,
                "scenario_ev":    scenario_ev,
                "scenario_p_win": scenario_p_win,
            }

        all_results[stage_n] = stage_result

        # Fix B: conservation check
        if "intermediate_sprint" in rb:
            sprint_val = sum(SPRINT_POINTS) * POINT_VALUE
            ratio = total_sprint_ev / max(sprint_val, 1)
            if not (0.5 < ratio < 1.2):
                print(f"  ⚠️  Stage {stage_n} sprint EV conservation: ratio={ratio:.2f} "
                      f"(total_sprint_ev={total_sprint_ev:,.0f}, sprint_val={sprint_val:,})")

        if output_dir:
            out = output_dir / f"ev_breakdown_stage{stage_n}.json"
            out.write_text(json.dumps(
                {"stage": stage_n, "stage_group": stage_group,
                 "default_weights": default_weights, "riders": stage_result},
                indent=2, ensure_ascii=False
            ))

    return all_results


# ── CLI ───────────────────────────────────────────────────────────────────────

def _load_all_riders(stage_n: int = 1) -> tuple[list, list]:
    riders_raw = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
    roadbooks  = json.loads((BASE / "data/stages/stage_roadbook.json").read_text())

    try:
        import yaml
        _ov_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
        _raw = yaml.safe_load(_ov_path.read_text()) or {}
        overrides = _raw.get("overrides", [])
    except Exception:
        overrides = []

    active = [
        load_rider_attributes(r, stage_n, overrides)
        for r in riders_raw
        if r.get("status") != "dns" and r.get("holdet_id")
        and not r.get("isOut", False)
    ]
    return active, roadbooks


def _run_diagnostic(stage_n: int = 1):
    active, roadbooks = _load_all_riders(stage_n)
    rb = next(r for r in roadbooks if r["stage"] == stage_n)

    print(f"\nDiagnostic — Stage {stage_n} ({rb.get('stage_group','?')})  "
          f"AFFINITY_POWER={AFFINITY_POWER}")
    print(f"Active riders: {len(active)}")

    for scenario_key in list(SCENARIO_CONFIGS.keys()):
        weights = PURE_SCENARIOS[scenario_key]
        p_wins = sorted(
            [(r["name"], compute_blended_win_prob(r, weights, active))
             for r in active if not r.get("isOut", False)],
            key=lambda x: x[1], reverse=True
        )
        total = sum(p for _, p in p_wins)
        print(f"\n  {scenario_key} — top 8 (total={total:.3f}):")
        for name, p in p_wins[:8]:
            bar = "█" * int(p * 100)
            print(f"    {name:<28} {p:5.1%}  {bar}")

    # Flat-stage sanity check for Milan
    flat_weights = STAGE_TYPE_DEFAULTS["flat"]
    milan = next((r for r in active if "Milan" in r["name"] and "Jonathan" in r["name"]), None)
    if milan and rb.get("stage_group") == "flat":
        p_bs = compute_conditional_win_prob(milan, "bunch_sprint", active)
        p_bl = compute_blended_win_prob(milan, flat_weights, active)
        print(f"\n  Milan Stage {stage_n}: P(win|bunch_sprint)={p_bs:.1%}  "
              f"P(win|blended flat)={p_bl:.1%}")
        if rb.get("stage_group") == "flat":
            if p_bs < 0.15:
                print(f"  ⚠️  Milan bunch_sprint P(win) below target (15%+) — "
                      f"increase AFFINITY_POWER (currently {AFFINITY_POWER})")
            elif p_bs > 0.50:
                print(f"  ⚠️  Milan bunch_sprint P(win) too high (>50%) — "
                      f"decrease AFFINITY_POWER (currently {AFFINITY_POWER})")
            else:
                print(f"  ✓ Milan P(win|bunch_sprint) in target range 15–50%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostic", action="store_true",
                        help="Print probability distribution and exit")
    parser.add_argument("--stage", type=int, default=1,
                        help="Stage number for diagnostic (default: 1)")
    parser.add_argument("--all-stages", action="store_true",
                        help="Regenerate all 21 stage breakdown files")
    args = parser.parse_args()

    if args.diagnostic:
        _run_diagnostic(args.stage)
    elif args.all_stages:
        active, roadbooks = _load_all_riders(1)
        out_dir = BASE / "models"
        out_dir.mkdir(exist_ok=True)
        print(f"Generating breakdowns for {len(active)} riders across 21 stages…")
        results = build_all_breakdowns(active, roadbooks, output_dir=out_dir)

        # Summary
        s1   = results[1]
        milan = next((v for k,v in s1.items() if "Milan" in v.get("name","")), None)
        if milan:
            print("\nMilan Stage 1 (new model):")
            print(f"  stage_finish:  {milan['stage_finish']:>10,} kr")
            print(f"  sprint_kom:    {milan['sprint_kom']:>10,} kr")
            print(f"  total:         {milan['total']:>10,} kr")
            print(f"  P(win|bunch_sprint):    {milan['scenario_p_win']['bunch_sprint']:.1%}")
            print(f"  EV (bunch_sprint):  {milan['scenario_ev']['bunch_sprint']:>10,} kr")

        print(f"\n✓ {len(list(out_dir.glob('ev_breakdown_stage*.json')))} stage files → {out_dir}")
    else:
        # Default: just run diagnostic for stage 1
        _run_diagnostic(1)
