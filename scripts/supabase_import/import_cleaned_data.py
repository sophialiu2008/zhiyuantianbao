#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import cleaned Hebei gaokao JSON data into Supabase Postgres.

Required environment variable:
  SUPABASE_DB_URL=postgresql://postgres.xxx:password@aws-...pooler.supabase.com:6543/postgres

Usage:
  python scripts/supabase_import/import_cleaned_data.py --data data/cleaned --truncate
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: psycopg. Install with `pip install psycopg[binary]`.") from exc


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


def chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def normalize_row(row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    return {column: row.get(column) for column in columns}


def upsert_rank(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    sql = """
      insert into public.rank_table (
        year, subject, score, count_at_score, cumulative_rank, score_label, source_file, source_row
      )
      values (
        %(year)s, %(subject)s, %(score)s, %(count_at_score)s, %(cumulative_rank)s,
        %(score_label)s, %(source_file)s, %(source_row)s
      )
      on conflict (year, subject, score) do update set
        count_at_score = excluded.count_at_score,
        cumulative_rank = excluded.cumulative_rank,
        score_label = excluded.score_label,
        source_file = excluded.source_file,
        source_row = excluded.source_row;
    """
    with conn.cursor() as cur:
        cur.executemany(sql, [normalize_row(row, RANK_COLUMNS) for row in rows])


def upsert_admission(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    sql = """
      insert into public.admission_records (
        year, subject, admission_type, school_code, school_name, school_name_raw, school_tags,
        major_code, major_name, min_score, min_rank, chinese_math_score, chinese_math_highest,
        foreign_language_score, first_choice_subject_score, second_choice_subject_highest,
        second_choice_subject_second, volunteer_no, remark, source_file, source_row
      )
      values (
        %(year)s, %(subject)s, %(admission_type)s, %(school_code)s, %(school_name)s,
        %(school_name_raw)s, %(school_tags)s, %(major_code)s, %(major_name)s, %(min_score)s,
        %(min_rank)s, %(chinese_math_score)s, %(chinese_math_highest)s, %(foreign_language_score)s,
        %(first_choice_subject_score)s, %(second_choice_subject_highest)s,
        %(second_choice_subject_second)s, %(volunteer_no)s, %(remark)s, %(source_file)s, %(source_row)s
      )
      on conflict (year, subject, admission_type, school_code, major_code, major_name) do update set
        school_name = excluded.school_name,
        school_name_raw = excluded.school_name_raw,
        school_tags = excluded.school_tags,
        min_score = excluded.min_score,
        min_rank = excluded.min_rank,
        chinese_math_score = excluded.chinese_math_score,
        chinese_math_highest = excluded.chinese_math_highest,
        foreign_language_score = excluded.foreign_language_score,
        first_choice_subject_score = excluded.first_choice_subject_score,
        second_choice_subject_highest = excluded.second_choice_subject_highest,
        second_choice_subject_second = excluded.second_choice_subject_second,
        volunteer_no = excluded.volunteer_no,
        remark = excluded.remark,
        source_file = excluded.source_file,
        source_row = excluded.source_row;
    """
    with conn.cursor() as cur:
        cur.executemany(sql, [normalize_row(row, ADMISSION_COLUMNS) for row in rows])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/cleaned", help="Cleaned data directory")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--truncate", action="store_true", help="Delete existing rank/admission rows before import")
    args = parser.parse_args()

    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("Set SUPABASE_DB_URL first.")

    data_dir = Path(args.data).resolve()
    rank_rows = read_json(data_dir / "rank_table" / "all_rank.json")
    admission_rows = read_json(data_dir / "admission" / "all_admission.json")

    with psycopg.connect(db_url) as conn:
      with conn.transaction():
        if args.truncate:
            with conn.cursor() as cur:
                cur.execute("truncate table public.admission_records restart identity cascade;")
                cur.execute("truncate table public.rank_table restart identity cascade;")

        for index, batch in enumerate(chunks(rank_rows, args.batch_size), start=1):
            upsert_rank(conn, batch)
            print(f"rank batch {index}: {len(batch)}")

        for index, batch in enumerate(chunks(admission_rows, args.batch_size), start=1):
            upsert_admission(conn, batch)
            print(f"admission batch {index}: {len(batch)}")

        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.data_import_batches (source, rank_count, admission_count, notes)
                values (%s, %s, %s, %s);
                """,
                (str(data_dir), len(rank_rows), len(admission_rows), "cleaned JSON import"),
            )

    print(f"Imported rank rows: {len(rank_rows)}")
    print(f"Imported admission rows: {len(admission_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
