#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a Supabase SQL Editor import file for enriched school profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def sql_string(value: Any) -> str:
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def sql_bool(value: Any) -> str:
    if value is None:
        return "null"
    return "true" if bool(value) else "false"


def sql_number(value: Any) -> str:
    if value is None or value == "":
        return "null"
    return str(value)


def sql_text_array(values: Any) -> str:
    if not values:
        return "'{}'::text[]"
    escaped = ",".join('"' + str(item).replace("\\", "\\\\").replace('"', '\\"') + '"' for item in values)
    return f"'{{{escaped}}}'::text[]"


def chunks(rows: list[Any], size: int):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def build_profiles_sql(rows: list[dict[str, Any]], batch_size: int) -> list[str]:
    statements: list[str] = []
    columns = [
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
    for batch in chunks(rows, batch_size):
        values = []
        for row in batch:
            values.append(
                "("
                + ", ".join(
                    [
                        sql_string(row.get("school_code")),
                        sql_string(row.get("school_name")),
                        sql_string(row.get("school_name_normalized")),
                        sql_text_array(row.get("school_tags")),
                        sql_string(row.get("province")),
                        sql_string(row.get("city")),
                        sql_string(row.get("campus_city")),
                        sql_string(row.get("city_tier")),
                        sql_string(row.get("school_type")),
                        sql_string(row.get("ownership")),
                        sql_bool(row.get("is_985")),
                        sql_bool(row.get("is_211")),
                        sql_bool(row.get("is_double_first_class")),
                        sql_text_array(row.get("double_first_class_subjects")),
                        sql_bool(row.get("has_postgrad_recommend")),
                        sql_number(row.get("postgrad_recommend_rate")),
                        sql_text_array(row.get("postgrad_destinations")),
                        sql_string(row.get("notes")),
                    ]
                )
                + ")"
            )
        statements.append(
            "insert into public.school_profiles ("
            + ", ".join(columns)
            + ")\nvalues\n"
            + ",\n".join(values)
            + "\non conflict (school_code) do update set\n"
            + "  school_name = excluded.school_name,\n"
            + "  school_name_normalized = excluded.school_name_normalized,\n"
            + "  school_tags = excluded.school_tags,\n"
            + "  province = excluded.province,\n"
            + "  city = excluded.city,\n"
            + "  campus_city = excluded.campus_city,\n"
            + "  city_tier = excluded.city_tier,\n"
            + "  school_type = excluded.school_type,\n"
            + "  ownership = excluded.ownership,\n"
            + "  is_985 = excluded.is_985,\n"
            + "  is_211 = excluded.is_211,\n"
            + "  is_double_first_class = excluded.is_double_first_class,\n"
            + "  double_first_class_subjects = excluded.double_first_class_subjects,\n"
            + "  has_postgrad_recommend = excluded.has_postgrad_recommend,\n"
            + "  postgrad_recommend_rate = excluded.postgrad_recommend_rate,\n"
            + "  postgrad_destinations = excluded.postgrad_destinations,\n"
            + "  notes = excluded.notes,\n"
            + "  updated_at = now();"
        )
    return statements


def build_rankings_sql(rows: list[dict[str, Any]], batch_size: int) -> list[str]:
    statements: list[str] = []
    columns = ["school_code", "school_name", "ranking_name", "ranking_year", "rank_no", "rank_label"]
    for batch in chunks(rows, batch_size):
        values = []
        for row in batch:
            values.append(
                "("
                + ", ".join(
                    [
                        sql_string(row.get("school_code")),
                        sql_string(row.get("school_name")),
                        sql_string(row.get("ranking_name")),
                        sql_number(row.get("ranking_year")),
                        sql_number(row.get("rank_no")),
                        sql_string(row.get("rank_label")),
                    ]
                )
                + ")"
            )
        statements.append(
            "insert into public.school_rankings ("
            + ", ".join(columns)
            + ")\nvalues\n"
            + ",\n".join(values)
            + "\non conflict (school_code, ranking_name, ranking_year) do update set\n"
            + "  school_name = excluded.school_name,\n"
            + "  rank_no = excluded.rank_no,\n"
            + "  rank_label = excluded.rank_label;"
        )
    return statements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", default="data/enriched/school_profiles/school_profiles_enriched.json")
    parser.add_argument("--rankings", default="data/enriched/school_profiles/school_rankings.json")
    parser.add_argument("--output", default="data/enriched/school_profiles/import_school_profiles_enriched.sql")
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()

    profiles = json.loads(Path(args.profiles).read_text(encoding="utf-8"))
    rankings = json.loads(Path(args.rankings).read_text(encoding="utf-8"))
    parts = [
        "-- Generated file. Execute in Supabase SQL Editor after 011_profile_schema_functions.sql.",
        "begin;",
        *build_profiles_sql(profiles, args.batch_size),
        *build_rankings_sql(rankings, args.batch_size),
        "commit;",
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(profiles)} profiles and {len(rankings)} rankings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
