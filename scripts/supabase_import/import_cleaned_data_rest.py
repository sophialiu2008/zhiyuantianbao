#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import cleaned data through Supabase PostgREST with a service_role key.

Required environment variables:
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=...

Usage:
  python scripts/supabase_import/import_cleaned_data_rest.py --data data/cleaned
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


RANK_COLUMNS = [
    "year",
    "subject",
    "score",
    "count_at_score",
    "cumulative_rank",
    "score_label",
    "source_file",
    "source_row",
]

ADMISSION_COLUMNS = [
    "year",
    "subject",
    "admission_type",
    "school_code",
    "school_name",
    "school_name_raw",
    "school_tags",
    "major_code",
    "major_name",
    "min_score",
    "min_rank",
    "chinese_math_score",
    "chinese_math_highest",
    "foreign_language_score",
    "first_choice_subject_score",
    "second_choice_subject_highest",
    "second_choice_subject_second",
    "volunteer_no",
    "remark",
    "source_file",
    "source_row",
]


def read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row.get(column) for column in columns} for row in rows]


def chunked(rows: list[dict[str, Any]], size: int):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


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
    parser.add_argument("--data", default="data/cleaned")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url:
        raise SystemExit("Set SUPABASE_URL first.")
    if not service_key:
        raise SystemExit("Set SUPABASE_SERVICE_ROLE_KEY first.")

    data_dir = Path(args.data).resolve()
    rank_rows = normalize(read_json(data_dir / "rank_table" / "all_rank.json"), RANK_COLUMNS)
    admission_rows = normalize(read_json(data_dir / "admission" / "all_admission.json"), ADMISSION_COLUMNS)

    upsert_table(
        supabase_url,
        service_key,
        "rank_table",
        rank_rows,
        "year,subject,score",
        args.batch_size,
    )
    upsert_table(
        supabase_url,
        service_key,
        "admission_records",
        admission_rows,
        "year,subject,admission_type,school_code,major_code,major_name",
        args.batch_size,
    )

    print(f"Imported rank rows: {len(rank_rows)}")
    print(f"Imported admission rows: {len(admission_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
