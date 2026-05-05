#!/usr/bin/env python3
"""Build Stage 1 Decision Dashboard for Giro 2026 — Phase 3f (collapsible rows, stage flipper)."""

import base64, json, math, os, sys, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

from models.ev_breakdown import (
    make_win_probs, rider_stage_ev_breakdown, captain_bonus_ev,
    sprint_kom_ev, classify, load_rider_attributes,
)

OUT = Path(__file__).resolve().parent / "stage1_dashboard.html"

# ── Load data ────────────────────────────────────────────────────────────────
riders_raw   = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
stages_meta  = {s["stage_number"]: s
                for s in json.loads((BASE / "data/stages/stages_giro2026.json").read_text())["stages"]}
roadbooks    = {r["stage"]: r
                for r in json.loads((BASE / "data/stages/stage_roadbook.json").read_text())}
prices_snap  = json.loads((BASE / "data/riders/prices_giro2026_stage0_pre.json").read_text())

try:
    odds_raw   = json.loads((BASE / "data/odds/odds_giro2026_stage1_T0.json").read_text())
    odds_probs = {e["rider_id"]: e["implied_probability"]
                  for e in odds_raw.get("stage_win_odds", [])
                  if e.get("implied_probability", 0) > 0}
except Exception:
    odds_probs = {}

snap_ts = prices_snap.get("timestamp", "unknown")

# ── Load attribute overrides ──────────────────────────────────────────────────
_overrides_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
_overrides: list[dict] = []
if _overrides_path.exists():
    _raw = yaml.safe_load(_overrides_path.read_text()) or {}
    _overrides = _raw.get("overrides", [])

# ── Load stage profiles for flipper ──────────────────────────────────────────
_stage_profiles = json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())
_stage_profiles_by_n = {p["stage"]: p for p in _stage_profiles}

def _embed_stages_js() -> str:
    """Return JS array literal of all 21 stage objects (base64 images embedded if present)."""
    stages_js = []
    for p in sorted(_stage_profiles, key=lambda x: x["stage"]):
        n = p["stage"]
        img_path = BASE / f"data/stage_images/stage-{n}.jpg"
        if img_path.exists():
            img_uri = "data:image/jpeg;base64," + base64.b64encode(img_path.read_bytes()).decode()
        else:
            img_uri = ""
        rb = roadbooks.get(n, {})
        stages_js.append({
            "number":      n,
            "label":       f"Stage {n} — {p.get('distance_km','?')}km, {p.get('stage_type','?').title()}",
            "image_b64":   img_uri,
            "type":        p.get("stage_type", ""),
            "finish_type": p.get("finish_type", ""),
            "distance":    p.get("distance_km", 0),
            "sprints":     len(rb.get("intermediate_sprints", [])),
            "koms":        len(rb.get("kom_climbs", [])),
        })
    return json.dumps(stages_js, ensure_ascii=False)

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

# ── Active riders (with overrides applied) ───────────────────────────────────
active_riders = [
    load_rider_attributes(r, 1, _overrides)
    for r in riders_raw
    if r.get("status") != "dns"
    and r.get("holdet_id")
    and r.get("holdet_id") not in DNS_IDS
]

# ── Archetype classification (Phase 3f) ──────────────────────────────────────
def get_archetype(rider: dict) -> str:
    ta = rider.get("terrain_affinity", {})
    s = ta.get("sprint", 0);  c = ta.get("climbing", 0)
    p = ta.get("mixed",  0);  g = ta.get("gc", 0)
    b = ta.get("breakaway", 0); t = ta.get("time_trial", 0)
    if g >= 0.65 and (c >= 0.60 or t >= 0.55): return "gc_leader"
    if b >= 0.65 and s < 0.55 and c < 0.55:    return "breakaway_artist"
    if s >= 0.65:                                return "sprinter"
    if c >= 0.65:                                return "climber"
    if p >= 0.55:                                return "puncheur"
    if t >= 0.65:                                return "tt_specialist"
    return "all_rounder"

_SPRINTER_ARCHETYPES = {"sprinter", "gc_leader"}

def terrain_mismatch(archetype: str, stage_type: str) -> bool:
    """True if rider archetype is structurally penalised on this stage type."""
    if archetype in ("sprinter",) and stage_type in ("hilly", "mountain"):
        return True
    if archetype in ("climber",) and stage_type == "sprint":
        return True
    return False

# ── Win probabilities per stage ──────────────────────────────────────────────
def stage_win_probs(stage_n):
    rb = roadbooks[stage_n]
    return make_win_probs(active_riders, rb["stage_type"], rb["finish_type"])

wp1 = stage_win_probs(1)
wp2 = stage_win_probs(2)
wp3 = stage_win_probs(3)

# ── Enrich riders with EV breakdown ──────────────────────────────────────────
def stage_ev(stage_n, wp, rider):
    rb      = roadbooks[stage_n]
    meta    = stages_meta.get(stage_n, {})
    win_p   = wp.get(rider["rider_id"], 0)
    return rider_stage_ev_breakdown(rider, meta, rb, win_p, stage_n)

enriched = []
for r in active_riders:
    rid = r["rider_id"]
    rt  = classify(r)

    bd1 = stage_ev(1, wp1, r)
    bd2 = stage_ev(2, wp2, r)
    bd3 = stage_ev(3, wp3, r)

    ev1  = bd1["total"]
    ev2  = bd2["total"]
    ev3s = ev1 + ev2 + bd3["total"]

    # Captain bonus uses new signature: win_prob, finish_type, je, sk
    win_p1   = wp1.get(rid, 0)
    rb1      = roadbooks[1]
    cap_ev   = captain_bonus_ev(win_p1, rb1["finish_type"], bd1["jersey"], bd1["sprint_kom"])

    arch = get_archetype(r)
    var3s = (bd1.get("variance", 0) + bd2.get("variance", 0) + bd3.get("variance", 0))
    sigma3s = round(math.sqrt(var3s)) if var3s > 0 else 0
    ev_per_sigma = round(ev3s / max(sigma3s, 1), 3)

    s1_type = roadbooks[1].get("stage_type", "flat")
    s2_type = roadbooks[2].get("stage_type", "flat")
    s3_type = roadbooks[3].get("stage_type", "flat")

    enriched.append({
        "rider_id":   rid,
        "name":       r["name"],
        "team":       r["team"],
        "holdet_id":  r["holdet_id"],
        "price":      r.get("price", 0),
        "type":       rt,
        "type_label": TYPE_LABEL[rt],
        "archetype":  arch,
        "wp1":        round(win_p1 * 100, 2),
        "wp2":        round(wp2.get(rid, 0) * 100, 2),
        "wp3":        round(wp3.get(rid, 0) * 100, 2),
        # Stage 1 breakdown
        "s1_finish":  bd1["stage_finish"],
        "s1_gc":      bd1["gc"],
        "s1_jersey":  bd1["jersey"],
        "s1_sk":      bd1["sprint_kom"],
        "ev1":        ev1,
        "s1_mismatch": terrain_mismatch(arch, s1_type),
        # Stage 2 breakdown
        "s2_finish":  bd2["stage_finish"],
        "s2_gc":      bd2["gc"],
        "s2_jersey":  bd2["jersey"],
        "s2_sk":      bd2["sprint_kom"],
        "ev2":        ev2,
        "s2_mismatch": terrain_mismatch(arch, s2_type),
        # Stage 3 breakdown
        "s3_finish":  bd3["stage_finish"],
        "s3_gc":      bd3["gc"],
        "s3_jersey":  bd3["jersey"],
        "s3_sk":      bd3["sprint_kom"],
        "ev3_stage":  bd3["total"],
        "s3_mismatch": terrain_mismatch(arch, s3_type),
        "ev3s":       ev3s,
        # Captain EV
        "cap_ev":     cap_ev,
        # Risk metrics
        "sigma3s":    sigma3s,
        "ev_per_sigma": ev_per_sigma,
        "sort_score": ev3s + cap_ev,
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
from models.ev_breakdown import team_bonus_ev as _tb

for r in recommended:
    rid      = r["rider_id"]
    raw      = next((x for x in active_riders if x["rider_id"] == rid), {})
    same_team = [t for t in recommended if t["team"] == r["team"] and t["rider_id"] != rid]
    st_wp1    = {t["rider_id"]: wp1.get(t["rider_id"], 0) for t in same_team}
    raw_team  = [next(x for x in active_riders if x["rider_id"] == t["rider_id"]) for t in same_team]
    r["s1_team_bonus"] = _tb(raw, raw_team, st_wp1)
    r["ev1_with_tb"]   = r["ev1"] + r["s1_team_bonus"]

# ── Captain ───────────────────────────────────────────────────────────────────
if recommended:
    cap_idx = max(range(len(recommended)), key=lambda i: recommended[i]["ev1"])
    for i, r in enumerate(recommended):
        r["captain"] = (i == cap_idx)

rec_ids = {r["rider_id"] for r in recommended}
cap_id  = next((r["rider_id"] for r in recommended if r.get("captain")), None)

cap_candidates = sorted(recommended, key=lambda x: x["ev1"], reverse=True)[:5]

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

# ── Expert intelligence (stage 1) ─────────────────────────────────────────────
_intel_path = BASE / "data/intelligence/stage1_expert_intel.yaml"
_intel_data: dict = {}
if _intel_path.exists():
    _intel_data = yaml.safe_load(_intel_path.read_text()) or {}

def _intel_panel_html(intel: dict) -> str:
    merged = intel.get("merged", [])
    if not merged:
        return ""
    rows = []
    for sig in sorted(merged, key=lambda s: abs(s.get("adjustment", 0)), reverse=True):
        adj = sig.get("adjustment", 0)
        direction = "▲" if adj > 0 else "▼"
        color = "#2ea043" if adj > 0 else "#f85149"
        sources = ", ".join(sig.get("sources", []))
        reasons = " / ".join(sig.get("reasons", []))[:80]
        rows.append(
            f"<tr><td>{sig['rider']}</td>"
            f"<td>{sig['attribute'].replace('_affinity','')}</td>"
            f"<td style='color:{color}'>{direction} {adj:+.2f}</td>"
            f"<td>{sources}</td>"
            f"<td class='muted' style='font-size:11px'>{reasons}</td></tr>"
        )
    n = len(merged)
    date_gathered = intel.get("date_gathered", "unknown")
    return f"""<p class="muted" style="margin-bottom:8px">
      {n} rider adjustments gathered {date_gathered} — applied as <code>mode:adjust</code> overrides.
      Rebuild EVs after gathering: <code>python3 scripts/apply_corrections_and_rebuild.py</code>
    </p>
    <div style="overflow-x:auto">
    <table class="ev-table">
      <thead><tr><th>Rider</th><th>Attribute</th><th>Adjustment</th><th>Sources</th><th>Reason</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>"""


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
      <td>{fmt(r['cap_ev'])}</td><td>{fmt(r['ev1'])}</td>
      <td>{reasons.get(r['type'], '')}</td>
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
  .stage-profile{{margin:12px 0}}
  .stage-profile img{{width:100%;max-width:1050px;border-radius:6px;
                      border:1px solid var(--border)}}
  .stage-meta{{display:flex;gap:20px;margin-top:6px;flex-wrap:wrap}}
  .stage-meta span{{background:var(--surface);border:1px solid var(--border);
    border-radius:4px;padding:3px 10px;font-size:12px;color:var(--muted)}}
  .stage-flipper{{display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap}}
  .flipper-btn{{padding:6px 14px;background:var(--surface);border:1px solid var(--border);
    color:var(--blue-hi);border-radius:6px;cursor:pointer;font-size:13px}}
  .flipper-btn:hover{{border-color:var(--blue-hi)}}
  .flipper-btn:disabled{{opacity:.3;cursor:default}}
  #stage-label{{flex:1;text-align:center;font-weight:600;color:#e6edf3;font-size:14px}}
  .stage-img-placeholder{{background:var(--surface);border:1px solid var(--border);
    border-radius:6px;padding:40px;text-align:center;color:var(--muted);
    font-size:13px;max-width:1050px}}
  .rider-detail-row{{display:none;background:#0d1117}}
  .rider-detail-row td{{padding:0}}
  .detail-box{{padding:10px 16px;border-bottom:1px solid var(--border);
    font-size:12px;line-height:1.7}}
  .detail-stage-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:6px}}
  .detail-stage{{background:var(--surface);border:1px solid var(--border);
    border-radius:4px;padding:8px 10px}}
  .detail-stage-hdr{{font-weight:600;color:var(--blue-hi);margin-bottom:4px;font-size:11px}}
  .mismatch-warn{{color:#f0a030;font-weight:600}}
  .expand-arrow{{color:var(--muted);margin-left:4px;font-size:11px}}
  .rider-row-clickable{{cursor:pointer}}
  .rider-row-clickable:hover td{{background:#1c2128 !important}}
  table.ev-table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:8px}}
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
  .intel-panel{{background:var(--surface);border:1px solid var(--border);
    border-radius:6px;padding:14px;margin-top:10px}}
  .intel-btn{{
    padding:8px 16px;background:#1f3a5c;border:1px solid var(--blue);
    color:var(--blue-hi);border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}}
  .intel-btn:hover{{background:#1a4a7a;border-color:#58a6ff}}
  .intel-signal-up{{color:#2ea043;font-weight:600}}
  .intel-signal-down{{color:#f85149;font-weight:600}}
</style>
</head>
<body>
<div class="container">

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

<div class="section">
  <h2>Stage Profiles (1–21)</h2>
  <div class="stage-flipper">
    <button class="flipper-btn" id="prev-stage" onclick="flipStage(-1)">← Prev</button>
    <span id="stage-label">Loading…</span>
    <button class="flipper-btn" id="next-stage" onclick="flipStage(+1)">Next →</button>
  </div>
  <div class="stage-profile">
    <div id="stage-image-wrap"></div>
    <div id="stage-meta" class="stage-meta"></div>
  </div>
</div>

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
    Captain EV = E[max(ΔV, 0)] from position distribution — positive value growth deposited to bank.
    Team Bonus = expected kr from same-team riders finishing top 3.
  </p>
</div>

<div class="prob-callout">
  <strong>⚠️ Probability model: rule-based baseline (Phase 3c)</strong><br>
  Win probability derived from <code>terrain_affinity</code> (Layer 0 rider attributes) only.<br>
  Sprint/KOM point scales are OFFICIAL fixed Giro values (not estimated).<br>
  GC EV on flat stages: peloton finishes same time → GC pos = stage finish pos.<br>
  Captain bonus = E[max(ΔV, 0)] — positive upside only, negative days not amplified.<br>
  <strong>These are structural estimates, not trained model outputs.</strong>
  Replace in Phase 4 with trained StageFinishPosition model.
</div>

<div class="section">
  <h2>§2 — Full EV Table (All Active Riders)</h2>
  <p class="muted" style="margin-bottom:8px;font-size:12px;">
    Click any row to expand 6-component EV breakdown × 3 stages + σ and terrain mismatch ⚠
  </p>
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
      <th data-col="ev1" class="ev-s1">S1 Total</th>
      <th data-col="ev2">S2 EV</th>
      <th data-col="ev3_stage">S3 EV</th>
      <th data-col="ev3s" class="sorted-desc">3-Stage EV</th>
      <th data-col="sigma3s">σ (3-stg)</th>
      <th data-col="ev_per_sigma">EV/σ</th>
      <th data-col="cap_ev">Capt EV</th>
      <th data-col="type_label">Type</th>
      <th data-col="archetype">Archetype</th>
      <th data-col="wp1">P(win S1)%</th>
      <th></th>
    </tr></thead>
    <tbody id="full-table-body"></tbody>
  </table>
  </div>
  <p id="table-count"></p>
</div>

<div class="section">
  <h2>§3 — Captain Recommendation</h2>
  <p class="muted" style="margin-bottom:10px;">Top 5 candidates from recommended team (ranked by S1 EV)</p>
  <table class="ev-table">
    <thead><tr>
      <th>#</th><th>Rider</th><th>Team</th><th>Price</th>
      <th>Type</th><th>Captain EV</th><th>S1 Total EV</th><th>Rationale</th>
    </tr></thead>
    <tbody>{cap_rows}</tbody>
  </table>
</div>

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

<div class="section">
  <h2>§5 — Odds Divergence Analysis</h2>
  {odds_section}
</div>

<div class="section">
  <h2>§6 — DNS Riders (Excluded)</h2>
  <table class="ev-table">
    <thead><tr><th>Rider</th><th>Team</th><th>holdet_id</th><th>Status</th></tr></thead>
    <tbody>{dns_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>§7 — Alternative Team Compositions</h2>
  {alt_html or '<p class="muted">No alternative teams computed.</p>'}
</div>

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

<div class="section">
  <h2>§9 — Expert Intelligence (Stage 1)</h2>
  <p class="muted" style="margin-bottom:10px;">
    Gather Emil Axelgaard (TV2 Sport) + 4 secondary sources via Anthropic API.
    Signals are merged with weighted agreement/conflict logic and applied as
    <code>mode:adjust</code> overrides — additive on top of base attributes, capped at [0,1].
  </p>
  <div class="intel-header" style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
    <button class="intel-btn" onclick="showIntelCommands()">🔍 Gather Intelligence</button>
    <div id="intel-commands" style="display:none;font-size:12px">
      <code>python3 scripts/gather_expert_intel.py --stage 1</code>
      &nbsp; then &nbsp;
      <code>python3 scripts/apply_corrections_and_rebuild.py</code>
      &nbsp;
      <button onclick="document.getElementById('intel-commands').style.display='none'"
              style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:12px">✕</button>
    </div>
  </div>
  <div id="intel-summary" class="intel-panel">
    {_intel_panel_html(_intel_data) or '<p class="muted">No intelligence gathered yet. Click \'Gather Intelligence\' above.</p>'}
  </div>
</div>

<div class="footer">
  <p>Snapshot: {snap_ts} &nbsp;|&nbsp; Phase 3f — collapsible rows, stage flipper, archetype risk profiles</p>
  <p style="margin-top:4px;">Submit team at <strong>holdet.dk</strong> before 17:00 May 8</p>
</div>
</div>

<script>
const ALL_RIDERS = {riders_js};
const REC_IDS    = new Set({json.dumps(list(rec_ids))});
const CAP_ID     = {json.dumps(cap_id)};
const STAGES_JS  = {_embed_stages_js()};

// ── Stage flipper ─────────────────────────────────────────────────────────────
let currentStageIdx = 0;

function renderStage(stage) {{
  const wrap  = document.getElementById("stage-image-wrap");
  const meta  = document.getElementById("stage-meta");
  const label = document.getElementById("stage-label");
  label.textContent = stage.label;
  wrap.innerHTML = stage.image_b64
    ? `<img src="${{stage.image_b64}}" alt="Stage ${{stage.number}} profile" style="width:100%;max-width:1050px;border-radius:6px;border:1px solid var(--border)">`
    : `<div class="stage-img-placeholder">Stage ${{stage.number}} image not available — add to data/stage_images/stage-${{stage.number}}.jpg</div>`;
  meta.innerHTML = [
    `Type: ${{stage.type || "?"}}`,
    `Distance: ${{stage.distance}} km`,
    `Finish: ${{stage.finish_type || "?"}}`,
    `Sprints: ${{stage.sprints}}`,
    `KOMs: ${{stage.koms}}`,
  ].map(t => `<span>${{t}}</span>`).join("");
  document.getElementById("prev-stage").disabled = (currentStageIdx === 0);
  document.getElementById("next-stage").disabled = (currentStageIdx === STAGES_JS.length - 1);
}}

function flipStage(delta) {{
  currentStageIdx = Math.max(0, Math.min(STAGES_JS.length - 1, currentStageIdx + delta));
  renderStage(STAGES_JS[currentStageIdx]);
}}

renderStage(STAGES_JS[currentStageIdx]);

// ── Full rider table with collapsible rows ────────────────────────────────────
let sortCol    = "ev3s";
let sortDesc   = true;
let filterText = "";
let filterType = "";
const openRows = new Set();

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

function stageDetail(r, n, evField, finField, gcField, jerField, skField, wpField, mmField) {{
  const mismatch = r[mmField] ? `<span class="mismatch-warn"> ⚠ terrain mismatch</span>` : "";
  return `
    <div class="detail-stage">
      <div class="detail-stage-hdr">Stage ${{n}} (P(win): ${{r[wpField]}}%)${{mismatch}}</div>
      <div><span class="bd-finish">Finish:</span> ${{fmt(r[finField])}}</div>
      <div><span class="bd-gc">GC:</span> ${{fmt(r[gcField])}}</div>
      <div><span class="bd-jer">Jersey:</span> ${{fmt(r[jerField])}}</div>
      <div><span class="bd-sk">Spr/KOM:</span> ${{fmt(r[skField])}}</div>
      <div style="margin-top:4px;font-weight:600">Total: ${{fmt(r[evField])}}</div>
    </div>`;
}}

function detailHtml(r) {{
  const ev_per_s = r.sigma3s > 0 ? (r.ev3s / r.sigma3s).toFixed(2) : "—";
  return `
  <td colspan="14">
    <div class="detail-box">
      <div style="display:flex;gap:16px;margin-bottom:6px;font-size:11px;color:var(--muted)">
        <span>Archetype: <strong style="color:var(--text)">${{r.archetype}}</strong></span>
        <span>σ (3-stg): <strong>${{fmt(r.sigma3s)}}</strong></span>
        <span>EV/σ: <strong>${{r.ev_per_sigma}}</strong></span>
        <span>3-Stage EV: <strong class="ev-total">${{fmt(r.ev3s)}}</strong></span>
        <span>Captain EV: <strong>${{fmt(r.cap_ev)}}</strong></span>
      </div>
      <div class="detail-stage-grid">
        ${{stageDetail(r,1,"ev1","s1_finish","s1_gc","s1_jersey","s1_sk","wp1","s1_mismatch")}}
        ${{stageDetail(r,2,"ev2","s2_finish","s2_gc","s2_jersey","s2_sk","wp2","s2_mismatch")}}
        ${{stageDetail(r,3,"ev3_stage","s3_finish","s3_gc","s3_jersey","s3_sk","wp3","s3_mismatch")}}
      </div>
    </div>
  </td>`;
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
  const frags = [];
  rows.forEach(r => {{
    const isRec  = REC_IDS.has(r.rider_id);
    const isCap  = r.rider_id === CAP_ID;
    const isOpen = openRows.has(r.rider_id);
    const cls    = isCap ? "captain-row rider-row-clickable"
                         : (isRec ? "rec-row rider-row-clickable" : "rider-row-clickable");
    const arrow  = isOpen ? "▼" : "▶";

    frags.push(`<tr class="${{cls}}" data-id="${{r.rider_id}}">
      <td>${{r.name}}${{isCap ? " ★" : ""}}</td>
      <td>${{r.team}}</td>
      <td>${{fmt(r.price)}}</td>
      <td class="ev-s1">${{fmt(r.ev1)}}</td>
      <td>${{fmt(r.ev2)}}</td>
      <td>${{fmt(r.ev3_stage)}}</td>
      <td class="ev-total">${{fmt(r.ev3s)}}</td>
      <td>${{fmt(r.sigma3s)}}</td>
      <td>${{r.ev_per_sigma}}</td>
      <td>${{fmt(r.cap_ev)}}</td>
      <td>${{badge(r.type)}}</td>
      <td style="color:var(--muted);font-size:11px">${{r.archetype}}</td>
      <td>${{r.wp1}}%</td>
      <td class="expand-arrow">${{arrow}}</td>
    </tr>`);

    if (isOpen) {{
      frags.push(`<tr class="rider-detail-row" style="display:table-row" data-detail="${{r.rider_id}}">${{detailHtml(r)}}</tr>`);
    }} else {{
      frags.push(`<tr class="rider-detail-row" data-detail="${{r.rider_id}}">${{detailHtml(r)}}</tr>`);
    }}
  }});

  tbody.innerHTML = frags.join("");

  tbody.querySelectorAll("tr.rider-row-clickable").forEach(row => {{
    row.addEventListener("click", () => {{
      const id     = row.dataset.id;
      const detail = tbody.querySelector(`tr[data-detail="${{id}}"]`);
      const arrow  = row.querySelector(".expand-arrow");
      if (!detail) return;
      const isNowOpen = detail.style.display === "table-row";
      if (isNowOpen) {{
        detail.style.display = "none";
        arrow.textContent = "▶";
        openRows.delete(id);
      }} else {{
        detail.style.display = "table-row";
        arrow.textContent = "▼";
        openRows.add(id);
      }}
    }});
  }});

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

// ── Intelligence panel toggle ─────────────────────────────────────────────────
function showIntelCommands() {{
  const el = document.getElementById("intel-commands");
  el.style.display = el.style.display === "none" ? "inline-flex" : "none";
}}
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
