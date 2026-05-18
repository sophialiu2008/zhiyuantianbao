#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge manual school location overrides into cleaned school_locations.json."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locations", default="data/cleaned/school_locations/school_locations.json")
    parser.add_argument("--overrides", default="data/manual/school_location_overrides.csv")
    args = parser.parse_args()

    locations_path = Path(args.locations)
    overrides_path = Path(args.overrides)
    records = json.loads(locations_path.read_text(encoding="utf-8"))
    by_name = {row["school_name_normalized"]: row for row in records}

    with overrides_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row = {key: (value if value != "" else None) for key, value in row.items()}
            if row.get("school_name_normalized"):
                row["school_name_normalized"] = row["school_name_normalized"].replace("（", "(").replace("）", ")")
            by_name[row["school_name_normalized"]] = row

    merged = sorted(by_name.values(), key=lambda item: (item.get("province") or "", item.get("city") or "", item["school_name_normalized"]))
    locations_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"merged: {len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
