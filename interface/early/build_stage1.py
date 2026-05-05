#!/usr/bin/env python3
"""Build Stage 1 Decision Dashboard for Giro 2026 — Phase 3b with EV breakdown."""

import json, os, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

from models.ev_breakdown import (
    make_win_probs, rider_stage_ev_breakdown, captain_bonus_ev,
    sprint_kom_ev, classify,
)

OUT = Path(__file__).resolve().parent / "stage1_dashboard.html"

# ── Load data ────────────────────────────────────────────────────────────────
riders_raw   = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
stages_meta  = {s["stage_number"]: s
                for s in json.loads((BASE / "data/stages/stages_giro2026.json").read_text())["stages"]}
profiles     = {p["stage"]: p
                for p in json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())}
prices_snap  = json.loads((BASE / "data/riders/prices_giro2026_stage0_pre.json").read_text())

try:
    odds_raw   = json.loads((BASE / "data/odds/odds_giro2026_stage1_T0.json").read_text())
    odds_probs = {e["rider_id"]: e["implied_probability"]
                  for e in odds_raw.get("stage_win_odds", [])
                  if e.get("implied_probability", 0) > 0}
except Exception:
    odds_probs = {}

snap_ts = prices_snap.get("timestamp", "unknown")

# ── Constants ────────────────────────────────────────────────────────────────
BUDGET       = 50_000_000
MAX_PER_TEAM = 2
DNS_IDS      = {47380, 47350}   # Germani, Conca

TYPE_LABEL = {
    "elite_sprinter": "Elite Sprinter",
    "good_sprinter":  "Good Sprinter",
    "punchy":         "Punchy",
    "climber":        "Climber",
    "gc_rider":       "GC Rider",
    "breakaway":      "Breakaway",
    "domestique":     "Domestique",
}

# ── Active riders ────────────────────────────────────────────────────────────
active_riders = [
    r for r in riders_raw
    if r.get("status") != "dns"
    and r.get("holdet_id")
    and r.get("holdet_id") not in DNS_IDS
]

# ── Win probabilities per stage ──────────────────────────────────────────────
def stage_win_probs(stage_n):
    p = profiles[stage_n]
    return make_win_probs(active_riders, p["stage_type"], p["finish_type"])

wp1 = stage_win_probs(1)
wp2 = stage_win_probs(2)
wp3 = stage_win_probs(3)

# ── Enrich riders with EV breakdown (no team_bonus at this stage — computed later) ──
def stage_ev(stage_n, wp, rider):
    p    = profiles[stage_n]
    meta = dict(p)
    meta["elevation_gain_m"] = stages_meta[stage_n].get("elevation_gain_m", 0)
    bd   = rider_stage_ev_breakdown(rider, meta, wp.get(rider["rider_id"], 0))
    return bd

enriched = []
for r in active_riders:
    rid  = r["rider_id"]
    rt   = classify(r)

    bd1  = stage_ev(1, wp1, r)
    bd2  = stage_ev(2, wp2, r)
    bd3  = stage_ev(3, wp3, r)

    ev1  = bd1["total"]
    ev2  = bd2["total"]
    ev3s = ev1 + ev2 + bd3["total"]

    cap_ev = captain_bonus_ev(bd1["stage_finish"], bd1["gc"], bd1["jersey"], bd1["sprint_kom"])

    enriched.append({
        "rider_id":     rid,
        "name":         r["name"],
        "team":         r["team"],
        "holdet_id":    r["holdet_id"],
        "price":        r.get("price", 0),
        "type":         rt,
        "type_label":   TYPE_LABEL[rt],
        "wp1":          round(wp1.get(rid, 0) * 100, 2),
        # Stage 1 breakdown
        "s1_finish":    bd1["stage_finish"],
        "s1_gc":        bd1["gc"],
        "s1_jersey":    bd1["jersey"],
        "s1_sk":        bd1["sprint_kom"],
        "ev1":          ev1,
        # Stage 2 total (breakdown stored separately)
        "ev2":          ev2,
        # Stage 3 total
        "ev3_stage":    bd3["total"],
        # 3-stage total
        "ev3s":         ev3s,
        # Captain EV (Stage 1 positive upside)
        "cap_ev":       cap_ev,
        "sort_score":   ev3s + cap_ev,
    })

enriched.sort(key=lambda x: x["sort_score"], reverse=True)

# ── Team optimisation (greedy, budget-reserve) ────────────────────────────────
def pick_team(candidates, budget=BUDGET, n=8):
    min_p = min((c["price"] for c in candidates if c.get("price", 0) > 0), default=2_500_000)
    team, team_counts, spent = [], {}, 0
    i = 0
    while len(team) < n and i < len(candidates):
        r = candidates[i]; i += 1
        slots_left = n - len(team)
        if spent + r["price"] + min_p * (slots_left - 1) > budget:
            continue
        if team_counts.get(r["team"], 0) >= MAX_PER_TEAM:
            continue
        team.append(r); spent += r["price"]
        team_counts[r["team"]] = team_counts.get(r["team"], 0) + 1
    return team, spent

recommended, total_cost = pick_team(enriched)
remaining   = BUDGET - total_cost

# ── Back-fill team_bonus into recommended team ────────────────────────────────
for r in recommended:
    rid = r["rider_id"]
    raw = next((x for x in active_riders if x["rider_id"] == rid), {})
    same_team = [t for t in recommended if t["team"] == r["team"] and t["rider_id"] != rid]
    st_wp1    = {t["rider_id"]: wp1.get(t["rider_id"], 0) for t in same_team}
    from models.ev_breakdown import team_bonus_ev as _tb
    raw_team  = [next(x for x in active_riders if x["rider_id"] == t["rider_id"]) for t in same_team]
    tb        = _tb(raw, raw_team, st_wp1)
    r["s1_team_bonus"] = tb
    r["ev1_with_tb"]   = r["ev1"] + tb

# ── Captain ───────────────────────────────────────────────────────────────────
if recommended:
    cap_idx = max(range(len(recommended)), key=lambda i: recommended[i]["cap_ev"])
    for i, r in enumerate(recommended):
        r["captain"] = (i == cap_idx)

rec_ids = {r["rider_id"] for r in recommended}
cap_id  = next((r["rider_id"] for r in recommended if r.get("captain")), None)

cap_candidates = sorted(recommended, key=lambda x: x["cap_ev"], reverse=True)[:5]

# ── Alternative teams ─────────────────────────────────────────────────────────
alt_teams = []
for pct in [0.97, 0.94]:
    alt, alt_cost = pick_team(enriched, budget=int(BUDGET * pct))
    alt_ids = {r["rider_id"] for r in alt}
    if alt and alt_ids != rec_ids:
        alt_teams.append({"team": alt, "cost": alt_cost, "budget_pct": round(pct * 100)})

# ── Odds divergence ───────────────────────────────────────────────────────────
divergences = []
for r in enriched:
    odds_p = odds_probs.get(r["rider_id"])
    if odds_p is not None:
        diff = abs(r["wp1"] - odds_p * 100)
        if diff > 10:
            divergences.append({"name": r["name"], "model_p": round(r["wp1"], 1),
                                 "odds_p": round(odds_p * 100, 1), "diff": round(diff, 1)})

# ── DNS list ──────────────────────────────────────────────────────────────────
dns_riders = [{"name": r["name"], "team": r["team"], "holdet_id": r.get("holdet_id", "—")}
              for r in riders_raw if r.get("status") == "dns"]


# ── HTML helpers ─────────────────────────────────────────────────────────────
def fmt(n):
    return f"{int(round(n)):,}".replace(",", ".") + " kr"


def rec_row(r):
    cap_mark = " ★" if r.get("captain") else ""
    cls = "captain-row" if r.get("captain") else "rec-row"
    tb = r.get("s1_team_bonus", 0)
    return f"""<tr class="{cls}">
      <td>{r['name']}{cap_mark}</td>
      <td>{r['team']}</td>
      <td>{fmt(r['price'])}</td>
      <td class="bd-finish">{fmt(r['s1_finish'])}</td>
      <td class="bd-gc">{fmt(r['s1_gc'])}</td>
      <td class="bd-jer">{fmt(r['s1_jersey'])}</td>
      <td class="bd-sk">{fmt(r['s1_sk'])}</td>
      <td class="bd-tb">{fmt(tb)}</td>
      <td class="ev-s1">{fmt(r['ev1'] + tb)}</td>
      <td>{fmt(r['ev2'])}</td>
      <td>{fmt(r['ev3_stage'])}</td>
      <td class="ev-total">{fmt(r['ev3s'])}</td>
      <td>{fmt(r['cap_ev'])}</td>
      <td>{r['type_label']}</td>
      <td>{r['wp1']}%</td>
    </tr>"""

rec_rows = "\n".join(rec_row(r) for r in recommended)

def cap_row(r, rank):
    reasons = {
        "elite_sprinter": "Elite sprinter — highest P(win) on flat Stage 1 and Stage 3 repeat.",
        "good_sprinter":  "Reliable sprinter — consistent top-5 finisher on flat stages.",
        "punchy":         "Punchy finisher — upside on hilly Stage 2, decent flat EV.",
        "gc_rider":       "GC contender — steady scoring across all three stages.",
        "breakaway":      "Breakaway specialist — high Stage 2 upside if move succeeds.",
        "climber":        "Climber — limited flat EV but strong Stage 2 breakaway chance.",
        "domestique":     "Support rider — low individual EV.",
    }
    return f"""<tr>
      <td>#{rank}</td><td><strong>{r['name']}</strong></td><td>{r['team']}</td>
      <td>{fmt(r['price'])}</td><td>{r['type_label']}</td>
      <td>{fmt(r['cap_ev'])}</td><td>{reasons.get(r['type'], '')}</td>
    </tr>"""

cap_rows  = "\n".join(cap_row(r, i + 1) for i, r in enumerate(cap_candidates))
dns_rows  = "\n".join(
    f"<tr class='dns-row'><td>{d['name']}</td><td>{d['team']}</td>"
    f"<td>{d['holdet_id']}</td><td>DNS — EXCLUDED</td></tr>"
    for d in dns_riders)

alt_html = ""
for i, a in enumerate(alt_teams):
    rows = "\n".join(
        f"<tr><td>{r['name']}</td><td>{r['team']}</td><td>{fmt(r['price'])}</td>"
        f"<td>{fmt(r['ev3s'])}</td><td>{r['type_label']}</td></tr>"
        for r in a["team"])
    alt_html += f"""<details>
      <summary>Alternative #{i+1} — budget cap {a['budget_pct']}% (cost: {fmt(a['cost'])})</summary>
      <table class="ev-table"><thead><tr>
        <th>Rider</th><th>Team</th><th>Price</th><th>3-Stage EV</th><th>Type</th>
      </tr></thead><tbody>{rows}</tbody></table>
    </details>"""

odds_section = (
    f"""<table class="ev-table"><thead>
      <tr><th>Rider</th><th>Model P(win)</th><th>Odds P(win)</th><th>Divergence</th></tr>
    </thead><tbody>""" +
    "\n".join(f"<tr class='flag-row'><td>{d['name']}</td><td>{d['model_p']}%</td>"
              f"<td>{d['odds_p']}%</td><td>{d['diff']} pp — REVIEW</td></tr>"
              for d in divergences) +
    "</tbody></table>"
    if divergences else
    '<p class="muted">No real odds data available — odds file is a template. '
    'Run <code>odds_snapshot.py</code> before stage start.</p>'
)

riders_js = json.dumps(enriched, ensure_ascii=False)

# ── Relative path to stage image from the HTML file ──────────────────────────
stage1_img_rel = "../../data/stage_images/stage-1.jpg"

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stage 1 Decision Dashboard — Giro 2026</title>
<style>
  :root {{
    --bg:#0d1117; --surface:#161b22; --border:#30363d;
    --text:#c9d1d9; --muted:#8b949e;
    --green:#238636; --green-hi:#2ea043;
    --gold:#d4a017; --gold-hi:#e3b341;
    --red:#da3633; --red-hi:#f85149;
    --blue:#1f6feb; --blue-hi:#388bfd;
    --warn:#9e6a03; --warn-bg:#2d1b00;
    --purple:#8957e5;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",monospace;
       background:var(--bg);color:var(--text);font-size:14px;line-height:1.5}}
  .container{{max-width:1400px;margin:0 auto;padding:20px}}
  h1{{font-size:1.6rem;color:#e6edf3;margin-bottom:4px}}
  h2{{font-size:1.05rem;color:var(--blue-hi);margin:24px 0 10px;
      border-bottom:1px solid var(--border);padding-bottom:6px}}
  h3{{font-size:.9rem;color:var(--muted);margin-bottom:8px}}
  .subtitle{{color:var(--muted);font-size:.9rem;margin-bottom:16px}}
  .warning-banner{{
    background:var(--warn-bg);border:1px solid var(--warn);
    border-radius:6px;padding:12px 16px;margin:16px 0;
    color:#f0a030;font-weight:600;font-size:1rem}}
  .budget-bar{{display:flex;gap:24px;padding:12px 16px;
    background:var(--surface);border:1px solid var(--border);
    border-radius:6px;margin-bottom:16px;flex-wrap:wrap}}
  .budget-bar span{{color:var(--muted)}}
  .budget-bar strong{{color:var(--green-hi)}}
  /* Stage image */
  .stage-profile{{margin:12px 0}}
  .stage-profile img{{width:100%;max-width:1050px;border-radius:6px;
                      border:1px solid var(--border)}}
  .stage-meta{{display:flex;gap:20px;margin-top:6px;flex-wrap:wrap}}
  .stage-meta span{{background:var(--surface);border:1px solid var(--border);
    border-radius:4px;padding:3px 10px;font-size:12px;color:var(--muted)}}
  /* Tables */
  table.ev-table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:8px;overflow-x:auto}}
  .ev-table th{{background:var(--surface);color:var(--muted);
    padding:7px 8px;text-align:left;font-weight:600;
    border-bottom:1px solid var(--border);white-space:nowrap;
    cursor:pointer;user-select:none}}
  .ev-table th:hover{{color:var(--blue-hi)}}
  .ev-table th.sorted-asc::after{{content:" ▲";color:var(--blue-hi)}}
  .ev-table th.sorted-desc::after{{content:" ▼";color:var(--blue-hi)}}
  .ev-table td{{padding:6px 8px;border-bottom:1px solid var(--border)}}
  .ev-table tr:hover td{{background:#1c2128}}
  .rec-row td{{background:#0f2d16}}
  .rec-row:hover td{{background:#173020}}
  .captain-row td{{background:#2d2000 !important;color:var(--gold-hi)}}
  .captain-row:hover td{{background:#3a2a00 !important}}
  .dns-row td{{color:var(--red);opacity:.7}}
  .flag-row td{{color:var(--warn)}}
  .ev-total{{font-weight:700;color:var(--green-hi)}}
  .ev-s1{{font-weight:600;color:#79c0ff}}
  /* Breakdown column colours */
  .bd-finish{{color:#58a6ff}}
  .bd-gc{{color:var(--gold-hi)}}
  .bd-jer{{color:#d2a8ff}}
  .bd-sk{{color:var(--green-hi)}}
  .bd-tb{{color:#f78166}}
  .badge{{display:inline-block;font-size:11px;padding:2px 7px;
    border-radius:10px;font-weight:600;white-space:nowrap}}
  .badge-sprint{{background:#1a3050;color:#58a6ff}}
  .badge-gc{{background:#2d1b00;color:var(--gold-hi)}}
  .badge-break{{background:#1a2d1a;color:var(--green-hi)}}
  .badge-punchy{{background:#2d1a2d;color:#d2a8ff}}
  .badge-dom{{background:#1c2128;color:var(--muted)}}
  .muted{{color:var(--muted);font-style:italic}}
  .prob-callout{{
    background:#1a1a2d;border:1px solid #5a3e7a;
    border-radius:6px;padding:12px 16px;margin:8px 0;
    color:#c9a0ff;font-size:13px;line-height:1.7}}
  .prob-callout strong{{color:#d2a8ff}}
  .stage2-warn{{
    background:#1a1a2d;border:1px solid #3d3d8a;
    border-radius:6px;padding:12px 16px;margin:8px 0;color:#8888cc}}
  .section{{margin-bottom:32px}}
  .filter-row{{display:flex;gap:10px;margin-bottom:8px;align-items:center;flex-wrap:wrap}}
  .search-bar{{flex:1;min-width:200px;padding:7px 12px;background:var(--surface);
    border:1px solid var(--border);color:var(--text);
    border-radius:6px;font-size:13px}}
  .search-bar:focus{{outline:none;border-color:var(--blue)}}
  select#type-filter{{padding:6px 10px;background:var(--surface);
    border:1px solid var(--border);color:var(--text);
    border-radius:6px;font-size:13px;cursor:pointer}}
  details{{margin:8px 0}}
  summary{{cursor:pointer;color:var(--blue-hi);padding:6px;
    background:var(--surface);border-radius:4px}}
  summary:hover{{color:#58a6ff}}
  code{{background:var(--surface);padding:2px 6px;border-radius:4px;font-size:12px}}
  .transfer-box{{background:var(--surface);border:1px solid var(--border);
    border-radius:6px;padding:14px}}
  .footer{{border-top:1px solid var(--border);padding-top:16px;
    color:var(--muted);font-size:12px;margin-top:32px}}
  #table-count{{color:var(--muted);font-size:12px;margin-top:4px}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<h1>Stage 1 Decision Dashboard — Giro d'Italia 2026</h1>
<p class="subtitle">
  Nessebar → Burgas &nbsp;|&nbsp; 156 km &nbsp;|&nbsp; Flat sprint &nbsp;|&nbsp;
  <strong>May 8 17:00</strong> &nbsp;|&nbsp; Trading window ~20:30
</p>

<div class="warning-banner">
  ⚠ Team is EMPTY — submit selection at holdet.dk before 17:00 on May 8
  &nbsp;|&nbsp; Initial selection is FREE (no transfer fees)
</div>

<div class="budget-bar">
  <div><span>Budget: </span><strong>{fmt(BUDGET)}</strong></div>
  <div><span>Team cost: </span><strong>{fmt(total_cost)}</strong></div>
  <div><span>Remaining: </span>
    <strong style="color:{'#2ea043' if remaining > 2_000_000 else '#f85149'}">{fmt(remaining)}</strong>
  </div>
  <div><span>Tier: </span><strong>Gold</strong></div>
</div>

<!-- Stage profile image -->
<div class="section">
  <h2>Stage 1 Profile</h2>
  <div class="stage-profile">
    <img src="{stage1_img_rel}" alt="Stage 1 profile — Nessebar to Burgas" />
    <div class="stage-meta">
      <span>Type: Flat</span>
      <span>Sprints: 1 intermediate (km 72)</span>
      <span>KOMs: 0</span>
      <span>Finish: Bunch sprint</span>
      <span>Source: stage_profiles_parsed.json (image-parsed)</span>
    </div>
  </div>
</div>

<!-- Section 1: Recommended Team with breakdown -->
<div class="section">
  <h2>§1 — Recommended Team (8 Riders)</h2>
  <p class="muted" style="margin-bottom:10px;">
    ★ = captain &nbsp;|&nbsp; Green = recommended &nbsp;|&nbsp; Gold = captain pick
    &nbsp;|&nbsp; EV columns: <span class="bd-finish">Finish</span>
    / <span class="bd-gc">GC</span>
    / <span class="bd-jer">Jersey</span>
    / <span class="bd-sk">Sprint/KOM</span>
    / <span class="bd-tb">Team Bonus</span>
  </p>
  <div style="overflow-x:auto">
  <table class="ev-table">
    <thead><tr>
      <th>Rider</th><th>Team</th><th>Price</th>
      <th class="bd-finish">S1 Finish</th>
      <th class="bd-gc">S1 GC</th>
      <th class="bd-jer">S1 Jersey</th>
      <th class="bd-sk">S1 Spr/KOM</th>
      <th class="bd-tb">S1 Team Bonus</th>
      <th class="ev-s1">S1 Total</th>
      <th>S2 EV</th>
      <th>S3 EV</th>
      <th>3-Stage EV</th>
      <th>Captain EV</th>
      <th>Type</th>
      <th>P(win S1)</th>
    </tr></thead>
    <tbody>{rec_rows}</tbody>
  </table>
  </div>
  <p style="margin-top:6px;font-size:12px;color:var(--muted);">
    Captain EV = 0.6 × (S1 stage_finish + gc + jersey + sprint_kom) — positive upside of doubling.
    Team Bonus = expected kr from same-team riders finishing top 3.
  </p>
</div>

<!-- Probability assumption callout — governance requirement -->
<div class="prob-callout">
  <strong>⚠️ Probability model: rule-based baseline (Phase 3a/3b)</strong><br>
  Win probability for each stage is derived from <code>terrain_affinity</code> (Layer 0 rider attributes) only.<br>
  Sprint/KOM point EV is estimated from stage profile image parsing (<code>stage_profiles_parsed.json</code>).<br>
  Calibration constants: sprint = 0.15 × affinity × pts, KOM = 0.10 × affinity × pts — placeholder estimates.<br>
  <strong>These are structural estimates, not trained model outputs.</strong>
  Replace in Phase 4 with trained StageFinishPosition model.
</div>

<!-- Section 2: Full EV Table (sortable, filterable) -->
<div class="section">
  <h2>§2 — Full EV Table (All Active Riders)</h2>
  <div class="filter-row">
    <input class="search-bar" id="search" placeholder="Search rider or team…" />
    <select id="type-filter">
      <option value="">All types</option>
      <option value="elite_sprinter">Elite Sprinter</option>
      <option value="good_sprinter">Good Sprinter</option>
      <option value="punchy">Punchy</option>
      <option value="gc_rider">GC Rider</option>
      <option value="climber">Climber</option>
      <option value="breakaway">Breakaway</option>
      <option value="domestique">Domestique</option>
    </select>
  </div>
  <div style="overflow-x:auto">
  <table class="ev-table" id="full-table">
    <thead><tr>
      <th data-col="name">Rider</th>
      <th data-col="team">Team</th>
      <th data-col="price">Price</th>
      <th data-col="s1_finish" class="bd-finish">S1 Finish</th>
      <th data-col="s1_gc" class="bd-gc">S1 GC</th>
      <th data-col="s1_jersey" class="bd-jer">S1 Jersey</th>
      <th data-col="s1_sk" class="bd-sk">S1 Spr/KOM</th>
      <th data-col="ev1" class="ev-s1">S1 Total</th>
      <th data-col="ev2">S2 EV</th>
      <th data-col="ev3_stage">S3 EV</th>
      <th data-col="ev3s" class="sorted-desc">3-Stage EV</th>
      <th data-col="cap_ev">Captain EV</th>
      <th data-col="type_label">Type</th>
      <th data-col="wp1">P(win S1)%</th>
    </tr></thead>
    <tbody id="full-table-body"></tbody>
  </table>
  </div>
  <p id="table-count"></p>
</div>

<!-- Section 3: Captain Recommendation -->
<div class="section">
  <h2>§3 — Captain Recommendation</h2>
  <p class="muted" style="margin-bottom:10px;">Top 5 candidates from recommended team</p>
  <table class="ev-table">
    <thead><tr>
      <th>#</th><th>Rider</th><th>Team</th><th>Price</th>
      <th>Type</th><th>Captain EV</th><th>Rationale</th>
    </tr></thead>
    <tbody>{cap_rows}</tbody>
  </table>
</div>

<!-- Section 4: Stage 2 Warning -->
<div class="section">
  <h2>§4 — Stage 2 Warning</h2>
  <div class="stage2-warn">
    <strong>Stage 2 is HILLY (219 km, +2800 m) — sprinter EV drops sharply.</strong><br>
    Three KOM climbs (Cat 3 + Cat 2 + Cat 2). Finishes with descent into Veliko Tarnovo.
    Verify sprinters earn their place across Stage 1 and Stage 3 combined.
    Breakaway and punchy riders have the highest Stage 2 EV.
  </div>
  <table class="ev-table" style="margin-top:10px">
    <thead><tr><th>Stage</th><th>Route</th><th>Km</th><th>Type</th><th>Sprints</th><th>KOMs</th><th>Finish</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>Nessebar → Burgas</td><td>156</td><td>Flat</td><td>1</td><td>0</td><td>Bunch sprint</td></tr>
      <tr><td>2</td><td>Burgas → Veliko Tarnovo</td><td>219</td><td>Hilly</td><td>1</td><td>3</td><td>Puncheur/break</td></tr>
      <tr><td>3</td><td>Plovdiv → Sofia</td><td>176</td><td>Hilly</td><td>1</td><td>1 (Cat 2)</td><td>Sprint</td></tr>
    </tbody>
  </table>
</div>

<!-- Section 5: Odds Divergence -->
<div class="section">
  <h2>§5 — Odds Divergence Analysis</h2>
  {odds_section}
</div>

<!-- Section 6: DNS Riders -->
<div class="section">
  <h2>§6 — DNS Riders (Excluded)</h2>
  <table class="ev-table">
    <thead><tr><th>Rider</th><th>Team</th><th>holdet_id</th><th>Status</th></tr></thead>
    <tbody>{dns_rows}</tbody>
  </table>
</div>

<!-- Section 7: Alternative Teams -->
<div class="section">
  <h2>§7 — Alternative Team Compositions</h2>
  {alt_html or '<p class="muted">No alternative teams computed.</p>'}
</div>

<!-- Section 8: Transfer Cost Formula -->
<div class="section">
  <h2>§8 — Transfer Cost Formula (Future Reference)</h2>
  <div class="transfer-box">
    <p style="font-family:monospace;color:#79c0ff;white-space:pre-wrap;">Net EV(transfer) =
  EV(rider_in,  stages t→t+n)
− EV(rider_out, stages t→t+n)
− transfer_fee_in  (1% of buy price)
− transfer_fee_out (1% of sell price at exit)   ← critical, often missed</p>
    <p style="margin-top:8px;color:var(--muted);font-size:12px;">
      Stage 1 initial selection is FREE. Fees apply from Stage 2 onwards.
    </p>
  </div>
</div>

<div class="footer">
  <p>Snapshot: {snap_ts} &nbsp;|&nbsp; Rule-based baseline — no ML model</p>
  <p style="margin-top:4px;">Submit team at <strong>holdet.dk</strong> before 17:00 May 8</p>
</div>
</div>

<script>
const ALL_RIDERS = {riders_js};
const REC_IDS   = new Set({json.dumps(list(rec_ids))});
const CAP_ID    = {json.dumps(cap_id)};

let sortCol  = "ev3s";
let sortDesc = true;
let filterText = "";
let filterType = "";

function fmt(n) {{
  return Math.round(n).toLocaleString("da-DK") + " kr";
}}
function badge(type) {{
  const cls = {{
    "elite_sprinter":"badge-sprint","good_sprinter":"badge-sprint",
    "punchy":"badge-punchy","gc_rider":"badge-gc","climber":"badge-gc",
    "breakaway":"badge-break","domestique":"badge-dom",
  }}[type] || "badge-dom";
  return `<span class="badge ${{cls}}">${{type}}</span>`;
}}

function renderTable() {{
  let rows = ALL_RIDERS.slice();
  if (filterText) {{
    const q = filterText.toLowerCase();
    rows = rows.filter(r => r.name.toLowerCase().includes(q) || r.team.toLowerCase().includes(q));
  }}
  if (filterType) {{
    rows = rows.filter(r => r.type === filterType);
  }}
  rows.sort((a, b) => {{
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === "string") {{ va = va.toLowerCase(); vb = vb.toLowerCase(); }}
    return sortDesc ? (vb > va ? 1 : -1) : (va > vb ? 1 : -1);
  }});

  const tbody = document.getElementById("full-table-body");
  tbody.innerHTML = rows.map(r => {{
    const isRec = REC_IDS.has(r.rider_id);
    const isCap = r.rider_id === CAP_ID;
    const cls   = isCap ? "captain-row" : (isRec ? "rec-row" : "");
    return `<tr class="${{cls}}">
      <td>${{r.name}}${{isCap ? " ★" : ""}}</td>
      <td>${{r.team}}</td>
      <td>${{fmt(r.price)}}</td>
      <td class="bd-finish">${{fmt(r.s1_finish)}}</td>
      <td class="bd-gc">${{fmt(r.s1_gc)}}</td>
      <td class="bd-jer">${{fmt(r.s1_jersey)}}</td>
      <td class="bd-sk">${{fmt(r.s1_sk)}}</td>
      <td class="ev-s1">${{fmt(r.ev1)}}</td>
      <td>${{fmt(r.ev2)}}</td>
      <td>${{fmt(r.ev3_stage)}}</td>
      <td class="ev-total">${{fmt(r.ev3s)}}</td>
      <td>${{fmt(r.cap_ev)}}</td>
      <td>${{badge(r.type)}}</td>
      <td>${{r.wp1}}%</td>
    </tr>`;
  }}).join("");

  document.getElementById("table-count").textContent =
    `Showing ${{rows.length}} of ${{ALL_RIDERS.length}} active riders`;
}}

document.querySelectorAll("#full-table th[data-col]").forEach(th => {{
  th.addEventListener("click", () => {{
    if (sortCol === th.dataset.col) {{ sortDesc = !sortDesc; }}
    else {{ sortCol = th.dataset.col; sortDesc = true; }}
    document.querySelectorAll("#full-table th").forEach(t =>
      t.classList.remove("sorted-asc", "sorted-desc"));
    th.classList.add(sortDesc ? "sorted-desc" : "sorted-asc");
    renderTable();
  }});
}});

document.getElementById("search").addEventListener("input", e => {{
  filterText = e.target.value; renderTable();
}});
document.getElementById("type-filter").addEventListener("change", e => {{
  filterType = e.target.value; renderTable();
}});

renderTable();
</script>
</body>
</html>"""

OUT.write_text(html, encoding="utf-8")

print(f"✓ Dashboard → {OUT}")
print(f"\nRecommended team ({fmt(total_cost)} / {fmt(BUDGET)}):")
for r in recommended:
    cap  = " ★ CAPTAIN" if r.get("captain") else ""
    tb   = r.get("s1_team_bonus", 0)
    print(f"  {r['name']:<35} {r['team']:<30} {fmt(r['price']):>15}"
          f"  S1:{fmt(r['ev1']+tb)}  3S:{fmt(r['ev3s'])}{cap}")
print(f"\nRemaining: {fmt(remaining)}")
print(f"Captain: {next((r['name'] for r in recommended if r.get('captain')), 'None')}")
