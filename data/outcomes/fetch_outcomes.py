"""
Fetch and compile grand tour historical outcome archive (2020-2025).

Usage:
    python3 fetch_outcomes.py --race giro --year 2024
    python3 fetch_outcomes.py --all          # fetch all races/years

Output: data/outcomes/outcomes_grand_tours_2020_2025.json

Data contract:
    - Training data only — must not be written back as system outputs
    - No race outcome data may enter Layer 0 (Rider-Intrinsic)
    - Provenance declared per record

Sources:
    - ProCyclingStats: https://www.procyclingstats.com/race/{race}/{year}/stage-{n}
    - FirstCycling: https://firstcycling.com
"""

import json
import argparse
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

RACES = {
    "giro": "giro-d-italia",
    "tour": "tour-de-france",
    "vuelta": "vuelta-a-espana",
}
YEARS = list(range(2020, 2026))
OUT_PATH = Path("data/outcomes/outcomes_grand_tours_2020_2025.json")
RETRIEVED_AT = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

HEADERS = {"User-Agent": "holdet-v2 data pipeline / research use"}


def pcs_stage_url(race_slug: str, year: int, stage: int) -> str:
    return f"https://www.procyclingstats.com/race/{race_slug}/{year}/stage-{stage}"


def fetch_page(url: str) -> str:
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as e:
        print(f"  WARN fetch failed {url}: {e}")
        return ""


class PCSResultsParser(HTMLParser):
    """Minimal parser — extracts rider name, team, position from PCS result table."""

    def __init__(self):
        super().__init__()
        self.results = []
        self._in_table = False
        self._in_row = False
        self._cells = []
        self._current_cell = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "basic" in attrs.get("class", ""):
            self._in_table = True
        if self._in_table and tag == "tr":
            self._in_row = True
            self._cells = []
        if self._in_row and tag in ("td", "th"):
            self._current_cell = ""

    def handle_endtag(self, tag):
        if self._in_row and tag in ("td", "th"):
            self._cells.append(self._current_cell.strip())
        if self._in_table and tag == "tr" and self._in_row:
            self._in_row = False
            if len(self._cells) >= 3:
                self.results.append(self._cells[:])
            self._cells = []
        if tag == "table":
            self._in_table = False

    def handle_data(self, data):
        if self._in_row:
            self._current_cell += data


def parse_position(pos_str: str):
    pos_str = pos_str.strip()
    if pos_str.isdigit():
        return int(pos_str), "FINISH"
    if pos_str.upper() in ("DNF", "DNS", "DSQ", "OTL"):
        return None, pos_str.upper()
    return None, "FINISH"


def scrape_stage(race_key: str, year: int, stage_num: int) -> list:
    """Scrape one stage result page. Returns list of outcome dicts."""
    race_slug = RACES[race_key]
    url = pcs_stage_url(race_slug, year, stage_num)
    html = fetch_page(url)
    if not html:
        return []

    parser = PCSResultsParser()
    parser.feed(html)

    outcomes = []
    for row in parser.results:
        if not row or not row[0].strip().lstrip("-").isdigit():
            continue
        try:
            pos_str = row[0].strip()
            rider_name = row[1].strip() if len(row) > 1 else "Unknown"
            team = row[2].strip() if len(row) > 2 else "Unknown"
            pos, status = parse_position(pos_str)

            outcomes.append({
                "race_id": f"{race_key}{year}",
                "year": year,
                "stage_number": stage_num,
                "rider_id": rider_name.lower().replace(" ", "_").replace("'", ""),
                "rider_name": rider_name,
                "team": team,
                "finish_status": status,
                "stage_position": pos,
                "time_gap_seconds": None,
                "late_arrival_minutes": None,
                "gc_position": None,
                "sprint_points": 0,
                "kom_points": 0,
                "jersey_yellow": False,
                "jersey_green": False,
                "jersey_kom": False,
                "jersey_white": False,
                "most_aggressive": False,
                "provenance": {
                    "source": f"procyclingstats.com {url}",
                    "retrieved_at": RETRIEVED_AT,
                },
            })
        except (IndexError, ValueError):
            continue

    time.sleep(1.5)  # polite rate limiting
    return outcomes


def fetch_all(race_keys=None, years=None):
    if race_keys is None:
        race_keys = list(RACES.keys())
    if years is None:
        years = YEARS

    all_outcomes = []
    for race_key in race_keys:
        for year in years:
            print(f"Fetching {race_key} {year}...")
            for stage_num in range(1, 22):
                print(f"  Stage {stage_num}", end=" ")
                results = scrape_stage(race_key, year, stage_num)
                if not results:
                    print("(no data)")
                    break
                all_outcomes.extend(results)
                print(f"({len(results)} riders)")

    return all_outcomes


def save(outcomes: list, path: Path):
    output = {
        "meta": {
            "description": "Grand tour historical outcomes 2020-2025 — training data only",
            "races": ["giro", "tour", "vuelta"],
            "years": list(YEARS),
            "record_count": len(outcomes),
            "generated_at": RETRIEVED_AT,
            "compliance_note": (
                "TRAINING DATA ONLY. Must not be written back as system outputs. "
                "Must not enter Layer 0 (Rider-Intrinsic). "
                "Outcome data is prohibited from all Layer 0 attributes regardless of age."
            ),
        },
        "outcomes": outcomes,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(outcomes)} records to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", choices=list(RACES.keys()), help="Single race")
    parser.add_argument("--year", type=int, help="Single year")
    parser.add_argument("--all", action="store_true", help="Fetch all races and years")
    args = parser.parse_args()

    if args.all:
        outcomes = fetch_all()
    elif args.race and args.year:
        outcomes = fetch_all(race_keys=[args.race], years=[args.year])
    elif args.race:
        outcomes = fetch_all(race_keys=[args.race])
    elif args.year:
        outcomes = fetch_all(years=[args.year])
    else:
        print("Usage: python3 fetch_outcomes.py --all  OR  --race giro --year 2024")
        print("Run with --all to fetch the complete 2020-2025 archive.")
        return

    save(outcomes, OUT_PATH)


if __name__ == "__main__":
    main()
