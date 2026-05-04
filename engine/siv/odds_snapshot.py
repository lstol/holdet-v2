"""
Odds snapshot pipeline — capture bookmaker odds at T0 before each stage.

Usage:
    python3 engine/siv/odds_snapshot.py --stage 1
    python3 engine/siv/odds_snapshot.py --stage 7 --source oddschecker

Output: data/odds/odds_giro2026_stage{N}_T0.json

CONSTRAINT REMINDER (contracts/v2.0/01_system_canonical.md §3):
    Odds are BENCHMARK ONLY. They must NEVER be used as:
    - Layer 0 (Rider-Intrinsic) inputs
    - Layer 3 (Probability) inputs or calibration targets
    - Feature inputs at any layer
    The sole permitted use is post-hoc divergence analysis for human review.
"""

import json
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

CONSTRAINT_REMINDER = (
    "BENCHMARK ONLY — not a model input or calibration target"
)

HEADERS = {"User-Agent": "holdet-v2 odds snapshot / research use"}


def snapshot_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_snapshot(stage_num: int, source: str, ts: str) -> dict:
    return {
        "race_id": "giro2026",
        "stage_number": stage_num,
        "snapshot_timestamp": ts,
        "source": source,
        "constraint_reminder": CONSTRAINT_REMINDER,
        "stage_win_odds": [],
        "top3_odds": [],
        "top10_odds": [],
    }


def decimal_to_implied(decimal_odds: float) -> float:
    if decimal_odds <= 0:
        return 0.0
    return round(1.0 / decimal_odds, 6)


class OddscheckerParser(HTMLParser):
    """Extracts stage-win odds rows from Oddschecker cycling pages."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_table = False
        self._cells = []
        self._current = ""
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if tag == "table" and ("odds" in cls or "coupon" in cls):
            self._in_table = True
            self._depth = 0
        if self._in_table:
            if tag == "tr":
                self._cells = []
            if tag in ("td", "th"):
                self._current = ""

    def handle_endtag(self, tag):
        if self._in_table:
            if tag in ("td", "th"):
                self._cells.append(self._current.strip())
            if tag == "tr" and self._cells:
                self.rows.append(list(self._cells))
                self._cells = []
            if tag == "table":
                self._in_table = False

    def handle_data(self, data):
        if self._in_table:
            self._current += data.strip()


def fetch_oddschecker(stage_num: int) -> list:
    """
    Fetch stage-win odds from Oddschecker.
    Returns list of {rider_name, decimal_odds, implied_probability}.

    NOTE: Oddschecker blocks automated access; this function provides the
    parsing skeleton. In practice, use a headless browser or the manually
    saved page HTML passed via --html-file argument.
    """
    url = f"https://www.oddschecker.com/cycling/giro-d-italia/stage-{stage_num}-winner"
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as e:
        print(f"  WARN: Could not fetch {url}: {e}")
        print("  TIP: Save the page HTML manually and pass via --html-file")
        return []

    parser = OddscheckerParser()
    parser.feed(html)

    results = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        try:
            name = row[0]
            odds_str = row[1].replace(",", ".")
            decimal_odds = float(odds_str)
            results.append({
                "rider_name": name,
                "decimal_odds": decimal_odds,
                "implied_probability": decimal_to_implied(decimal_odds),
            })
        except (ValueError, IndexError):
            continue

    return results


def parse_html_file(path: str) -> list:
    """Parse a manually-saved HTML page for odds data."""
    with open(path) as f:
        html = f.read()
    parser = OddscheckerParser()
    parser.feed(html)
    results = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        try:
            name = row[0].strip()
            decimal_odds = float(row[1].replace(",", "."))
            results.append({
                "rider_name": name,
                "decimal_odds": decimal_odds,
                "implied_probability": decimal_to_implied(decimal_odds),
            })
        except (ValueError, IndexError):
            continue
    return results


def enrich_with_rider_ids(entries: list, startlist_path: str = "data/riders/riders_giro2026_v1.json") -> list:
    """
    Attempt to match rider names to rider_ids from the startlist.
    Unmatched riders get rider_id = None.
    """
    try:
        with open(startlist_path) as f:
            data = json.load(f)
        name_to_id = {r["name"].lower(): r["rider_id"] for r in data["riders"]}
    except (FileNotFoundError, KeyError):
        name_to_id = {}

    for entry in entries:
        name_lower = entry.get("rider_name", "").lower()
        entry["rider_id"] = name_to_id.get(name_lower, None)

    return entries


def save_snapshot(snapshot: dict, stage_num: int) -> Path:
    out_dir = Path("data/odds")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"odds_giro2026_stage{stage_num}_T0.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"Saved snapshot to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Capture odds snapshot at T0 for a Giro stage.")
    parser.add_argument("--stage", type=int, required=True, help="Stage number (1-21)")
    parser.add_argument("--source", default="oddschecker", help="Bookmaker source name")
    parser.add_argument("--html-file", help="Path to manually saved HTML page (avoids bot blocking)")
    args = parser.parse_args()

    if not (1 <= args.stage <= 21):
        print("Error: stage must be 1-21")
        sys.exit(1)

    ts = snapshot_timestamp()
    snapshot = empty_snapshot(args.stage, args.source, ts)

    if args.html_file:
        raw = parse_html_file(args.html_file)
    else:
        raw = fetch_oddschecker(args.stage)

    if raw:
        enriched = enrich_with_rider_ids(raw)
        snapshot["stage_win_odds"] = enriched
        print(f"Captured {len(enriched)} stage-win odds entries for stage {args.stage}")
    else:
        print("No odds data captured. Saving empty template.")
        print("To populate: save the bookmaker page as HTML and pass --html-file <path>")

    save_snapshot(snapshot, args.stage)


if __name__ == "__main__":
    main()
