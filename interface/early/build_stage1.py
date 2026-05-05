#!/usr/bin/env python3
"""Build Stage 1 Decision Dashboard — Giro 2026 (Phase 3h+3i)

Scenario-based EV model with live sliders:
  Bunch Sprint / Reduced Sprint / Breakaway / GC Day
Team recommendation updates in real time as sliders change.
"""

import base64, json, math, sys, yaml
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

from models.ev_breakdown import (
    load_rider_attributes,
    build_rider_scenario_data,
    compute_blended_win_prob,
    get_rider_archetype,
    SCENARIO_CONFIGS,
    STAGE_TYPE_DEFAULTS,
    PURE_SCENARIOS,
)

OUT = Path(__file__).resolve().parent / "stage1_dashboard.html"

# ── Load data ─────────────────────────────────────────────────────────────────
riders_raw   = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())["riders"]
roadbooks    = {r["stage"]: r
                for r in json.loads((BASE / "data/stages/stage_roadbook.json").read_text())}
_stage_profiles = json.loads((BASE / "data/stages/stage_profiles_parsed.json").read_text())
_stage_profiles_by_n = {p["stage"]: p for p in _stage_profiles}

try:
    prices_snap = json.loads((BASE / "data/riders/prices_giro2026_stage0_pre.json").read_text())
    snap_ts = prices_snap.get("timestamp", "unknown")
except Exception:
    snap_ts = "unknown"

try:
    odds_raw   = json.loads((BASE / "data/odds/odds_giro2026_stage1_T0.json").read_text())
    odds_probs = {e["rider_id"]: e["implied_probability"]
                  for e in odds_raw.get("stage_win_odds", [])
                  if e.get("implied_probability", 0) > 0}
except Exception:
    odds_probs = {}

# ── Load attribute overrides ──────────────────────────────────────────────────
_overrides: list[dict] = []
_ov_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
if _ov_path.exists():
    _raw = yaml.safe_load(_ov_path.read_text()) or {}
    _overrides = _raw.get("overrides", [])

# ── Constants ─────────────────────────────────────────────────────────────────
BUDGET       = 50_000_000
MAX_PER_TEAM = 2
DNS_IDS      = {47380, 47350}

STAGE_N     = 1
LOOKAHEAD   = [1, 2, 3]

# Stage 1 is flat; stage 2 hilly; stage 3 flat
RB1 = roadbooks[1]
RB2 = roadbooks[2]
RB3 = roadbooks[3]

# ── Active riders with overrides ──────────────────────────────────────────────
active_riders = [
    load_rider_attributes(r, 1, _overrides)
    for r in riders_raw
    if r.get("status") != "dns"
    and r.get("holdet_id")
    and r.get("holdet_id") not in DNS_IDS
    and not r.get("isOut", False)
]

dns_riders = [{"name": r["name"], "team": r["team"], "holdet_id": r.get("holdet_id", "—")}
              for r in riders_raw if r.get("status") == "dns"]

print(f"  Active riders: {len(active_riders)}")

# ── Build per-scenario EV data for Stage 1 ───────────────────────────────────
print("  Building Stage 1 scenario data…")
s1_scenario_rows = build_rider_scenario_data(active_riders, RB1, active_riders)
s1_by_id = {row["id"]: row for row in s1_scenario_rows}

# ── Load pre-computed EVs for stages 2 and 3 (default scenario weights) ──────
# These are blended at build time using each stage's default weights.
def load_default_ev(stage_n: int) -> dict[int, int]:
    """Load total EV per rider from pre-computed breakdown, keyed by holdet_id."""
    path = BASE / f"models/ev_breakdown_stage{stage_n}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {r["holdet_id"]: data["riders"].get(rid, {}).get("total", 0)
            for r in active_riders
            for rid in [r.get("rider_id") or ""]}

def load_scenario_ev(stage_n: int) -> dict[int, dict]:
    """Load per-scenario EVs per rider for a given stage, keyed by holdet_id."""
    path = BASE / f"models/ev_breakdown_stage{stage_n}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    result: dict[int, dict] = {}
    for r in active_riders:
        rid = r.get("rider_id") or ""
        entry = data["riders"].get(rid, {})
        result[r["holdet_id"]] = {
            "scenario_ev":    entry.get("scenario_ev", {}),
            "scenario_p_win": entry.get("scenario_p_win", {}),
        }
    return result

print("  Loading stage 2 & 3 scenario data…")
s2_scenario = load_scenario_ev(2)
s3_scenario = load_scenario_ev(3)

# Default weights for stages 2 and 3
s2_defaults = STAGE_TYPE_DEFAULTS.get(RB2.get("stage_group", "hilly"), STAGE_TYPE_DEFAULTS["hilly"])
s3_defaults = STAGE_TYPE_DEFAULTS.get(RB3.get("stage_group", "flat"), STAGE_TYPE_DEFAULTS["flat"])

def blend_ev(scenario_ev: dict, weights: dict) -> int:
    return round(sum(weights.get(s, 0) * scenario_ev.get(s, 0)
                     for s in PURE_SCENARIOS))

# ── Build RIDER_SCENARIO_DATA for embedding in HTML ──────────────────────────
# Fields used by JS: id, rider_id, name, team, price, is_out, archetype,
#   scenario_ev (s1), scenario_p_win (s1), s2_ev, s3_ev
print("  Assembling rider scenario data…")
rider_scenario_data = []
for row in s1_scenario_rows:
    hid = row["id"]
    raw = next((r for r in active_riders if r.get("holdet_id") == hid), {})

    s2_se = s2_scenario.get(hid, {})
    s3_se = s3_scenario.get(hid, {})
    s2_ev = blend_ev(s2_se.get("scenario_ev", {}), s2_defaults)
    s3_ev = blend_ev(s3_se.get("scenario_ev", {}), s3_defaults)

    # Stage 1 blended using flat defaults (for initial display)
    s1_flat_w = STAGE_TYPE_DEFAULTS["flat"]
    s1_default_ev = blend_ev(row["scenario_ev"], s1_flat_w)
    s1_default_pw = round(sum(s1_flat_w.get(sc, 0) * row["scenario_p_win"].get(sc, 0)
                               for sc in PURE_SCENARIOS) * 100, 2)

    rider_scenario_data.append({
        "id":         hid,
        "rider_id":   raw.get("rider_id", ""),
        "name":       row["name"],
        "team":       row["team"],
        "price":      row["price"],
        "is_out":     row["is_out"],
        "archetype":  row["archetype"],
        # Stage 1 per-scenario (for slider blending)
        "s1_scenario_ev":    row["scenario_ev"],
        "s1_scenario_p_win": row["scenario_p_win"],
        # Stage 2 & 3 fixed defaults
        "s2_ev": s2_ev,
        "s3_ev": s3_ev,
        # Stage 2 & 3 per-scenario (for detail expansion)
        "s2_scenario_ev":    s2_se.get("scenario_ev", {}),
        "s3_scenario_ev":    s3_se.get("scenario_ev", {}),
        # Initial blended values (flat default)
        "s1_ev":    s1_default_ev,
        "s1_p_win": s1_default_pw,
        "ev3s":     s1_default_ev + s2_ev + s3_ev,
    })

# Sort by 3-stage EV descending
rider_scenario_data.sort(key=lambda x: x["ev3s"], reverse=True)

# ── Default scenario weights for Stage 1 (flat) ──────────────────────────────
default_weights = STAGE_TYPE_DEFAULTS["flat"]  # {"bunch_sprint": 0.7, ...}

# ── Odds divergence ───────────────────────────────────────────────────────────
divergences = []
for row in rider_scenario_data:
    odds_p = odds_probs.get(row["rider_id"])
    if odds_p is not None:
        p_model = row["s1_p_win"]
        diff    = abs(p_model - odds_p * 100)
        if diff > 10:
            divergences.append({"name": row["name"], "model_p": round(p_model, 1),
                                 "odds_p": round(odds_p * 100, 1), "diff": round(diff, 1)})

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
      {n} rider adjustments gathered {date_gathered}.</p>
    <div style="overflow-x:auto">
    <table class="ev-table">
      <thead><tr><th>Rider</th><th>Attribute</th><th>Adj</th><th>Sources</th><th>Reason</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>"""

# ── Stage image embedding ─────────────────────────────────────────────────────
def _embed_stages_js() -> str:
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
            "number":    n,
            "label":     f"Stage {n} — {p.get('distance_km','?')}km, {p.get('stage_type','?').title()}",
            "image_b64": img_uri,
            "type":      p.get("stage_type", ""),
            "group":     rb.get("stage_group", ""),
            "finish_type": p.get("finish_type", ""),
            "distance":  p.get("distance_km", 0),
            "sprints":   1 if "intermediate_sprint" in rb else 0,
            "koms":      len(rb.get("kom_climbs", [])),
        })
    return json.dumps(stages_js, ensure_ascii=False)

# ── Stage 1 image assertion ───────────────────────────────────────────────────
_s1_img = BASE / "data/stage_images/stage-1.jpg"
if _s1_img.exists():
    _s1_uri = "data:image/jpeg;base64," + base64.b64encode(_s1_img.read_bytes()).decode()
    assert _s1_uri.startswith("data:image/jpeg"), "Stage 1 image embedding failed"
    print(f"  ✓ Stage 1 image: {len(_s1_uri)//1024}KB embedded")
else:
    print("  ⚠️  Stage 1 image not found at data/stage_images/stage-1.jpg")

# ── HTML helpers ──────────────────────────────────────────────────────────────
def fmt(n):
    return f"{int(round(n)):,}".replace(",", ".") + " kr"

odds_section = (
    """<table class="ev-table"><thead>
      <tr><th>Rider</th><th>Model P(win)</th><th>Odds P(win)</th><th>Divergence</th></tr>
    </thead><tbody>""" +
    "".join(f"<tr class='flag-row'><td>{d['name']}</td><td>{d['model_p']}%</td>"
            f"<td>{d['odds_p']}%</td><td>{d['diff']} pp — REVIEW</td></tr>"
            for d in divergences) +
    "</tbody></table>"
    if divergences else
    '<p class="muted">No real odds data available. '
    'Run <code>odds_snapshot.py</code> before stage start.</p>'
)

dns_rows = "".join(
    f"<tr class='dns-row'><td>{d['name']}</td><td>{d['team']}</td>"
    f"<td>{d['holdet_id']}</td><td>DNS — EXCLUDED</td></tr>"
    for d in dns_riders
)

# ── JSON payloads ─────────────────────────────────────────────────────────────
riders_json       = json.dumps(rider_scenario_data, ensure_ascii=False)
default_w_json    = json.dumps(default_weights)
scenario_cfg_json = json.dumps({
    k: {"label": v["label"], "color": v["color"], "description": v["description"]}
    for k, v in SCENARIO_CONFIGS.items()
}, ensure_ascii=False)
stages_js_data    = _embed_stages_js()

# ── Build HTML ────────────────────────────────────────────────────────────────
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
  .warning-banner{{background:var(--warn-bg);border:1px solid var(--warn);
    border-radius:6px;padding:12px 16px;margin:16px 0;
    color:#f0a030;font-weight:600;font-size:1rem}}
  .budget-bar{{display:flex;gap:24px;padding:12px 16px;
    background:var(--surface);border:1px solid var(--border);
    border-radius:6px;margin-bottom:16px;flex-wrap:wrap}}
  .budget-bar span{{color:var(--muted)}} .budget-bar strong{{color:var(--green-hi)}}

  /* Scenario panel */
  .scenario-panel{{background:var(--surface);border:1px solid var(--border);
    border-radius:8px;padding:16px;margin-bottom:20px}}
  .scenario-panel h3{{color:#e6edf3;font-size:1rem;margin-bottom:4px}}
  .scenario-hint{{color:var(--muted);font-size:12px;margin-bottom:14px}}
  .sliders{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  @media(max-width:700px){{.sliders{{grid-template-columns:1fr}}}}
  .slider-row{{background:var(--bg);border:1px solid var(--border);
    border-radius:6px;padding:10px 12px}}
  .slider-row label{{display:flex;align-items:center;gap:8px;
    font-size:13px;font-weight:600;margin-bottom:6px;color:#e6edf3}}
  .slider-row label .dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
  .slider-row label .val{{margin-left:auto;color:var(--blue-hi);font-size:13px}}
  .slider-row input[type=range]{{width:100%;accent-color:var(--blue);cursor:pointer}}
  .slider-row small{{color:var(--muted);font-size:11px;display:block;margin-top:4px}}
  .scenario-footer{{display:flex;align-items:center;gap:16px;margin-top:12px;flex-wrap:wrap}}
  .scenario-footer>span{{font-size:13px;color:var(--muted)}}
  #scenario-total{{color:#e6edf3;font-weight:600}}
  #scenario-warning{{color:var(--red);font-weight:600}}
  .presets{{display:flex;gap:6px;flex-wrap:wrap}}
  .preset-btn{{padding:4px 10px;background:var(--bg);border:1px solid var(--border);
    color:var(--blue-hi);border-radius:4px;cursor:pointer;font-size:12px}}
  .preset-btn:hover{{border-color:var(--blue-hi)}}
  .scenario-mix-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;
    margin-top:10px;gap:1px}}
  .scenario-mix-bar span{{transition:flex .3s ease}}

  /* Rider tables */
  .stage-profile{{margin:12px 0}}
  .stage-profile img{{width:100%;max-width:1050px;border-radius:6px;border:1px solid var(--border)}}
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
  .detail-box{{padding:10px 16px;border-bottom:1px solid var(--border);font-size:12px;line-height:1.7}}
  .detail-stage-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:6px}}
  .detail-stage{{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:8px 10px}}
  .detail-stage-hdr{{font-weight:600;color:var(--blue-hi);margin-bottom:4px;font-size:11px}}
  .scenario-detail-table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:11px}}
  .scenario-detail-table th,.scenario-detail-table td{{padding:3px 6px;border-bottom:1px solid var(--border);text-align:right}}
  .scenario-detail-table th:first-child,.scenario-detail-table td:first-child{{text-align:left;color:var(--muted)}}
  .expand-arrow{{color:var(--muted);margin-left:4px;font-size:11px}}
  .rider-row-clickable{{cursor:pointer}}
  .rider-row-clickable:hover td{{background:#1c2128 !important}}
  table.ev-table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:8px}}
  .ev-table th{{background:var(--surface);color:var(--muted);padding:7px 8px;text-align:left;
    font-weight:600;border-bottom:1px solid var(--border);white-space:nowrap;
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
  .badge{{display:inline-block;font-size:11px;padding:2px 7px;
    border-radius:10px;font-weight:600;white-space:nowrap}}
  .badge-sprint{{background:#1a3050;color:#58a6ff}}
  .badge-gc{{background:#2d1b00;color:var(--gold-hi)}}
  .badge-break{{background:#1a2d1a;color:var(--green-hi)}}
  .badge-punchy{{background:#2d1a2d;color:#d2a8ff}}
  .badge-dom{{background:#1c2128;color:var(--muted)}}
  .muted{{color:var(--muted);font-style:italic}}
  .prob-callout{{background:#1a1a2d;border:1px solid #5a3e7a;border-radius:6px;
    padding:12px 16px;margin:8px 0;color:#c9a0ff;font-size:13px;line-height:1.7}}
  .section{{margin-bottom:32px}}
  .filter-row{{display:flex;gap:10px;margin-bottom:8px;align-items:center;flex-wrap:wrap}}
  .search-bar{{flex:1;min-width:200px;padding:7px 12px;background:var(--surface);
    border:1px solid var(--border);color:var(--text);border-radius:6px;font-size:13px}}
  .search-bar:focus{{outline:none;border-color:var(--blue)}}
  select#type-filter{{padding:6px 10px;background:var(--surface);border:1px solid var(--border);
    color:var(--text);border-radius:6px;font-size:13px;cursor:pointer}}
  details{{margin:8px 0}}
  summary{{cursor:pointer;color:var(--blue-hi);padding:6px;background:var(--surface);border-radius:4px}}
  summary:hover{{color:#58a6ff}}
  code{{background:var(--surface);padding:2px 6px;border-radius:4px;font-size:12px}}
  .transfer-box{{background:var(--surface);border:1px solid var(--border);
    border-radius:6px;padding:14px}}
  .footer{{border-top:1px solid var(--border);padding-top:16px;
    color:var(--muted);font-size:12px;margin-top:32px}}
  #table-count{{color:var(--muted);font-size:12px;margin-top:4px}}
  .intel-panel{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:14px;margin-top:10px}}
  .intel-btn{{padding:8px 16px;background:#1f3a5c;border:1px solid var(--blue);
    color:var(--blue-hi);border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}}
  .intel-btn:hover{{background:#1a4a7a;border-color:#58a6ff}}
  .team-summary{{padding:8px 12px;background:var(--surface);border:1px solid var(--border);
    border-radius:0 0 6px 6px;font-size:12px;color:var(--muted)}}
  .team-summary strong{{color:#e6edf3}}
  #scenario-out-warning{{padding:10px;background:#2d1a00;border:1px solid var(--warn);
    border-radius:6px;color:#f0a030;display:none;margin-bottom:8px}}
</style>
</head>
<body>
<div class="container">

<h1>Stage 1 Decision Dashboard — Giro d'Italia 2026</h1>
<p class="subtitle">
  Nessebar → Burgas &nbsp;|&nbsp; 156 km &nbsp;|&nbsp; Flat sprint
</p>

<div class="warning-banner">
  ⚠ Team is EMPTY — submit selection at holdet.dk before stage start
  &nbsp;|&nbsp; Initial selection is FREE (no transfer fees)
</div>

<div class="budget-bar">
  <div><span>Budget: </span><strong id="budget-total">{fmt(BUDGET)}</strong></div>
  <div><span>Team cost: </span><strong id="budget-used">—</strong></div>
  <div><span>Remaining: </span><strong id="budget-remaining">—</strong></div>
</div>

<!-- ── Stage Profiles ────────────────────────────────────────────────────── -->
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

<!-- ── §1 Scenario Sliders ──────────────────────────────────────────────── -->
<div class="section">
  <h2>§1 — Stage Scenario Weights</h2>
  <div class="scenario-panel">
    <h3>How will Stage 1 unfold?</h3>
    <p class="scenario-hint">
      Adjust your read of this stage. Team recommendation and EV table update instantly.
    </p>

    <div class="sliders">
      <div class="slider-row">
        <label>
          <span class="dot" style="background:#2ecc71"></span>
          Bunch Sprint <span class="val" id="val-bunch_sprint"></span>
        </label>
        <input type="range" id="sl-bunch_sprint" min="0" max="100"
               oninput="onSlider('bunch_sprint', this.value)">
        <small>Full peloton — pure sprinters dominate</small>
      </div>

      <div class="slider-row">
        <label>
          <span class="dot" style="background:#f39c12"></span>
          Reduced Sprint <span class="val" id="val-reduced_sprint"></span>
        </label>
        <input type="range" id="sl-reduced_sprint" min="0" max="100"
               oninput="onSlider('reduced_sprint', this.value)">
        <small>Small group — puncheurs and versatile riders</small>
      </div>

      <div class="slider-row">
        <label>
          <span class="dot" style="background:#e74c3c"></span>
          Breakaway <span class="val" id="val-breakaway"></span>
        </label>
        <input type="range" id="sl-breakaway" min="0" max="100"
               oninput="onSlider('breakaway', this.value)">
        <small>Escape group survives — breakaway artists win</small>
      </div>

      <div class="slider-row">
        <label>
          <span class="dot" style="background:#9b59b6"></span>
          GC Day <span class="val" id="val-gc_day"></span>
        </label>
        <input type="range" id="sl-gc_day" min="0" max="100"
               oninput="onSlider('gc_day', this.value)">
        <small>GC selection — climbers and leaders take time</small>
      </div>
    </div>

    <div class="scenario-footer">
      <span>Total: <strong id="scenario-total">100%</strong></span>
      <span id="scenario-warning" style="display:none">⚠ Must sum to 100%</span>
      <div class="presets">
        <button class="preset-btn" onclick="preset('pure_sprint')">Pure Sprint</button>
        <button class="preset-btn" onclick="preset('sprint_risk')">Sprint+Risk</button>
        <button class="preset-btn" onclick="preset('breakaway')">Breakaway</button>
        <button class="preset-btn" onclick="preset('mountain')">Mountain GC</button>
        <button class="preset-btn" onclick="preset('open')">Wide Open</button>
        <button class="preset-btn" onclick="preset('default')">Reset</button>
      </div>
    </div>

    <div class="scenario-mix-bar" id="scenario-bar"></div>
  </div>
</div>

<!-- ── §2 Recommended Team ──────────────────────────────────────────────── -->
<div class="section">
  <h2>§2 — Recommended Team (8 Riders)</h2>
  <p class="muted" style="margin-bottom:8px;font-size:12px">
    ★ = captain &nbsp;|&nbsp; Auto-selected by blended EV (Stage 1 scenario + fixed S2/S3 defaults)
    &nbsp;|&nbsp; Click any row to expand scenario breakdown
  </p>
  <div id="scenario-out-warning">⚠ Scenario weights don't sum to 100% — team not updated</div>
  <div style="overflow-x:auto">
  <table class="ev-table">
    <thead><tr>
      <th>Rider</th><th>Team</th><th>Price</th>
      <th class="ev-s1">S1 EV</th><th>S2 EV</th><th>S3 EV</th>
      <th class="ev-total">3-Stage EV</th>
      <th>P(win S1)</th><th>Archetype</th>
    </tr></thead>
    <tbody id="team-tbody"></tbody>
  </table>
  </div>
  <div class="team-summary" id="team-summary"></div>
</div>

<div class="prob-callout">
  <strong>Model: Phase 3h — scenario-based, AFFINITY_POWER=8</strong><br>
  P(win | bunch_sprint): Milan 25.6%, Groves 23.5%, De Lie 23.5%, Groenewegen 12.7%<br>
  Stage 1 sliders update team in real time. S2 (hilly) and S3 (flat) use fixed defaults.<br>
  <strong>Rule-based baseline. Replace in Phase 4 with trained StageFinishPosition model.</strong>
</div>

<!-- ── §3 Full EV Table ──────────────────────────────────────────────────── -->
<div class="section">
  <h2>§3 — Full EV Table (All Active Riders)</h2>
  <p class="muted" style="margin-bottom:8px;font-size:12px">
    Click row to expand scenario breakdown (P(win) and EV per scenario)
  </p>
  <div class="filter-row">
    <input class="search-bar" id="search" placeholder="Search rider or team…" />
    <select id="type-filter">
      <option value="">All archetypes</option>
      <option value="sprinter">Sprinter</option>
      <option value="gc_leader">GC Leader</option>
      <option value="breakaway_artist">Breakaway Artist</option>
      <option value="climber">Climber</option>
      <option value="puncheur">Puncheur</option>
      <option value="tt_specialist">TT Specialist</option>
      <option value="all_rounder">All Rounder</option>
    </select>
  </div>
  <div style="overflow-x:auto">
  <table class="ev-table" id="full-table">
    <thead><tr>
      <th data-col="name">Rider</th>
      <th data-col="team">Team</th>
      <th data-col="price">Price</th>
      <th data-col="s1_ev" class="ev-s1 sorted-desc">S1 EV</th>
      <th data-col="s2_ev">S2 EV</th>
      <th data-col="s3_ev">S3 EV</th>
      <th data-col="ev3s" class="ev-total">3-Stage EV</th>
      <th data-col="s1_p_win">P(win S1)%</th>
      <th data-col="archetype">Archetype</th>
      <th></th>
    </tr></thead>
    <tbody id="full-table-body"></tbody>
  </table>
  </div>
  <p id="table-count"></p>
</div>

<!-- ── §4 Odds Divergence ────────────────────────────────────────────────── -->
<div class="section">
  <h2>§4 — Odds Divergence Analysis</h2>
  {odds_section}
</div>

<!-- ── §5 DNS Riders ─────────────────────────────────────────────────────── -->
<div class="section">
  <h2>§5 — DNS Riders (Excluded)</h2>
  <table class="ev-table">
    <thead><tr><th>Rider</th><th>Team</th><th>holdet_id</th><th>Status</th></tr></thead>
    <tbody>{dns_rows}</tbody>
  </table>
</div>

<!-- ── §6 Transfer Cost ──────────────────────────────────────────────────── -->
<div class="section">
  <h2>§6 — Transfer Cost Formula (Future Reference)</h2>
  <div class="transfer-box">
    <p style="font-family:monospace;color:#79c0ff;white-space:pre-wrap;">Net EV(transfer) =
  EV(rider_in,  stages t→t+n)
− EV(rider_out, stages t→t+n)
− transfer_fee_in  (1% of buy price)
Stage 1 initial selection is FREE.</p>
  </div>
</div>

<!-- ── §7 Expert Intelligence ────────────────────────────────────────────── -->
<div class="section">
  <h2>§7 — Expert Intelligence (Stage 1)</h2>
  <p class="muted" style="margin-bottom:10px;font-size:12px">
    Gather Emil Axelgaard (TV2 Sport) + 4 secondary sources via Anthropic API.
    Applied as mode:adjust overrides — additive, capped at [0,1].
  </p>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
    <button class="intel-btn" onclick="toggleIntelCommands()">🔍 Gather Intelligence</button>
    <span style="font-size:11px;color:var(--muted)">
      Emil Axelgaard · VeloNews · CyclingNews · ProCyclingStats · FirstCycling
    </span>
  </div>
  <div id="intel-commands" style="display:none;background:var(--bg);border:1px solid var(--border);
       border-radius:6px;padding:12px;margin-bottom:10px;font-size:12px">
    <code>python3 scripts/gather_expert_intel.py --stage 1</code><br>
    <code>python3 scripts/apply_corrections_and_rebuild.py</code><br>
    <small style="color:var(--muted)">Then refresh this page.</small>
    <button onclick="toggleIntelCommands()"
            style="float:right;background:none;border:none;color:var(--muted);cursor:pointer">✕</button>
  </div>
  <div id="intel-summary" class="intel-panel">
    {_intel_panel_html(_intel_data) or "<p class='muted'>No intelligence gathered yet. Click 'Gather Intelligence' above.</p>"}
  </div>
</div>

<div class="footer">
  <p>Snapshot: {snap_ts} &nbsp;|&nbsp; Phase 3h+3i — scenario sliders, AFFINITY_POWER={{}}, point scales</p>
  <p style="margin-top:4px;">Submit team at <strong>holdet.dk</strong> before stage start</p>
</div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<script>
// Embedded data
const RIDERS   = {riders_json};
const BUDGET   = {BUDGET};
const MAX_TEAM = {MAX_PER_TEAM};
const STAGES_JS = {stages_js_data};
const SCENARIO_CFG = {scenario_cfg_json};
const S2_DEFAULTS = {json.dumps(s2_defaults)};
const S3_DEFAULTS = {json.dumps(s3_defaults)};
const AFFINITY_POWER = 8;

// Current scenario weights (Stage 1)
let W = {default_w_json};

const PRESETS = {{
  pure_sprint:  {{bunch_sprint:0.85, reduced_sprint:0.10, breakaway:0.05, gc_day:0.00}},
  sprint_risk:  {{bunch_sprint:0.50, reduced_sprint:0.30, breakaway:0.20, gc_day:0.00}},
  breakaway:    {{bunch_sprint:0.10, reduced_sprint:0.15, breakaway:0.75, gc_day:0.00}},
  mountain:     {{bunch_sprint:0.00, reduced_sprint:0.05, breakaway:0.25, gc_day:0.70}},
  open:         {{bunch_sprint:0.25, reduced_sprint:0.25, breakaway:0.25, gc_day:0.25}},
  default:      {{bunch_sprint:0.70, reduced_sprint:0.20, breakaway:0.10, gc_day:0.00}},
}};

const SCENARIO_COLORS = {{
  bunch_sprint:   "#2ecc71",
  reduced_sprint: "#f39c12",
  breakaway:      "#e74c3c",
  gc_day:         "#9b59b6",
}};

// ── Slider logic ──────────────────────────────────────────────────────────
function onSlider(scenario, rawValue) {{
  W[scenario] = parseInt(rawValue) / 100;
  document.getElementById(`val-${{scenario}}`).textContent = rawValue + "%";
  syncTotal();
  refreshAll();
}}

function preset(key) {{
  W = {{...PRESETS[key]}};
  for (const [s, w] of Object.entries(W)) {{
    const pct = Math.round(w * 100);
    document.getElementById(`sl-${{s}}`).value = pct;
    document.getElementById(`val-${{s}}`).textContent = pct + "%";
  }}
  syncTotal();
  refreshAll();
}}

function syncTotal() {{
  const total = Math.round(Object.values(W).reduce((a,b)=>a+b,0) * 100);
  document.getElementById("scenario-total").textContent = total + "%";
  const warn = document.getElementById("scenario-warning");
  warn.style.display = Math.abs(total - 100) > 2 ? "inline" : "none";
  document.getElementById("scenario-out-warning").style.display =
    Math.abs(total - 100) > 2 ? "block" : "none";
  renderScenarioBar();
}}

function isValid() {{
  return Math.abs(Object.values(W).reduce((a,b)=>a+b,0) - 1.0) <= 0.02;
}}

function renderScenarioBar() {{
  const bar = document.getElementById("scenario-bar");
  bar.innerHTML = Object.entries(W).map(([s, w]) =>
    w > 0.005
      ? `<span style="flex:${{w}};background:${{SCENARIO_COLORS[s]}};height:6px" title="${{SCENARIO_CFG[s].label}}: ${{Math.round(w*100)}}%"></span>`
      : ""
  ).join("");
}}

// ── EV computation ────────────────────────────────────────────────────────
function blendedS1EV(rider) {{
  return Math.round(Object.entries(W).reduce((sum,[s,w]) =>
    sum + w * (rider.s1_scenario_ev[s] || 0), 0));
}}

function blendedS1PWin(rider) {{
  return Object.entries(W).reduce((sum,[s,w]) =>
    sum + w * (rider.s1_scenario_p_win[s] || 0), 0);
}}

function totalEV(rider) {{
  return blendedS1EV(rider) + (rider.s2_ev||0) + (rider.s3_ev||0);
}}

// ── Team selection ────────────────────────────────────────────────────────
function selectTeam() {{
  if (!isValid()) return [];
  const active = RIDERS
    .filter(r => !r.is_out)
    .map(r => ({{...r, _ev1: blendedS1EV(r), _ev3: totalEV(r)}}))
    .sort((a,b) => b._ev3 - a._ev3);

  const team = [];
  let spent = 0;
  const counts = {{}};
  const minPrice = Math.min(...active.map(r=>r.price));

  for (const r of active) {{
    if (team.length >= 8) break;
    if ((counts[r.team]||0) >= MAX_TEAM) continue;
    const slotsLeft = 8 - team.length;
    if (spent + r.price + minPrice * (slotsLeft - 1) > BUDGET) continue;
    team.push(r);
    spent += r.price;
    counts[r.team] = (counts[r.team]||0) + 1;
  }}
  return team;
}}

// ── Rendering ─────────────────────────────────────────────────────────────
function fmt(n) {{
  return Math.round(n).toLocaleString("da-DK") + " kr";
}}

function archBadge(arch) {{
  const cls = {{
    sprinter:"badge-sprint", gc_leader:"badge-gc", breakaway_artist:"badge-break",
    climber:"badge-gc", puncheur:"badge-punchy", tt_specialist:"badge-dom", all_rounder:"badge-dom"
  }}[arch] || "badge-dom";
  return `<span class="badge ${{cls}}">${{arch}}</span>`;
}}

const openRows = new Set();

function scenarioDetailHtml(rider) {{
  const skeys = ["bunch_sprint","reduced_sprint","breakaway","gc_day"];
  const s1ev = skeys.map(s => rider.s1_scenario_ev[s]||0);
  const s1pw = skeys.map(s => (rider.s1_scenario_p_win[s]||0)*100);
  const s2ev = skeys.map(s => rider.s2_scenario_ev?.[s]||0);
  const s3ev = skeys.map(s => rider.s3_scenario_ev?.[s]||0);
  const blendS1 = blendedS1EV(rider);
  const blendPW = (blendedS1PWin(rider)*100).toFixed(1);
  const labels = skeys.map(s => SCENARIO_CFG[s].label);
  return `
    <div class="scenario-detail" style="margin-top:8px">
      <table class="scenario-detail-table">
        <tr><th></th><th style="color:#2ecc71">Bunch Sprint</th>
          <th style="color:#f39c12">Reduced Sprint</th>
          <th style="color:#e74c3c">Breakaway</th>
          <th style="color:#9b59b6">GC Day</th>
          <th>Blended</th></tr>
        <tr><td>S1 P(win)</td>
          ${{skeys.map((_,i)=>`<td>${{s1pw[i].toFixed(1)}}%</td>`).join("")}}
          <td><b>${{blendPW}}%</b></td></tr>
        <tr><td>S1 EV</td>
          ${{skeys.map((_,i)=>`<td>${{fmt(s1ev[i])}}</td>`).join("")}}
          <td><b>${{fmt(blendS1)}}</b></td></tr>
        <tr><td>S2 EV</td>
          ${{skeys.map((_,i)=>`<td style="color:var(--muted)">${{fmt(s2ev[i])}}</td>`).join("")}}
          <td><b>${{fmt(rider.s2_ev||0)}}</b></td></tr>
        <tr><td>S3 EV</td>
          ${{skeys.map((_,i)=>`<td style="color:var(--muted)">${{fmt(s3ev[i])}}</td>`).join("")}}
          <td><b>${{fmt(rider.s3_ev||0)}}</b></td></tr>
      </table>
    </div>`;
}}

function renderTeam() {{
  const team = selectTeam();
  if (!team.length) return;
  const spent = team.reduce((s,r)=>s+r.price, 0);
  const captain = team.reduce((best,r) => blendedS1EV(r) > blendedS1EV(best) ? r : best, team[0]);

  document.getElementById("budget-used").textContent = fmt(spent);
  const rem = BUDGET - spent;
  document.getElementById("budget-remaining").textContent = fmt(rem);
  document.getElementById("budget-remaining").style.color = rem > 2_000_000 ? "#2ea043" : "#f85149";

  const teamIds = new Set(team.map(r=>r.id));
  const tbody = document.getElementById("team-tbody");
  const frags = [];
  for (const r of team) {{
    const isCap = r.id === captain.id;
    const cls = isCap ? "captain-row rider-row-clickable" : "rec-row rider-row-clickable";
    const ev1 = blendedS1EV(r), ev3 = totalEV(r), pw = (blendedS1PWin(r)*100).toFixed(1);
    frags.push(`<tr class="${{cls}}" data-id="t-${{r.id}}">
      <td>${{r.name}}${{isCap?" ★":""}}</td>
      <td>${{r.team}}</td>
      <td>${{fmt(r.price)}}</td>
      <td class="ev-s1">${{fmt(ev1)}}</td>
      <td>${{fmt(r.s2_ev||0)}}</td>
      <td>${{fmt(r.s3_ev||0)}}</td>
      <td class="ev-total">${{fmt(ev3)}}</td>
      <td>${{pw}}%</td>
      <td>${{archBadge(r.archetype)}}</td>
    </tr>`);
    const isOpen = openRows.has("t-"+r.id);
    frags.push(`<tr class="rider-detail-row" style="display:${{isOpen?"table-row":"none"}}" data-detail="t-${{r.id}}">
      <td colspan="9"><div class="detail-box">${{scenarioDetailHtml(r)}}</div></td>
    </tr>`);
  }}
  tbody.innerHTML = frags.join("");
  tbody.querySelectorAll("tr.rider-row-clickable").forEach(row => {{
    row.addEventListener("click", () => toggleDetail(row.dataset.id, tbody));
  }});

  const ev3Total = team.reduce((s,r)=>s+totalEV(r),0);
  document.getElementById("team-summary").innerHTML =
    `Budget: <strong>${{fmt(spent)}} / {fmt(BUDGET)}</strong> &nbsp;|&nbsp;
     Captain: <strong>★ ${{captain.name}}</strong> &nbsp;|&nbsp;
     3-Stage EV: <strong class="ev-total">${{fmt(ev3Total)}}</strong>`;
}}

function renderFullTable() {{
  if (!isValid()) return;
  let rows = RIDERS.map(r => ({{...r, _ev1: blendedS1EV(r), _ev3: totalEV(r),
                                    _pw: blendedS1PWin(r)*100}}));
  const qText = (document.getElementById("search").value||"").toLowerCase();
  const qType = document.getElementById("type-filter").value;
  if (qText) rows = rows.filter(r => r.name.toLowerCase().includes(qText) || r.team.toLowerCase().includes(qText));
  if (qType) rows = rows.filter(r => r.archetype === qType);
  rows.sort((a,b) => {{
    let va = a[fullSortCol], vb = b[fullSortCol];
    if (fullSortCol==="s1_ev") {{va=a._ev1; vb=b._ev1;}}
    if (fullSortCol==="ev3s")  {{va=a._ev3; vb=b._ev3;}}
    if (fullSortCol==="s1_p_win"){{va=a._pw; vb=b._pw;}}
    if (typeof va==="string") {{va=va.toLowerCase(); vb=vb.toLowerCase();}}
    return fullSortDesc ? (vb>va?1:-1) : (va>vb?1:-1);
  }});

  const tbody = document.getElementById("full-table-body");
  const frags = [];
  rows.forEach(r => {{
    const ev1 = r._ev1, ev3 = r._ev3, pw = r._pw.toFixed(1);
    const isOpen = openRows.has("f-"+r.id);
    frags.push(`<tr class="rider-row-clickable" data-id="f-${{r.id}}">
      <td>${{r.name}}</td><td>${{r.team}}</td><td>${{fmt(r.price)}}</td>
      <td class="ev-s1">${{fmt(ev1)}}</td>
      <td>${{fmt(r.s2_ev||0)}}</td>
      <td>${{fmt(r.s3_ev||0)}}</td>
      <td class="ev-total">${{fmt(ev3)}}</td>
      <td>${{pw}}%</td>
      <td>${{archBadge(r.archetype)}}</td>
      <td class="expand-arrow">${{isOpen?"▼":"▶"}}</td>
    </tr>`);
    frags.push(`<tr class="rider-detail-row" style="display:${{isOpen?"table-row":"none"}}" data-detail="f-${{r.id}}">
      <td colspan="10"><div class="detail-box">${{scenarioDetailHtml(r)}}</div></td>
    </tr>`);
  }});
  tbody.innerHTML = frags.join("");
  tbody.querySelectorAll("tr.rider-row-clickable").forEach(row => {{
    row.addEventListener("click", () => toggleDetail(row.dataset.id, tbody));
  }});
  document.getElementById("table-count").textContent =
    `Showing ${{rows.length}} of ${{RIDERS.length}} active riders`;
}}

function toggleDetail(id, tbody) {{
  const detail = tbody.querySelector(`tr[data-detail="${{id}}"]`);
  const row    = tbody.querySelector(`tr[data-id="${{id}}"]`);
  if (!detail) return;
  const isOpen = detail.style.display === "table-row";
  detail.style.display = isOpen ? "none" : "table-row";
  const arr = row?.querySelector(".expand-arrow");
  if (arr) arr.textContent = isOpen ? "▶" : "▼";
  if (isOpen) openRows.delete(id); else openRows.add(id);
}}

let fullSortCol  = "s1_ev";
let fullSortDesc = true;

document.querySelectorAll("#full-table th[data-col]").forEach(th => {{
  th.addEventListener("click", () => {{
    if (fullSortCol===th.dataset.col) fullSortDesc=!fullSortDesc;
    else {{ fullSortCol=th.dataset.col; fullSortDesc=true; }}
    document.querySelectorAll("#full-table th").forEach(t => t.classList.remove("sorted-asc","sorted-desc"));
    th.classList.add(fullSortDesc?"sorted-desc":"sorted-asc");
    renderFullTable();
  }});
}});

document.getElementById("search").addEventListener("input", ()=>renderFullTable());
document.getElementById("type-filter").addEventListener("change", ()=>renderFullTable());

function refreshAll() {{
  if (!isValid()) return;
  renderTeam();
  renderFullTable();
}}

// ── Stage flipper ─────────────────────────────────────────────────────────
let currentStageIdx = 0;
function renderStage(stage) {{
  const wrap  = document.getElementById("stage-image-wrap");
  const meta  = document.getElementById("stage-meta");
  document.getElementById("stage-label").textContent = stage.label;
  wrap.innerHTML = stage.image_b64
    ? `<img src="${{stage.image_b64}}" alt="Stage ${{stage.number}} profile"
            style="width:100%;max-width:1050px;border-radius:6px;border:1px solid var(--border)">`
    : `<div class="stage-img-placeholder">Stage ${{stage.number}} image not found</div>`;
  meta.innerHTML = [
    `Group: ${{stage.group||"?"}}`, `Type: ${{stage.type||"?"}}`,
    `Distance: ${{stage.distance}} km`, `Finish: ${{stage.finish_type||"?"}}`,
    `Sprints: ${{stage.sprints}}`, `KOMs: ${{stage.koms}}`,
  ].map(t=>`<span>${{t}}</span>`).join("");
  document.getElementById("prev-stage").disabled = (currentStageIdx===0);
  document.getElementById("next-stage").disabled = (currentStageIdx===STAGES_JS.length-1);
}}
function flipStage(delta) {{
  currentStageIdx = Math.max(0, Math.min(STAGES_JS.length-1, currentStageIdx+delta));
  renderStage(STAGES_JS[currentStageIdx]);
}}
renderStage(STAGES_JS[0]);

// ── Intelligence panel toggle ─────────────────────────────────────────────
function toggleIntelCommands() {{
  const el = document.getElementById("intel-commands");
  el.style.display = el.style.display==="none" ? "block" : "none";
}}

// ── Initialise sliders ────────────────────────────────────────────────────
(function init() {{
  for (const [s, w] of Object.entries(W)) {{
    const pct = Math.round(w * 100);
    document.getElementById(`sl-${{s}}`).value = pct;
    document.getElementById(`val-${{s}}`).textContent = pct + "%";
  }}
  syncTotal();
  refreshAll();
}})();
</script>
</body>
</html>"""

OUT.write_text(html, encoding="utf-8")
print(f"\n✓ Dashboard → {OUT}")

# Quick sanity output
print(f"\nTop 5 (Stage 1, flat default weights):")
for r in rider_scenario_data[:5]:
    ev1 = blend_ev(r["s1_scenario_ev"], default_weights)
    print(f"  {r['name']:<30} S1={fmt(ev1):>14}  arch={r['archetype']}")
