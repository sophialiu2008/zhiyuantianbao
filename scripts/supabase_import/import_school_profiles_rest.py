#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import enriched school profiles through Supabase PostgREST.

Required environment variables:
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=...

Usage:
  python scripts/supabase_import/import_school_profiles_rest.py --input data/enriched/school_profiles/school_profiles_enriched.json
"""

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


SCHOOL_PROFILE_COLUMNS = [
    "school_code",
    "school_name",
    "school_name_normalized",
    "school_tags",
    "province",
    "city",
    "campus_city",
    "city_tier",
    "school_type",
    "ownership",
    "is_985",
    "is_211",
    "is_double_first_class",
    "double_first_class_subjects",
    "has_postgrad_recommend",
    "postgrad_recommend_rate",
    "postgrad_destinations",
    "notes",
]

SCHOOL_RANKING_COLUMNS = [
    "school_code",
    "school_name",
    "ranking_name",
    "ranking_year",
    "rank_no",
    "rank_label",
]


def chunked(rows: list[dict[str, Any]], size: int):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def normalize(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row.get(column) for column in columns} for row in rows]


def request_json(url: str, key: str, method: str, payload: Any | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("apikey", key)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Prefer", "resolution=merge-duplicates,return=minimal")

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError:
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise


def upsert_table(base_url: str, key: str, table: str, rows: list[dict[str, Any]], conflict: str, batch_size: int) -> None:
    conflict_query = urllib.parse.quote(conflict, safe=",")
    url = f"{base_url}/rest/v1/{table}?on_conflict={conflict_query}"
    for batch_index, batch in enumerate(chunked(rows, batch_size), start=1):
        request_json(url, key, "POST", batch)
        print(f"{table} batch {batch_index}: {len(batch)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/enriched/school_profiles/school_profiles_enriched.json")
    parser.add_argument("--rankings", default="data/enriched/school_profiles/school_rankings.json")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url:
        raise SystemExit("Set SUPABASE_URL first.")
    if not service_key:
        raise SystemExit("Set SUPABASE_SERVICE_ROLE_KEY first.")

    rows = normalize(json.loads(Path(args.input).read_text(encoding="utf-8")), SCHOOL_PROFILE_COLUMNS)
    upsert_table(supabase_url, service_key, "school_profiles", rows, "school_code", args.batch_size)
    print(f"Imported school profile rows: {len(rows)}")
    ranking_path = Path(args.rankings)
    if ranking_path.exists():
        ranking_rows = normalize(json.loads(ranking_path.read_text(encoding="utf-8")), SCHOOL_RANKING_COLUMNS)
        upsert_table(supabase_url, service_key, "school_rankings", ranking_rows, "school_code,ranking_name,ranking_year", args.batch_size)
        print(f"Imported school ranking rows: {len(ranking_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
