#!/usr/bin/env python3
"""Build Stage 1 Decision Dashboard for Giro 2026."""

import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage1_dashboard.html")

# ── Load data ────────────────────────────────────────────────────────────────
riders_raw  = json.load(open(f"{BASE}/data/riders/riders_giro2026_v1.json"))["riders"]
stages_all  = json.load(open(f"{BASE}/data/stages/stages_giro2026.json"))["stages"]
prices_snap = json.load(open(f"{BASE}/data/riders/prices_giro2026_stage0_pre.json"))

# Odds — template-only, so treat as empty
try:
    odds_raw = json.load(open(f"{BASE}/data/odds/odds_giro2026_stage1_T0.json"))
    odds_probs = {
        e["rider_id"]: e["implied_probability"]
        for e in odds_raw.get("stage_win_odds", [])
        if e.get("implied_probability", 0) > 0
    }
except Exception:
    odds_probs = {}

stages = {s["stage_number"]: s for s in stages_all}
snap_ts = prices_snap.get("timestamp", "unknown")

# ── Constants ────────────────────────────────────────────────────────────────
BUDGET      = 50_000_000
MAX_PER_TEAM = 2
DNS_IDS     = {47380, 47350}   # Germani, Conca

STAGE_PAYOFFS = [200_000, 150_000, 130_000, 120_000, 110_000,
                 100_000,  95_000,  90_000,  85_000,  80_000,
                  70_000,  55_000,  40_000,  30_000,  15_000]

GC_PAYOFFS = [100_000, 90_000, 80_000, 70_000, 60_000,
               50_000, 40_000, 30_000, 20_000, 10_000]

# Geometric placement weights (empirically tuned for ~2x win_prob -> EV multiplier)
WEIGHTS = [1.00, 0.72, 0.57, 0.46, 0.38,
           0.33, 0.28, 0.25, 0.22, 0.20,
           0.18, 0.15, 0.12, 0.10, 0.08]


# ── Rider classification ─────────────────────────────────────────────────────
def classify(r):
    ta  = r.get("terrain_affinity", {})
    cp  = r.get("consistency_profile", {})
    sp  = ta.get("sprint",   0)
    cl  = ta.get("climbing", 0)
    rel = cp.get("reliability", "medium")
    if sp >= 0.80:                        return "elite_sprinter"
    if sp >= 0.60:                        return "good_sprinter"
    if sp >= 0.40 and cl >= 0.50:         return "punchy"
    if cl >= 0.80:                        return "climber"
    if cl >= 0.70:                        return "gc_rider"
    if rel == "high" and sp < 0.60:       return "breakaway"
    return "domestique"

TYPE_LABEL = {
    "elite_sprinter": "Elite Sprinter",
    "good_sprinter":  "Good Sprinter",
    "punchy":         "Punchy",
    "climber":        "Climber",
    "gc_rider":       "GC Rider",
    "breakaway":      "Breakaway",
    "domestique":     "Domestique",
}


# ── Stage win probability ────────────────────────────────────────────────────
def raw_score_flat(r):
    """Raw score proportional to sprint power on a flat stage."""
    ta = r.get("terrain_affinity", {})
    sp = ta.get("sprint", 0)
    rt = classify(r)
    boost = {
        "elite_sprinter": 2.0,
        "good_sprinter":  1.2,
        "punchy":         0.45,
        "gc_rider":       0.10,
        "climber":        0.06,
        "breakaway":      0.30,
        "domestique":     0.04,
    }.get(rt, 0.04)
    return (sp ** 2.0) * boost

def raw_score_hilly(r):
    """Raw score for a hilly puncheur/breakaway stage."""
    ta = r.get("terrain_affinity", {})
    sp = ta.get("sprint",   0)
    cl = ta.get("climbing", 0)
    mx = ta.get("mixed",    0)
    rt = classify(r)
    boost = {
        "elite_sprinter": 0.30,
        "good_sprinter":  0.45,
        "punchy":         1.40,
        "gc_rider":       1.10,
        "climber":        1.00,
        "breakaway":      1.60,
        "domestique":     0.08,
    }.get(rt, 0.08)
    score = (cl * 0.45 + mx * 0.35 + sp * 0.20) ** 2.0
    return score * boost


def make_win_probs(riders_active, stage_terrain):
    """Return dict[rider_id -> win_prob], normalised to sum=1."""
    fn = raw_score_flat if stage_terrain == "flat" else raw_score_hilly
    raw = {r["rider_id"]: fn(r) for r in riders_active}
    total = sum(raw.values()) or 1.0
    return {rid: v / total for rid, v in raw.items()}


# ── EV computation ───────────────────────────────────────────────────────────
def finish_ev(win_prob):
    return win_prob * sum(w * p for w, p in zip(WEIGHTS, STAGE_PAYOFFS))

def gc_ev_bonus(win_prob, rtype):
    """Small GC bonus for gc/climber riders every stage."""
    if rtype not in ("gc_rider", "climber"):
        return 0
    # Roughly 5× the stage win prob maps to GC position probability (top 10)
    gc_win_prob = win_prob * 5
    return gc_win_prob * sum(w * p for w, p in zip(WEIGHTS[:10], GC_PAYOFFS))

def sprint_bonus(r, stage):
    n = len(stage.get("sprint_locations", []))
    sp = r.get("terrain_affinity", {}).get("sprint", 0)
    return sp * n * 3_000

def kom_bonus(r, stage):
    n = len(stage.get("kom_locations", []))
    cl = r.get("terrain_affinity", {}).get("climbing", 0)
    return cl * n * 2_000

def compute_ev_for_stage(rider, win_prob, stage):
    rt = classify(rider)
    ev  = finish_ev(win_prob)
    ev += gc_ev_bonus(win_prob, rt)
    ev += sprint_bonus(rider, stage)
    ev += kom_bonus(rider, stage)
    return round(ev)


# ── Main processing ──────────────────────────────────────────────────────────
active_riders = [
    r for r in riders_raw
    if r.get("status") != "dns"
    and r.get("holdet_id")
    and r.get("holdet_id") not in DNS_IDS
]

win_probs_s1 = make_win_probs(active_riders, stages[1]["terrain_classification"])
win_probs_s2 = make_win_probs(active_riders, stages[2]["terrain_classification"])
win_probs_s3 = make_win_probs(active_riders, stages[3]["terrain_classification"])

enriched = []
for r in active_riders:
    rid  = r["rider_id"]
    rt   = classify(r)
    wp1  = win_probs_s1.get(rid, 0)
    wp2  = win_probs_s2.get(rid, 0)
    wp3  = win_probs_s3.get(rid, 0)

    ev1  = compute_ev_for_stage(r, wp1, stages[1])
    ev2  = compute_ev_for_stage(r, wp2, stages[2])
    ev3  = compute_ev_for_stage(r, wp3, stages[3])
    ev3s = ev1 + ev2 + ev3

    # Captain EV = 0.6 * stage1_ev (positive upside of doubling)
    cap_ev = round(0.6 * ev1)

    enriched.append({
        "rider_id":  rid,
        "name":      r["name"],
        "team":      r["team"],
        "holdet_id": r["holdet_id"],
        "price":     r.get("price", 0),
        "type":      rt,
        "type_label": TYPE_LABEL[rt],
        "wp1":       round(wp1 * 100, 2),
        "ev1":       ev1,
        "ev2":       ev2,
        "ev3_stage": ev3,
        "ev3s":      ev3s,
        "cap_ev":    cap_ev,
        "sort_score": ev3s + cap_ev,
    })

enriched.sort(key=lambda x: x["sort_score"], reverse=True)

# ── Team optimisation (greedy) ───────────────────────────────────────────────
def pick_team(candidates, budget=BUDGET, n=8):
    min_price = min((c["price"] for c in candidates if c.get("price", 0) > 0), default=2_500_000)
    team = []
    team_counts = {}
    spent = 0
    remaining_candidates = list(candidates)
    i = 0
    while len(team) < n and i < len(remaining_candidates):
        r = remaining_candidates[i]
        i += 1
        slots_left = n - len(team)
        # Reserve min_price per remaining slot (excluding this pick)
        budget_reserve = min_price * (slots_left - 1)
        if spent + r["price"] + budget_reserve > budget:
            continue
        tc = team_counts.get(r["team"], 0)
        if tc >= MAX_PER_TEAM:
            continue
        team.append(r)
        spent += r["price"]
        team_counts[r["team"]] = tc + 1
    return team, spent

recommended, total_cost = pick_team(enriched)
remaining_budget = BUDGET - total_cost

# Mark captain (highest cap_ev in recommended team)
if recommended:
    cap_idx = max(range(len(recommended)), key=lambda i: recommended[i]["cap_ev"])
    for i, r in enumerate(recommended):
        r["captain"] = (i == cap_idx)

rec_ids = {r["rider_id"] for r in recommended}
cap_id  = next((r["rider_id"] for r in recommended if r.get("captain")), None)

# Top-5 captain candidates within recommended team
cap_candidates = sorted(recommended, key=lambda x: x["cap_ev"], reverse=True)[:5]

# Alternative teams (shift budget down slightly)
alt_teams = []
for budget_pct in [0.97, 0.94, 0.91]:
    alt, alt_cost = pick_team(enriched, budget=int(BUDGET * budget_pct))
    if alt and alt != recommended:
        alt_teams.append({"team": alt, "cost": alt_cost, "budget_pct": round(budget_pct*100)})

# Odds divergence
divergences = []
for r in enriched:
    model_p = r["wp1"]
    odds_p  = odds_probs.get(r["rider_id"], None)
    if odds_p is not None:
        diff = abs(model_p - odds_p * 100)
        if diff > 10:
            divergences.append({
                "name":    r["name"],
                "model_p": round(model_p, 1),
                "odds_p":  round(odds_p * 100, 1),
                "diff":    round(diff, 1),
            })

# DNS list for display
dns_riders = [
    {"name": r["name"], "team": r["team"], "holdet_id": r.get("holdet_id", "—")}
    for r in riders_raw
    if r.get("status") == "dns"
]


# ── HTML generation ──────────────────────────────────────────────────────────
def fmt_kr(n):
    return f"{n:,.0f} kr".replace(",", ".")

def pct(p):
    return f"{p:.1f}%"


def table_row_rec(r):
    cap_mark = " ★" if r.get("captain") else ""
    price_str = fmt_kr(r["price"])
    return f"""<tr class="rec-row{'captain-row' if r.get('captain') else ''}">
      <td>{r['name']}{cap_mark}</td>
      <td>{r['team']}</td>
      <td>{price_str}</td>
      <td>{fmt_kr(r['ev1'])}</td>
      <td>{fmt_kr(r['ev2'])}</td>
      <td>{fmt_kr(r['ev3_stage'])}</td>
      <td class="ev-total">{fmt_kr(r['ev3s'])}</td>
      <td>{fmt_kr(r['cap_ev'])}</td>
      <td>{r['type_label']}</td>
      <td>{pct(r['wp1'])}</td>
    </tr>"""

rec_rows = "\n".join(table_row_rec(r) for r in recommended)

# Serialize all enriched riders to JS
riders_js = json.dumps(enriched, ensure_ascii=False)

# Captain candidate rows
def cap_row(r, rank):
    reasons = {
        "elite_sprinter": "Elite sprinter — high P(win) on flat opener and Stage 3 repeat.",
        "good_sprinter":   "Reliable sprinter — consistent top-5 finisher on flat stages.",
        "punchy":          "Punchy finisher — upside on hilly Stage 2, decent flat EV.",
        "gc_rider":        "GC contender — steady scoring across all three stages.",
        "breakaway":       "Breakaway specialist — high Stage 2 upside if move succeeds.",
        "climber":         "Climber — limited flat EV but strong Stage 2 breakaway chance.",
        "domestique":      "Support rider — low individual EV, best as budget filler.",
    }
    reason = reasons.get(r["type"], "")
    return f"""<tr>
      <td>#{rank}</td>
      <td><strong>{r['name']}</strong></td>
      <td>{r['team']}</td>
      <td>{fmt_kr(r['price'])}</td>
      <td>{r['type_label']}</td>
      <td>{fmt_kr(r['cap_ev'])}</td>
      <td>{reason}</td>
    </tr>"""

cap_rows = "\n".join(cap_row(r, i+1) for i, r in enumerate(cap_candidates))

# Odds section
if divergences:
    odd_rows = "\n".join(
        f"<tr class='flag-row'><td>{d['name']}</td><td>{d['model_p']}%</td>"
        f"<td>{d['odds_p']}%</td><td>{d['diff']} pp — REVIEW</td></tr>"
        for d in divergences
    )
    odds_section = f"""<table class="ev-table">
      <thead><tr><th>Rider</th><th>Model P(win)</th><th>Odds P(win)</th><th>Divergence</th></tr></thead>
      <tbody>{odd_rows}</tbody>
    </table>"""
else:
    odds_section = """<p class="muted">No real odds data available — odds file is a template.
    Run <code>odds_snapshot.py</code> before stage start to populate divergence analysis.</p>"""

# DNS table
dns_rows = "\n".join(
    f"<tr class='dns-row'><td>{d['name']}</td><td>{d['team']}</td>"
    f"<td>{d['holdet_id']}</td><td>DNS — EXCLUDED</td></tr>"
    for d in dns_riders
)

# Alt team sections
alt_html = ""
for i, a in enumerate(alt_teams):
    rows = "\n".join(
        f"<tr><td>{r['name']}</td><td>{r['team']}</td><td>{fmt_kr(r['price'])}</td>"
        f"<td>{fmt_kr(r['ev3s'])}</td><td>{r['type_label']}</td></tr>"
        for r in a["team"]
    )
    alt_html += f"""
    <details>
      <summary>Alternative #{i+1} — budget cap {a['budget_pct']}%
        (cost: {fmt_kr(a['cost'])})</summary>
      <table class="ev-table">
        <thead><tr><th>Rider</th><th>Team</th><th>Price</th><th>3-Stage EV</th><th>Type</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </details>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stage 1 Decision Dashboard — Giro 2026</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #c9d1d9; --muted: #8b949e;
    --green: #238636; --green-hi: #2ea043;
    --gold: #d4a017; --gold-hi: #e3b341;
    --red: #da3633; --red-hi: #f85149;
    --blue: #1f6feb; --blue-hi: #388bfd;
    --warn: #9e6a03; --warn-bg: #2d1b00;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace;
         background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.5; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 1.6rem; color: #e6edf3; margin-bottom: 4px; }}
  h2 {{ font-size: 1.1rem; color: var(--blue-hi); margin: 24px 0 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  h3 {{ font-size: 0.95rem; color: var(--muted); margin-bottom: 8px; }}
  .subtitle {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 16px; }}
  .warning-banner {{
    background: var(--warn-bg); border: 1px solid var(--warn);
    border-radius: 6px; padding: 12px 16px; margin: 16px 0;
    color: #f0a030; font-weight: 600; font-size: 1rem;
  }}
  .budget-bar {{
    display: flex; gap: 24px; padding: 12px 16px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; margin-bottom: 16px;
  }}
  .budget-bar span {{ color: var(--muted); }}
  .budget-bar strong {{ color: var(--green-hi); }}
  table.ev-table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
    margin-bottom: 8px;
  }}
  .ev-table th {{
    background: var(--surface); color: var(--muted);
    padding: 8px 10px; text-align: left; font-weight: 600;
    border-bottom: 1px solid var(--border); white-space: nowrap;
    cursor: pointer; user-select: none;
  }}
  .ev-table th:hover {{ color: var(--blue-hi); }}
  .ev-table th.sorted-asc::after  {{ content: " ▲"; color: var(--blue-hi); }}
  .ev-table th.sorted-desc::after {{ content: " ▼"; color: var(--blue-hi); }}
  .ev-table td {{
    padding: 7px 10px; border-bottom: 1px solid var(--border);
  }}
  .ev-table tr:hover td {{ background: #1c2128; }}
  .rec-row td   {{ background: #0f2d16; }}
  .rec-row:hover td {{ background: #173020; }}
  .captain-row td {{ background: #2d2000 !important; color: var(--gold-hi); }}
  .captain-row:hover td {{ background: #3a2a00 !important; }}
  .dns-row td   {{ color: var(--red); opacity: 0.7; }}
  .flag-row td  {{ color: var(--warn); }}
  .ev-total     {{ font-weight: 700; color: var(--green-hi); }}
  .badge {{
    display: inline-block; font-size: 11px; padding: 2px 7px;
    border-radius: 10px; font-weight: 600; white-space: nowrap;
  }}
  .badge-sprint  {{ background: #1a3050; color: #58a6ff; }}
  .badge-gc      {{ background: #2d1b00; color: var(--gold-hi); }}
  .badge-break   {{ background: #1a2d1a; color: var(--green-hi); }}
  .badge-punchy  {{ background: #2d1a2d; color: #d2a8ff; }}
  .badge-dom     {{ background: #1c2128; color: var(--muted); }}
  .muted         {{ color: var(--muted); font-style: italic; }}
  .stage2-warn {{
    background: #1a1a2d; border: 1px solid #3d3d8a;
    border-radius: 6px; padding: 12px 16px; margin: 8px 0;
    color: #8888cc;
  }}
  .section {{ margin-bottom: 32px; }}
  details {{ margin: 8px 0; }}
  summary {{
    cursor: pointer; color: var(--blue-hi); padding: 6px;
    background: var(--surface); border-radius: 4px;
  }}
  summary:hover {{ color: #58a6ff; }}
  code {{ background: var(--surface); padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
  .footer {{
    border-top: 1px solid var(--border); padding-top: 16px;
    color: var(--muted); font-size: 12px; margin-top: 32px;
  }}
  .search-bar {{
    width: 100%; padding: 8px 12px; background: var(--surface);
    border: 1px solid var(--border); color: var(--text);
    border-radius: 6px; margin-bottom: 10px; font-size: 13px;
  }}
  .search-bar:focus {{ outline: none; border-color: var(--blue); }}
  #type-filter {{
    padding: 6px 10px; background: var(--surface); border: 1px solid var(--border);
    color: var(--text); border-radius: 6px; margin-bottom: 10px;
    font-size: 13px; cursor: pointer;
  }}
  .filter-row {{ display: flex; gap: 10px; margin-bottom: 8px; align-items: center; }}
  .label {{ color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <h1>Stage 1 Decision Dashboard — Giro d'Italia 2026</h1>
  <p class="subtitle">
    Nessebar → Burgas &nbsp;|&nbsp; 147 km &nbsp;|&nbsp; Flat sprint &nbsp;|&nbsp;
    <strong>May 8 17:00</strong>
    &nbsp;|&nbsp; Trading window opens ~20:30
  </p>

  <div class="warning-banner">
    ⚠ Team is EMPTY — submit selection at holdet.dk before 17:00 on May 8
    &nbsp;|&nbsp; Initial selection is FREE (no transfer fees)
  </div>

  <div class="budget-bar">
    <div><span>Budget: </span><strong>{fmt_kr(BUDGET)}</strong></div>
    <div><span>Team cost: </span><strong>{fmt_kr(total_cost)}</strong></div>
    <div><span>Remaining: </span><strong style="color: {'#2ea043' if remaining_budget > 2_000_000 else '#f85149'}">{fmt_kr(remaining_budget)}</strong></div>
    <div><span>Tier: </span><strong>Gold</strong></div>
  </div>


  <!-- Section 1: Recommended Team -->
  <div class="section">
    <h2>§1 — Recommended Team (8 Riders)</h2>
    <p class="muted" style="margin-bottom:10px;">
      Optimised for 3-stage EV + captain EV &nbsp;|&nbsp;
      ★ = captain &nbsp;|&nbsp; Green rows = recommended &nbsp;|&nbsp; Gold row = captain pick
    </p>
    <table class="ev-table">
      <thead>
        <tr>
          <th>Rider</th><th>Team</th><th>Price</th>
          <th>EV S1</th><th>EV S2</th><th>EV S3</th>
          <th>3-Stage EV</th><th>Captain EV</th>
          <th>Type</th><th>P(win S1)</th>
        </tr>
      </thead>
      <tbody>
        {rec_rows}
      </tbody>
    </table>
    <p style="margin-top:6px; font-size:12px; color:var(--muted);">
      Captain EV = 0.6 × Stage 1 EV (upside of positive doubling)
    </p>
  </div>


  <!-- Section 2: Full EV Table -->
  <div class="section">
    <h2>§2 — Full EV Table (All Active Riders)</h2>
    <div class="filter-row">
      <input class="search-bar" id="search" placeholder="Search rider or team…" style="flex:1;" />
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
    <table class="ev-table" id="full-table">
      <thead>
        <tr>
          <th data-col="name">Rider</th>
          <th data-col="team">Team</th>
          <th data-col="price">Price</th>
          <th data-col="ev1">EV S1</th>
          <th data-col="ev2">EV S2</th>
          <th data-col="ev3_stage">EV S3</th>
          <th data-col="ev3s" class="sorted-desc">3-Stage EV</th>
          <th data-col="cap_ev">Captain EV</th>
          <th data-col="type_label">Type</th>
          <th data-col="wp1">P(win S1)%</th>
        </tr>
      </thead>
      <tbody id="full-table-body"></tbody>
    </table>
    <p id="table-count" style="color:var(--muted);font-size:12px;margin-top:4px;"></p>
  </div>


  <!-- Section 3: Captain Recommendation -->
  <div class="section">
    <h2>§3 — Captain Recommendation</h2>
    <p class="muted" style="margin-bottom:10px;">Top 5 captain candidates from recommended team</p>
    <table class="ev-table">
      <thead>
        <tr>
          <th>#</th><th>Rider</th><th>Team</th><th>Price</th>
          <th>Type</th><th>Captain EV</th><th>Rationale</th>
        </tr>
      </thead>
      <tbody>
        {cap_rows}
      </tbody>
    </table>
  </div>


  <!-- Section 4: Stage 2 Warning -->
  <div class="section">
    <h2>§4 — Stage 2 Warning</h2>
    <div class="stage2-warn">
      <strong>Stage 2 is HILLY (221 km, +2800 m) — sprinter EV drops sharply.</strong><br>
      Pure sprinters earn very little on Stage 2. Verify your sprinters earn their place
      across Stage 1 and Stage 3 combined before selecting them.
      Breakaway and punchy riders have the highest Stage 2 EV — consider including
      at least 1–2 to hedge.
    </div>

    <h3 style="margin-top:14px;">Stage 1–3 Profile</h3>
    <table class="ev-table">
      <thead>
        <tr><th>Stage</th><th>Route</th><th>Distance</th><th>Terrain</th><th>Sprints</th><th>KOMs</th></tr>
      </thead>
      <tbody>
        <tr><td>1</td><td>Nessebar → Burgas</td><td>147 km</td><td>Flat</td><td>1</td><td>0</td></tr>
        <tr><td>2</td><td>Burgas → Veliko Tarnovo</td><td>221 km</td><td>Hilly</td><td>1</td><td>2</td></tr>
        <tr><td>3</td><td>Plovdiv → Sofia</td><td>175 km</td><td>Flat</td><td>1</td><td>1</td></tr>
      </tbody>
    </table>
  </div>


  <!-- Section 5: Odds Divergence -->
  <div class="section">
    <h2>§5 — Odds Divergence Analysis</h2>
    {odds_section}
  </div>


  <!-- DNS Exclusions -->
  <div class="section">
    <h2>§6 — DNS Riders (Excluded)</h2>
    <table class="ev-table">
      <thead><tr><th>Rider</th><th>Team</th><th>holdet_id</th><th>Status</th></tr></thead>
      <tbody>{dns_rows}</tbody>
    </table>
  </div>


  <!-- Alternative Teams -->
  <div class="section">
    <h2>§7 — Alternative Team Compositions</h2>
    {alt_html if alt_html else '<p class="muted">No alternative teams computed.</p>'}
  </div>


  <!-- Transfer Cost Reference -->
  <div class="section">
    <h2>§8 — Transfer Cost Formula (Future Reference)</h2>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:14px;">
      <p style="font-family:monospace;color:#79c0ff;white-space:pre-wrap;">Net EV(transfer) =
  EV(rider_in,  stages t→t+n)
− EV(rider_out, stages t→t+n)
− transfer_fee_in  (1% of buy price)
− transfer_fee_out (1% of sell price)   ← critical, often missed</p>
      <p style="margin-top:8px;color:var(--muted);font-size:12px;">
        Stage 1 initial selection is FREE. Fees apply from Stage 2 onwards.
      </p>
    </div>
  </div>


  <!-- Footer -->
  <div class="footer">
    <p>Snapshot: {snap_ts} &nbsp;|&nbsp; Rule-based baseline — no ML model</p>
    <p style="margin-top:4px;">Submit team at <strong>holdet.dk</strong> before 17:00 May 8</p>
  </div>

</div><!-- /container -->


<script>
// ── Data ──────────────────────────────────────────────────────────────────
const ALL_RIDERS = {riders_js};
const REC_IDS   = new Set({json.dumps(list(rec_ids))});
const CAP_ID    = {json.dumps(cap_id)};

// ── Table rendering ────────────────────────────────────────────────────────
let sortCol  = "ev3s";
let sortDesc = true;
let filterText = "";
let filterType = "";

function fmt(n) {{
  return Math.round(n).toLocaleString("da-DK") + " kr";
}}

function badge(type) {{
  const cls = {{
    "elite_sprinter": "badge-sprint",
    "good_sprinter":  "badge-sprint",
    "punchy":         "badge-punchy",
    "gc_rider":       "badge-gc",
    "climber":        "badge-gc",
    "breakaway":      "badge-break",
    "domestique":     "badge-dom",
  }}[type] || "badge-dom";
  return `<span class="badge ${{cls}}">${{type}}</span>`;
}}

function renderTable() {{
  let rows = ALL_RIDERS.slice();

  if (filterText) {{
    const q = filterText.toLowerCase();
    rows = rows.filter(r =>
      r.name.toLowerCase().includes(q) || r.team.toLowerCase().includes(q)
    );
  }}
  if (filterType) {{
    rows = rows.filter(r => r.type === filterType);
  }}

  rows.sort((a, b) => {{
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === "string") va = va.toLowerCase();
    if (typeof vb === "string") vb = vb.toLowerCase();
    if (va < vb) return sortDesc ? 1 : -1;
    if (va > vb) return sortDesc ? -1 : 1;
    return 0;
  }});

  const tbody = document.getElementById("full-table-body");
  tbody.innerHTML = rows.map(r => {{
    const isRec = REC_IDS.has(r.rider_id);
    const isCap = r.rider_id === CAP_ID;
    const cls   = isCap ? "captain-row" : (isRec ? "rec-row" : "");
    const capMark = isCap ? " ★" : "";
    return `<tr class="${{cls}}">
      <td>${{r.name}}${{capMark}}</td>
      <td>${{r.team}}</td>
      <td>${{fmt(r.price)}}</td>
      <td>${{fmt(r.ev1)}}</td>
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

// ── Sort on header click ───────────────────────────────────────────────────
document.querySelectorAll("#full-table th[data-col]").forEach(th => {{
  th.addEventListener("click", () => {{
    const col = th.dataset.col;
    if (sortCol === col) {{
      sortDesc = !sortDesc;
    }} else {{
      sortCol  = col;
      sortDesc = true;
    }}
    document.querySelectorAll("#full-table th").forEach(t => {{
      t.classList.remove("sorted-asc", "sorted-desc");
    }});
    th.classList.add(sortDesc ? "sorted-desc" : "sorted-asc");
    renderTable();
  }});
}});

// ── Search & type filter ───────────────────────────────────────────────────
document.getElementById("search").addEventListener("input", e => {{
  filterText = e.target.value;
  renderTable();
}});
document.getElementById("type-filter").addEventListener("change", e => {{
  filterType = e.target.value;
  renderTable();
}});

renderTable();
</script>
</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✓ Dashboard written → {OUT}")
print(f"\nRecommended team ({fmt_kr(total_cost)} / {fmt_kr(BUDGET)}):")
for r in recommended:
    cap = " ★ CAPTAIN" if r.get("captain") else ""
    print(f"  {r['name']:<35} {r['team']:<30} {fmt_kr(r['price']):>15}  3S-EV:{fmt_kr(r['ev3s'])} {cap}")
print(f"\nRemaining budget: {fmt_kr(remaining_budget)}")
print(f"Captain: {next((r['name'] for r in recommended if r.get('captain')), 'None')}")
