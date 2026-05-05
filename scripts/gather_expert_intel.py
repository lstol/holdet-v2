#!/usr/bin/env python3
"""
Gather expert intelligence for a Giro stage from Emil Axelgaard (TV2 Sport)
and 4 secondary sources, then write mode:adjust overrides to the YAML.

Usage:
  python3 scripts/gather_expert_intel.py --stage 1
  python3 scripts/gather_expert_intel.py --stage 2 --dry-run

Primary source: Emil Axelgaard articles on sport.tv2.dk
Secondary sources (via Anthropic web_search):
  - VeloNews stage preview
  - CyclingNews stage preview
  - ProCyclingStats pre-race odds/notes
  - FirstCycling stage notes

Output:
  data/intelligence/stage{N}_expert_intel.yaml  — raw signals per rider
  data/overrides/rider_attribute_overrides.yaml — mode:adjust entries appended/updated
"""

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parent.parent

RIDERS_FILE   = BASE / "data/riders/riders_giro2026_v1.json"
ROADBOOK_FILE = BASE / "data/stages/stage_roadbook.json"
OVERRIDES_FILE = BASE / "data/overrides/rider_attribute_overrides.yaml"
INTEL_DIR     = BASE / "data/intelligence"

# Priority order for sort in YAML: lower number = applied first (last applied wins)
SORT_ORDER = {"manual": 2, "expert_intel": 1, "copilot_research": 0, "web_search": 0}

# Source weights for multi-source merging
SOURCE_WEIGHTS = {
    "tv2_sport_axelgaard": 1.5,  # primary expert source, higher weight
    "velonews":            1.0,
    "cyclingnews":         1.0,
    "procyclingstats":     0.8,
    "firstcycling":        0.8,
}

AGREEMENT_AMPLIFIER = 1.2  # cap amplification at this factor
AGREEMENT_CAP       = 0.20  # max total adjustment magnitude
CONFLICT_DAMPENER   = 0.5


# ── Name normalisation ────────────────────────────────────────────────────────
def _norm(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def build_rider_index(riders: list[dict]) -> dict[str, dict]:
    """Map normalised name → rider dict."""
    idx = {}
    for r in riders:
        idx[_norm(r["name"])] = r
    return idx


def find_rider(name: str, idx: dict[str, dict]) -> dict | None:
    n = _norm(name)
    if n in idx:
        return idx[n]
    # Last-name match
    for k, r in idx.items():
        if k.split()[-1] == n.split()[-1]:
            return r
    return None


# ── TV2 Sport scraping via Anthropic API ──────────────────────────────────────
def fetch_tv2_axelgaard(stage_n: int, client: anthropic.Anthropic) -> str:
    """
    Fetch Emil Axelgaard's stage preview from TV2 Sport using Anthropic web_search.
    Returns raw text of the article or empty string if not found.
    """
    query = f"Emil Axelgaard Giro 2026 etape {stage_n} TV2 Sport site:sport.tv2.dk"
    prompt = (
        f"Search for Emil Axelgaard's preview article for Stage {stage_n} of the Giro d'Italia 2026 "
        f"on TV2 Sport (sport.tv2.dk). "
        f"Return the full article text if found, or 'NOT FOUND' if no relevant article exists. "
        f"Search query: {query}"
    )
    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [
            b.text for b in response.content
            if hasattr(b, "text") and b.type == "text"
        ]
        return "\n".join(text_parts)
    except Exception as e:
        print(f"  [TV2] Error: {e}")
        return ""


def fetch_secondary_source(source_name: str, stage_n: int, client: anthropic.Anthropic) -> str:
    """Fetch a secondary source preview via web_search."""
    queries = {
        "velonews":       f"VeloNews Giro 2026 stage {stage_n} preview",
        "cyclingnews":    f"CyclingNews Giro 2026 stage {stage_n} preview",
        "procyclingstats": f"ProCyclingStats Giro d'Italia 2026 stage {stage_n}",
        "firstcycling":   f"FirstCycling Giro d'Italia 2026 stage {stage_n} notes",
    }
    query = queries.get(source_name, f"Giro 2026 stage {stage_n} preview")
    prompt = (
        f"Search for the Giro d'Italia 2026 Stage {stage_n} preview from {source_name}. "
        f"Focus on: which riders are favoured, form notes, team tactics, breakaway candidates. "
        f"Search query: {query}. "
        f"Return relevant rider-specific notes only."
    )
    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [
            b.text for b in response.content
            if hasattr(b, "text") and b.type == "text"
        ]
        return "\n".join(text_parts)
    except Exception as e:
        print(f"  [{source_name}] Error: {e}")
        return ""


# ── Signal extraction ─────────────────────────────────────────────────────────
EXTRACTION_SCHEMA = """\
For each rider mentioned with a form or tactical note, output one JSON object per line:
{
  "rider_name": "Full Name",
  "attribute": "sprint_affinity|climbing_affinity|puncheur_affinity|breakaway_affinity|gc_affinity|tt_affinity",
  "direction": "up|down|neutral",
  "magnitude": 0.05,
  "confidence": "high|medium|low",
  "reason": "one-line reason"
}
magnitude: 0.03=minor, 0.05=moderate, 0.10=major, 0.15=very strong signal
Only output riders with clear directional signals. Do not invent signals.
Output ONLY the JSON lines, no prose."""


def extract_signals(source_text: str, source_name: str, stage_n: int, finish_type: str,
                    client: anthropic.Anthropic) -> list[dict]:
    """Ask Claude to extract structured rider signals from source text."""
    if not source_text or "NOT FOUND" in source_text:
        return []

    prompt = (
        f"You are extracting rider form signals from a cycling expert's stage preview.\n"
        f"Stage {stage_n} finish type: {finish_type}\n\n"
        f"Source ({source_name}):\n{source_text[:6000]}\n\n"
        f"{EXTRACTION_SCHEMA}"
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text if response.content else ""
        signals = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                sig = json.loads(line)
                sig["source"] = source_name
                signals.append(sig)
            except json.JSONDecodeError:
                continue
        return signals
    except Exception as e:
        print(f"  [extract] Error from {source_name}: {e}")
        return []


# ── Multi-source signal merging ───────────────────────────────────────────────
def merge_signals(all_signals: list[dict]) -> dict[tuple[str, str], dict]:
    """
    Group signals by (rider_name, attribute), merge with weighted average.
    Agreement between sources amplifies; conflict dampens.
    Returns dict keyed by (rider_name, attribute) → merged signal.
    """
    from collections import defaultdict
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for sig in all_signals:
        key = (_norm(sig["rider_name"]), sig["attribute"])
        groups[key].append(sig)

    merged = {}
    for (rider_norm, attr), sigs in groups.items():
        weight_map = {"high": 1.0, "medium": 0.7, "low": 0.4}
        total_w = 0.0
        total_adj = 0.0

        for sig in sigs:
            sw = SOURCE_WEIGHTS.get(sig["source"], 1.0)
            cw = weight_map.get(sig.get("confidence", "medium"), 0.7)
            w  = sw * cw
            mag = sig.get("magnitude", 0.05)
            direction = sig.get("direction", "neutral")
            if direction == "up":
                adj = +mag
            elif direction == "down":
                adj = -mag
            else:
                adj = 0.0
            total_w   += w
            total_adj += w * adj

        if total_w == 0:
            continue

        raw_adj = total_adj / total_w

        # Check agreement: what fraction of sources agree on direction?
        directions = [s["direction"] for s in sigs if s["direction"] != "neutral"]
        if directions:
            dominant = max(set(directions), key=directions.count)
            agree_frac = directions.count(dominant) / len(directions)
            if agree_frac >= 0.75 and len(sigs) >= 2:
                raw_adj *= AGREEMENT_AMPLIFIER
            elif agree_frac <= 0.5 and len(directions) >= 2:
                raw_adj *= CONFLICT_DAMPENER

        # Cap total magnitude
        raw_adj = max(-AGREEMENT_CAP, min(AGREEMENT_CAP, raw_adj))

        # Round to 2dp
        adjustment = round(raw_adj, 2)
        if adjustment == 0.0:
            continue

        rider_name = sigs[0]["rider_name"]  # use first occurrence's casing
        reasons = list({s.get("reason", "") for s in sigs if s.get("reason")})
        sources = list({s["source"] for s in sigs})

        merged[(rider_norm, attr)] = {
            "rider_name": rider_name,
            "attribute":  attr,
            "adjustment": adjustment,
            "n_sources":  len(sigs),
            "sources":    sources,
            "reasons":    reasons,
        }

    return merged


# ── Override writing ──────────────────────────────────────────────────────────
def load_overrides() -> list[dict]:
    if not OVERRIDES_FILE.exists():
        return []
    raw = yaml.safe_load(OVERRIDES_FILE.read_text()) or {}
    return raw.get("overrides", [])


def save_overrides(overrides: list[dict]) -> None:
    # Sort by priority: manual=2 first in display, then expert_intel=1, then rest
    # But for load_rider_attributes() application order (last wins), we want
    # lower-priority sources first in the file, so manual entries are last applied.
    # Sort descending by priority so manual appears at top of file (written last in apply loop).
    # Actually: file order doesn't matter — load_rider_attributes() sorts by source at runtime.
    # We sort for human readability: manual first, then expert_intel, then copilot/web.
    priority = lambda o: -SORT_ORDER.get(o.get("source", ""), 0)
    overrides.sort(key=lambda o: (priority(o), o.get("holdet_id", 0), o.get("attribute", "")))
    OVERRIDES_FILE.write_text(yaml.dump(
        {"overrides": overrides},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    ))


def remove_old_expert_intel(overrides: list[dict], stage_n: int) -> list[dict]:
    """Remove existing expert_intel entries for this stage before re-writing."""
    return [
        o for o in overrides
        if not (
            o.get("source") == "expert_intel"
            and o.get("stage_first_applicable") == stage_n
        )
    ]


def write_intel_overrides(
    merged: dict[tuple, dict],
    stage_n: int,
    rider_idx: dict[str, dict],
    overrides: list[dict],
    dry_run: bool,
) -> list[dict]:
    """Convert merged signals to mode:adjust override entries and merge into overrides list."""
    new_entries = []
    today = date.today().isoformat()

    for (rider_norm, attr), sig in merged.items():
        rider = find_rider(sig["rider_name"], rider_idx)
        if not rider:
            print(f"  [SKIP] Could not match rider: {sig['rider_name']}")
            continue
        if not rider.get("holdet_id"):
            print(f"  [SKIP] No holdet_id for: {rider['name']}")
            continue

        entry = {
            "holdet_id":             rider["holdet_id"],
            "name":                  rider["name"],
            "attribute":             attr,
            "mode":                  "adjust",
            "adjustment":            sig["adjustment"],
            "source":                "expert_intel",
            "stage_first_applicable": stage_n,
            "stage_last_applicable": stage_n,
            "date":                  today,
            "sources":               sig["sources"],
            "reasons":               sig["reasons"][:2],  # keep max 2 reasons
        }
        new_entries.append(entry)
        direction = "+" if sig["adjustment"] > 0 else ""
        print(f"  {rider['name']:<30} {attr:<20} {direction}{sig['adjustment']:+.2f}"
              f"  ({', '.join(sig['sources'])})")

    if dry_run:
        print(f"\n[DRY RUN] Would write {len(new_entries)} expert_intel entries for stage {stage_n}")
        return overrides

    cleaned = remove_old_expert_intel(overrides, stage_n)
    return cleaned + new_entries


# ── Intel YAML output ─────────────────────────────────────────────────────────
def save_intel_yaml(
    stage_n: int,
    finish_type: str,
    all_signals: list[dict],
    merged: dict[tuple, dict],
) -> None:
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "stage":         stage_n,
        "finish_type":   finish_type,
        "date_gathered": date.today().isoformat(),
        "raw_signals":   all_signals,
        "merged": [
            {
                "rider":      v["rider_name"],
                "attribute":  v["attribute"],
                "adjustment": v["adjustment"],
                "n_sources":  v["n_sources"],
                "sources":    v["sources"],
                "reasons":    v["reasons"],
            }
            for v in merged.values()
        ],
    }
    path = INTEL_DIR / f"stage{stage_n}_expert_intel.yaml"
    path.write_text(yaml.dump(out, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"\nSaved intel: {path.relative_to(BASE)}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-secondary", action="store_true",
                        help="Only fetch TV2/Axelgaard, skip 4 secondary sources")
    args = parser.parse_args()

    stage_n = args.stage

    # Load stage roadbook
    roadbooks = {r["stage"]: r for r in json.loads(ROADBOOK_FILE.read_text())}
    rb = roadbooks.get(stage_n)
    if not rb:
        print(f"Stage {stage_n} not found in roadbook.")
        return
    finish_type = rb.get("finish_type", "sprint")

    # Load riders
    riders_raw = json.loads(RIDERS_FILE.read_text())["riders"]
    active = [r for r in riders_raw if r.get("status") == "active" and r.get("holdet_id")]
    rider_idx = build_rider_index(active)

    client = anthropic.Anthropic()

    print(f"\n=== Expert intelligence gathering: Stage {stage_n} ({finish_type}) ===\n")

    # 1. Fetch TV2 / Emil Axelgaard
    print("Fetching TV2 Sport / Emil Axelgaard...")
    tv2_text = fetch_tv2_axelgaard(stage_n, client)
    tv2_signals = extract_signals(tv2_text, "tv2_sport_axelgaard", stage_n, finish_type, client)
    print(f"  → {len(tv2_signals)} signals extracted")

    all_signals = list(tv2_signals)

    # 2. Fetch secondary sources
    if not args.skip_secondary:
        secondary_sources = ["velonews", "cyclingnews", "procyclingstats", "firstcycling"]
        for src in secondary_sources:
            print(f"Fetching {src}...")
            text = fetch_secondary_source(src, stage_n, client)
            sigs = extract_signals(text, src, stage_n, finish_type, client)
            print(f"  → {len(sigs)} signals extracted")
            all_signals.extend(sigs)

    if not all_signals:
        print("\nNo signals found — no overrides written.")
        return

    print(f"\nTotal raw signals: {len(all_signals)}")

    # 3. Merge signals
    merged = merge_signals(all_signals)
    print(f"Merged into {len(merged)} unique (rider, attribute) adjustments:\n")

    # 4. Save intel YAML
    save_intel_yaml(stage_n, finish_type, all_signals, merged)

    # 5. Write overrides
    overrides = load_overrides()
    overrides = write_intel_overrides(merged, stage_n, rider_idx, overrides, args.dry_run)

    if not args.dry_run:
        save_overrides(overrides)
        expert_count = sum(1 for o in overrides if o.get("source") == "expert_intel")
        print(f"\n✓ Wrote {len(merged)} expert_intel overrides (stage {stage_n})")
        print(f"  Total expert_intel entries in file: {expert_count}")
        print(f"\nNext: rebuild EVs with:")
        print(f"  python3 scripts/apply_corrections_and_rebuild.py")


if __name__ == "__main__":
    main()
