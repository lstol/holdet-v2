#!/usr/bin/env python3
"""
Research riders using Anthropic API with web search.
Extracts Layer 0 attributes from real rider profiles and race history.
Writes results to data/overrides/rider_attribute_overrides.yaml.

Usage:
  python3 scripts/gather_rider_intelligence.py --stage-type sprint
  python3 scripts/gather_rider_intelligence.py --stage-type mountain
  python3 scripts/gather_rider_intelligence.py --rider-id 47373
  python3 scripts/gather_rider_intelligence.py --all
"""

import anthropic, json, re, time, yaml, argparse
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv()


client = anthropic.Anthropic()

ATTRIBUTE_SCHEMA = """
{
  "sprint_affinity":    <float 0.0-1.0>,
  "climbing_affinity":  <float 0.0-1.0>,
  "puncheur_affinity":  <float 0.0-1.0>,
  "gc_affinity":        <float 0.0-1.0>,
  "breakaway_affinity": <float 0.0-1.0>,
  "tt_affinity":        <float 0.0-1.0>,
  "rider_type": <"sprinter"|"climber"|"puncheur"|"gc_leader"|"breakaway_artist"|"domestique"|"all_rounder"|"tt_specialist">,
  "team_role":  <"protected_leader"|"sprint_lead"|"lead_out"|"domestique"|"support">,
  "stage_win_types": [<"sprint"|"mountain"|"hilly"|"itt"|"breakaway">],
  "notable_results": "<2-3 sentence summary of key results and palmares>",
  "giro_role_2026":  "<what is this rider's role and goal at the 2026 Giro specifically>",
  "confidence": <"high"|"medium"|"low">
}
"""

RESEARCH_PROMPT = """Research the professional cyclist {name} who rides for {team}.

Use web search to find:
1. Their racing specialty (sprinter, climber, puncheur, GC rider, breakaway artist, domestique, TT specialist)
2. Their key results and palmares (stage wins, GC results, classics results)
3. Their role on their team (protected leader, sprint lead-out, domestique, etc.)
4. Their likely role at the 2026 Giro d'Italia specifically

Then return ONLY a JSON object with this exact schema, no other text:

{schema}

Scoring guide for affinities (0.0 = none, 1.0 = world class):
- sprint_affinity:    0.85+ = world-class sprinter (Cavendish, Milan level)
                      0.70-0.84 = reliable sprint finisher, wins regularly
                      0.50-0.69 = can sprint, wins occasionally or in smaller races
                      < 0.50 = not a sprinter
- climbing_affinity:  0.85+ = mountain specialist, wins summit finishes
                      0.70-0.84 = strong climber, GC capable
                      0.50-0.69 = decent climber, survives mountains
                      < 0.50 = loses time in mountains
- puncheur_affinity:  ability to win hilly/punchy finishes, one-day classics
- gc_affinity:        likelihood of being a genuine GC contender (top 10 overall)
- breakaway_affinity: tendency to ride in breakaways and ability to succeed in them
- tt_affinity:        time trial ability relative to peloton
- confidence:         high = clear specialist with strong results record
                      medium = some ambiguity or limited results
                      low = unclear specialty or very limited information found"""


def research_rider(name: str, team: str) -> dict:
    prompt = RESEARCH_PROMPT.format(name=name, team=team, schema=ATTRIBUTE_SCHEMA)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")

    # Strip markdown code fences if present
    if "```" in text:
        text = re.sub(r"```(?:json)?\n?", "", text)

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON in response: {text[:300]}")

    return json.loads(json_match.group())


def attrs_to_overrides(holdet_id: int, name: str, team: str,
                       attrs: dict, stage_first: int = 1) -> list[dict]:
    today = date.today().isoformat()
    attribute_keys = [
        "sprint_affinity", "climbing_affinity", "puncheur_affinity",
        "gc_affinity", "breakaway_affinity", "tt_affinity",
    ]
    result = []
    for key in attribute_keys:
        if key in attrs:
            result.append({
                "holdet_id":               holdet_id,
                "name":                    name,
                "attribute":               key,
                "value":                   round(float(attrs[key]), 2),
                "reason": (
                    f"Web search intelligence. "
                    f"rider_type={attrs.get('rider_type', 'unknown')}, "
                    f"team_role={attrs.get('team_role', 'unknown')}. "
                    f"{attrs.get('notable_results', '')}"
                ),
                "giro_role_2026":          attrs.get("giro_role_2026", ""),
                "source":                  "web_search",
                "confidence":              attrs.get("confidence", "medium"),
                "stage_first_applicable":  stage_first,
                "date":                    today,
            })
    return result


def load_existing(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {"overrides": []}
    return {"overrides": []}


def save_overrides(data: dict, path: Path) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False))


def already_researched(holdet_id: int, existing: dict) -> bool:
    return any(
        o["holdet_id"] == holdet_id and o.get("source") == "web_search"
        for o in existing.get("overrides", [])
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-type", choices=["sprint", "hilly", "mountain", "itt", "all"])
    parser.add_argument("--rider-id", type=int, help="Research a single rider by holdet_id")
    parser.add_argument("--all", action="store_true", dest="all_riders")
    parser.add_argument("--force", action="store_true",
                        help="Re-research riders already in override file")
    args = parser.parse_args()

    data        = json.loads((BASE / "data/riders/riders_giro2026_v1.json").read_text())
    all_riders  = data["riders"]
    active      = [r for r in all_riders
                   if r.get("status") == "active" and r.get("holdet_id")]

    overrides_path = BASE / "data/overrides/rider_attribute_overrides.yaml"
    existing       = load_existing(overrides_path)

    def ta(r):
        return r.get("terrain_affinity", {})

    # Select riders to research
    if args.rider_id:
        to_research = [r for r in active if r.get("holdet_id") == args.rider_id]
        if not to_research:
            print(f"No active rider with holdet_id={args.rider_id}")
            return
    elif args.stage_type == "sprint":
        to_research = [r for r in active if ta(r).get("sprint", 0) > 0.40]
        print(f"Sprint stage: {len(to_research)} riders with sprint > 0.40")
    elif args.stage_type == "hilly":
        to_research = [r for r in active
                       if ta(r).get("mixed", 0) > 0.40 or ta(r).get("climbing", 0) > 0.40]
        print(f"Hilly stage: {len(to_research)} riders with mixed/climbing > 0.40")
    elif args.stage_type == "mountain":
        to_research = [r for r in active
                       if ta(r).get("climbing", 0) > 0.40]
        print(f"Mountain stage: {len(to_research)} riders with climbing > 0.40")
    elif args.stage_type == "itt":
        to_research = [r for r in active if ta(r).get("time_trial", 0) > 0.50]
        print(f"ITT stage: {len(to_research)} riders with time_trial > 0.50")
    elif args.all_riders:
        to_research = active
        print(f"Full field: {len(to_research)} active riders")
    else:
        parser.print_help()
        return

    if not args.force:
        before = len(to_research)
        to_research = [r for r in to_research
                       if not already_researched(r["holdet_id"], existing)]
        skipped = before - len(to_research)
        if skipped:
            print(f"Skipping {skipped} already-researched riders. Remaining: {len(to_research)}")

    if not to_research:
        print("Nothing to research. Use --force to re-research existing riders.")
        return

    print(f"Estimated time: ~{len(to_research) * 15}s\n")

    new_overrides: list[dict] = []
    errors:        list[dict] = []

    for i, rider in enumerate(to_research):
        name = rider["name"]
        team = rider.get("team", "unknown")
        hid  = rider["holdet_id"]
        print(f"[{i+1}/{len(to_research)}] {name} ({team})...", end=" ", flush=True)

        try:
            attrs = research_rider(name, team)
            rider_overrides = attrs_to_overrides(hid, name, team, attrs)
            new_overrides.extend(rider_overrides)
            print(
                f"✓ {attrs.get('rider_type', '?')} "
                f"(sprint={attrs.get('sprint_affinity', '?')}, "
                f"climb={attrs.get('climbing_affinity', '?')}, "
                f"conf={attrs.get('confidence', '?')})"
            )
        except Exception as e:
            print(f"✗ {e}")
            errors.append({"rider": name, "holdet_id": hid, "error": str(e)})

        time.sleep(2)

    # Merge: new overrides replace old ones for same rider+attribute
    kept = [o for o in existing.get("overrides", [])
            if (o["holdet_id"], o["attribute"])
            not in {(n["holdet_id"], n["attribute"]) for n in new_overrides}]
    merged = {"overrides": kept + new_overrides}
    save_overrides(merged, overrides_path)

    print(f"\n✓ {len(new_overrides)} overrides written → {overrides_path}")
    if errors:
        print(f"✗ {len(errors)} errors:")
        for e in errors:
            print(f"  holdet_id={e['holdet_id']} {e['rider']}: {e['error']}")
    print("\nNext: python3 scripts/apply_corrections_and_rebuild.py")


if __name__ == "__main__":
    main()
