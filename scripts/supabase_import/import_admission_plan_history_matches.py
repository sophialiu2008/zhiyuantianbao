#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import cleaned 2026 admission-plan history snapshots into Supabase Postgres.

Database URL can be passed with --db-url or SUPABASE_DB_URL.

Usage:
  python scripts/supabase_import/import_admission_plan_history_matches.py \
    --data data/cleaned/admission_plan/admission_plan_history_matches_2026_physics_benke.json \
    --replace-batch
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

Jsonb: Any = None


COLUMNS = [
    "plan_year",
    "subject",
    "batch",
    "school_code",
    "school_name",
    "school_name_raw",
    "school_name_normalized",
    "major_code",
    "major_name",
    "major_name_normalized",
    "major_remark",
    "min_score_2025",
    "min_rank_2025",
    "min_score_2024",
    "min_rank_2024",
    "min_score_2023",
    "min_rank_2023",
    "history_years",
    "best_rank",
    "worst_rank",
    "avg_rank",
    "latest_score",
    "latest_rank",
    "is_new_major",
    "match_note",
    "source_file",
    "source_row",
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


def upsert_history_matches(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    sql = """
      insert into public.admission_plan_history_matches (
        plan_year, subject, batch,
        school_code, school_name, school_name_raw, school_name_normalized,
        major_code, major_name, major_name_normalized, major_remark,
        min_score_2025, min_rank_2025,
        min_score_2024, min_rank_2024,
        min_score_2023, min_rank_2023,
        history_years, best_rank, worst_rank, avg_rank, latest_score, latest_rank,
        is_new_major, match_note, source_file, source_row, raw_payload
      )
      values (
        %(plan_year)s, %(subject)s, %(batch)s,
        %(school_code)s, %(school_name)s, %(school_name_raw)s, %(school_name_normalized)s,
        %(major_code)s, %(major_name)s, %(major_name_normalized)s, %(major_remark)s,
        %(min_score_2025)s, %(min_rank_2025)s,
        %(min_score_2024)s, %(min_rank_2024)s,
        %(min_score_2023)s, %(min_rank_2023)s,
        %(history_years)s, %(best_rank)s, %(worst_rank)s, %(avg_rank)s, %(latest_score)s, %(latest_rank)s,
        %(is_new_major)s, %(match_note)s, %(source_file)s, %(source_row)s, %(raw_payload)s
      )
      on conflict (
        plan_year, subject, batch, school_code, major_code, major_name, major_remark
      )
      do update set
        school_name = excluded.school_name,
        school_name_raw = excluded.school_name_raw,
        school_name_normalized = excluded.school_name_normalized,
        major_name_normalized = excluded.major_name_normalized,
        min_score_2025 = excluded.min_score_2025,
        min_rank_2025 = excluded.min_rank_2025,
        min_score_2024 = excluded.min_score_2024,
        min_rank_2024 = excluded.min_rank_2024,
        min_score_2023 = excluded.min_score_2023,
        min_rank_2023 = excluded.min_rank_2023,
        history_years = excluded.history_years,
        best_rank = excluded.best_rank,
        worst_rank = excluded.worst_rank,
        avg_rank = excluded.avg_rank,
        latest_score = excluded.latest_score,
        latest_rank = excluded.latest_rank,
        is_new_major = excluded.is_new_major,
        match_note = excluded.match_note,
        source_file = excluded.source_file,
        source_row = excluded.source_row,
        raw_payload = excluded.raw_payload,
        updated_at = now();
    """
    with conn.cursor() as cur:
        cur.executemany(sql, [normalize_row(row) for row in rows])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/cleaned/admission_plan/admission_plan_history_matches_2026_physics_benke.json")
    parser.add_argument("--db-url", default="", help="Supabase Postgres connection URI. Falls back to SUPABASE_DB_URL.")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--replace-batch", action="store_true", help="Delete rows for the same plan_year+subject+batch before import")
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

    plan_year = rows[0]["plan_year"]
    subject = rows[0]["subject"]
    batch = rows[0]["batch"]
    with psycopg.connect(db_url) as conn:
        with conn.transaction():
            if args.replace_batch:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        delete from public.admission_plan_history_matches
                        where plan_year = %s and subject = %s and batch = %s;
                        """,
                        (plan_year, subject, batch),
                    )
            for index, batch_rows in enumerate(chunks(rows, args.batch_size), start=1):
                upsert_history_matches(conn, batch_rows)
                print(f"history match batch {index}: {len(batch_rows)}")

    print(f"Imported admission plan history match rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
