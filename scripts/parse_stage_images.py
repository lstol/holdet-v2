#!/usr/bin/env python3
"""
Parse all 21 Giro 2026 stage profile images using Claude vision.
Outputs: data/stages/stage_profiles_parsed.json
"""

import anthropic, base64, json, sys
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
IMAGES = BASE / "data" / "stage_images"
OUT    = BASE / "data" / "stages" / "stage_profiles_parsed.json"

import os
_key   = os.environ.get("ANTHROPIC_API_KEY", "")
_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
if _key:
    client = anthropic.Anthropic(api_key=_key)
elif _token:
    client = anthropic.Anthropic(auth_token=_token)
else:
    raise RuntimeError("No Anthropic credentials found. Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN.")

PROMPT = """You are reading an official Giro d'Italia 2026 stage profile image.

Extract the following and return ONLY valid JSON, no other text:

{
  "stage": <int>,
  "distance_km": <float>,
  "stage_type": <"flat"|"hilly"|"mountain"|"itt"|"ttt">,
  "finish_type": <"sprint"|"uphill"|"summit"|"tt"|"ttt">,
  "intermediate_sprints": [
    {"km": <float>, "points_available": <int>, "label": "<string or null>"}
  ],
  "kom_climbs": [
    {"km": <float>, "category": <1|2|3|4|"HC">, "points_available": <int>, "name": "<string or null>"}
  ],
  "final_climb_gradient_pct": <float or null>,
  "notes": "<any other relevant observation>"
}

Rules:
- intermediate_sprints: include ALL sprint point markers visible (green triangle, sprint banner,
  or "GV"/"GPM" symbols). Include the finish if it is a flat/bunch sprint stage.
- kom_climbs: include ALL mountain point markers (red or dotted triangle, KOM symbol).
  Category is the number shown (1, 2, 3, 4) or HC. Points_available is the integer printed
  next to the marker. If not visible, use 8 for Cat1, 5 for Cat2, 3 for Cat3, 1 for Cat4.
- intermediate_sprints points_available: sprint finish points are typically 25/18/15/12/10/8/6/4/2/1.
  Intermediate sprints typically award 3/2/1. Use visible value or best estimate.
- If a value cannot be determined from the image, use null.
- Do not invent values not visible in the image."""


def parse_stage(n: int) -> dict:
    img_path = IMAGES / f"stage-{n}.jpg"
    if not img_path.exists():
        return {"stage": n, "error": "image not found",
                "intermediate_sprints": [], "kom_climbs": []}

    img_data = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data}},
                {"type": "text", "text": PROMPT},
            ]
        }]
    )

    raw = resp.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[:-3]
    parsed = json.loads(raw)
    # Ensure required list fields are never null
    parsed.setdefault("intermediate_sprints", [])
    parsed.setdefault("kom_climbs", [])
    if parsed["intermediate_sprints"] is None:
        parsed["intermediate_sprints"] = []
    if parsed["kom_climbs"] is None:
        parsed["kom_climbs"] = []
    return parsed


def main():
    results = []
    for n in range(1, 22):
        sys.stdout.write(f"  Parsing stage {n:2d}/21 … ")
        sys.stdout.flush()
        try:
            data = parse_stage(n)
            sp = len(data.get("intermediate_sprints", []))
            km = len(data.get("kom_climbs", []))
            print(f"OK  sprints={sp} koms={km}")
        except Exception as e:
            print(f"ERROR: {e}")
            data = {"stage": n, "error": str(e),
                    "intermediate_sprints": [], "kom_climbs": []}
        results.append(data)

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n✓ Saved → {OUT}")


if __name__ == "__main__":
    main()
