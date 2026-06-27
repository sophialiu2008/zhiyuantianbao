#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import cleaned 2026 admission-plan JSON into Supabase Postgres.

Database URL can be passed with --db-url or SUPABASE_DB_URL.

Usage:
  python scripts/supabase_import/import_admission_plans.py \
    --db-url "postgresql://..." \
    --data data/cleaned/admission_plan/admission_plan_2026_physics.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

Jsonb: Any = None


COLUMNS = [
    "year",
    "subject",
    "batch",
    "plan_nature",
    "volunteer_mode",
    "school_code",
    "school_name",
    "school_name_raw",
    "school_name_normalized",
    "school_tags",
    "major_code",
    "major_name",
    "major_name_normalized",
    "major_remark",
    "subject_requirement",
    "plan_count",
    "duration_years",
    "tuition",
    "source_file",
    "source_page",
    "source_row",
    "entry",
    "crawled_at",
    "raw_payload",
]


def read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {column: row.get(column) for column in COLUMNS}
    normalized["raw_payload"] = Jsonb(normalized.get("raw_payload") or {})
    return normalized


def upsert_plans(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    sql = """
      insert into public.admission_plans (
        year, subject, batch, plan_nature, volunteer_mode,
        school_code, school_name, school_name_raw, school_name_normalized, school_tags,
        major_code, major_name, major_name_normalized, major_remark, subject_requirement,
        plan_count, duration_years, tuition,
        source_file, source_page, source_row, entry, crawled_at, raw_payload
      )
      values (
        %(year)s, %(subject)s, %(batch)s, %(plan_nature)s, %(volunteer_mode)s,
        %(school_code)s, %(school_name)s, %(school_name_raw)s, %(school_name_normalized)s, %(school_tags)s,
        %(major_code)s, %(major_name)s, %(major_name_normalized)s, %(major_remark)s, %(subject_requirement)s,
        %(plan_count)s, %(duration_years)s, %(tuition)s,
        %(source_file)s, %(source_page)s, %(source_row)s, %(entry)s, %(crawled_at)s, %(raw_payload)s
      )
      on conflict (
        year, subject, batch, plan_nature, volunteer_mode,
        school_code, major_code, major_name, major_remark
      )
      do update set
        school_name = excluded.school_name,
        school_name_raw = excluded.school_name_raw,
        school_name_normalized = excluded.school_name_normalized,
        school_tags = excluded.school_tags,
        major_name_normalized = excluded.major_name_normalized,
        subject_requirement = excluded.subject_requirement,
        plan_count = excluded.plan_count,
        duration_years = excluded.duration_years,
        tuition = excluded.tuition,
        source_file = excluded.source_file,
        source_page = excluded.source_page,
        source_row = excluded.source_row,
        entry = excluded.entry,
        crawled_at = excluded.crawled_at,
        raw_payload = excluded.raw_payload,
        updated_at = now();
    """
    with conn.cursor() as cur:
        cur.executemany(sql, [normalize_row(row) for row in rows])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/cleaned/admission_plan/admission_plan_2026_physics.json")
    parser.add_argument("--db-url", default="", help="Supabase Postgres connection URI. Falls back to SUPABASE_DB_URL.")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--replace-year", action="store_true", help="Delete rows for the same year+subject before import")
    parser.add_argument("--replace-batch", default="", help="Delete rows for the same year+subject+batch before import")
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("Pass --db-url or set SUPABASE_DB_URL first.")

    try:
        import psycopg
        from psycopg.types.json import Jsonb as PsycopgJsonb
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Missing dependency: psycopg. Install with `pip install psycopg[binary]`.") from exc

    global Jsonb
    Jsonb = PsycopgJsonb

    data_path = Path(args.data).resolve()
    rows = read_json(data_path)
    if not rows:
        raise SystemExit(f"No rows in {data_path}")

    year = rows[0]["year"]
    subject = rows[0]["subject"]
    replace_batch = args.replace_batch.strip()
    with psycopg.connect(db_url) as conn:
        with conn.transaction():
            if args.replace_year and replace_batch:
                raise SystemExit("Use either --replace-year or --replace-batch, not both.")
            if replace_batch:
                with conn.cursor() as cur:
                    cur.execute(
                        "delete from public.admission_plans where year = %s and subject = %s and batch = %s;",
                        (year, subject, replace_batch),
                    )
            elif args.replace_year:
                with conn.cursor() as cur:
                    cur.execute(
                        "delete from public.admission_plans where year = %s and subject = %s;",
                        (year, subject),
                    )
            for index, batch in enumerate(chunks(rows, args.batch_size), start=1):
                upsert_plans(conn, batch)
                print(f"plan batch {index}: {len(batch)}")

    print(f"Imported admission plan rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
