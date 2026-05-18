#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import data/cleaned/school_locations/school_locations.json through Supabase REST."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COLUMNS = [
    "school_name",
    "school_name_normalized",
    "moe_school_code",
    "province",
    "city",
    "department",
    "education_level",
    "remark",
    "campus_city",
    "location_note",
    "location_source",
    "confidence",
]


def request_json(url: str, key: str, payload: Any) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("apikey", key)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Prefer", "resolution=merge-duplicates,return=minimal")

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                response.read()
                return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/cleaned/school_locations/school_locations.json")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url:
        raise SystemExit("Set SUPABASE_URL first.")
    if not service_key:
        raise SystemExit("Set SUPABASE_SERVICE_ROLE_KEY first.")

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = [{column: record.get(column) for column in COLUMNS} for record in records]
    url = f"{supabase_url}/rest/v1/school_locations?on_conflict=school_name_normalized"
    for index in range(0, len(rows), args.batch_size):
        batch = rows[index : index + args.batch_size]
        request_json(url, service_key, batch)
        print(f"school_locations batch {index // args.batch_size + 1}: {len(batch)}")
    print(f"Imported school locations: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
