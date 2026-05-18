from __future__ import annotations

import csv
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE_XLSX = ROOT / "学校专业就业数据.xlsx"
OUTPUT_DIR = ROOT / "data" / "enriched" / "job_data"
IMPORT_SQL = OUTPUT_DIR / "job_data_import.sql"
IMPORT_CHUNKS_DIR = OUTPUT_DIR / "import_chunks"
CLEANED_CSV = OUTPUT_DIR / "job_data_cleaned.csv"
ISSUES_CSV = OUTPUT_DIR / "job_data_import_issues.csv"
SUMMARY_JSON = OUTPUT_DIR / "job_data_import_summary.json"

IMPORT_BATCH = "学校专业就业数据_2026_20260512"
SOURCE_KEY = "job_excel_school_major_2026"
CHUNK_SIZE = 120

DIRECTION_COLUMNS = ["就业方向1", "就业方向2", "就业方向3", "就业方向4"]
EMPLOYER_COLUMNS = ["企业1", "企业2", "企业3", "企业4"]
TIER_COLUMNS = ["企业层级1", "企业层级2", "企业层级3", "企业层级4"]
NUMERIC_COLUMNS = [
    "月薪下限",
    "月薪上限",
    "年终奖下限",
    "年终奖上限",
    "首年收入下限",
    "首年收入上限",
    "毕业年份",
]


@dataclass
class CleanRow:
    source_row_number: int
    school_name: str | None
    major_name: str | None
    degree_level: str
    job_directions: list[str]
    employers: list[str]
    employer_tiers: list[str]
    monthly_salary_min: int | None
    monthly_salary_max: int | None
    annual_bonus_min: int | None
    annual_bonus_max: int | None
    first_year_income_min: int | None
    first_year_income_max: int | None
    employment_city: str | None
    data_year: int | None
    credibility: str
    verification_status: str
    issue_codes: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


def clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def clean_int(value: Any) -> int | None:
    if pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return int(round(number))


def unique_values(values: list[str | None]) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for value in values:
        if value:
            seen.setdefault(value, None)
    return list(seen.keys())


def sql_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def sql_text_array(values: list[str]) -> str:
    if not values:
        return "'{}'::text[]"
    return "array[" + ", ".join(sql_literal(value) for value in values) + "]::text[]"


def issue_for_row(row: CleanRow) -> list[str]:
    issues: list[str] = []
    if not row.school_name:
        issues.append("missing_school_name")
    if not row.major_name:
        issues.append("missing_major_name")
    if not row.job_directions:
        issues.append("missing_job_direction")
    if not row.employers:
        issues.append("missing_employer")

    range_pairs = [
        ("monthly_salary", row.monthly_salary_min, row.monthly_salary_max),
        ("annual_bonus", row.annual_bonus_min, row.annual_bonus_max),
        ("first_year_income", row.first_year_income_min, row.first_year_income_max),
    ]
    for name, low, high in range_pairs:
        if low is not None and high is not None and low > high:
            issues.append(f"{name}_min_gt_max")

    if row.monthly_salary_max is not None and row.monthly_salary_max > 100000:
        issues.append("monthly_salary_suspect")
    if row.first_year_income_max is not None and row.first_year_income_max > 2_000_000:
        issues.append("first_year_income_suspect")
    if row.data_year is None:
        issues.append("missing_data_year")
    elif row.data_year < 2020 or row.data_year > 2030:
        issues.append("data_year_suspect")

    return issues


def build_rows() -> list[CleanRow]:
    df = pd.read_excel(SOURCE_XLSX, sheet_name=0)
    rows: list[CleanRow] = []

    for index, record in df.iterrows():
        raw = {
            key: (None if pd.isna(value) else value)
            for key, value in record.to_dict().items()
        }
        row = CleanRow(
            source_row_number=index + 2,
            school_name=clean_text(record.get("学校名称")),
            major_name=clean_text(record.get("专业名称")),
            degree_level=clean_text(record.get("学历层次")) or "本科",
            job_directions=unique_values([clean_text(record.get(col)) for col in DIRECTION_COLUMNS]),
            employers=unique_values([clean_text(record.get(col)) for col in EMPLOYER_COLUMNS]),
            employer_tiers=unique_values([clean_text(record.get(col)) for col in TIER_COLUMNS]),
            monthly_salary_min=clean_int(record.get("月薪下限")),
            monthly_salary_max=clean_int(record.get("月薪上限")),
            annual_bonus_min=clean_int(record.get("年终奖下限")),
            annual_bonus_max=clean_int(record.get("年终奖上限")),
            first_year_income_min=clean_int(record.get("首年收入下限")),
            first_year_income_max=clean_int(record.get("首年收入上限")),
            employment_city=clean_text(record.get("就业城市")),
            data_year=clean_int(record.get("毕业年份")),
            credibility="中",
            verification_status="reviewed",
            raw_payload=raw,
        )
        row.issue_codes = issue_for_row(row)
        if row.issue_codes:
            row.credibility = "待核实"
            row.verification_status = "pending"
        rows.append(row)

    return rows


def write_cleaned_csv(rows: list[CleanRow]) -> None:
    fields = [
        "source_row_number",
        "school_name",
        "major_name",
        "degree_level",
        "job_directions",
        "employers",
        "employer_tiers",
        "monthly_salary_min",
        "monthly_salary_max",
        "annual_bonus_min",
        "annual_bonus_max",
        "first_year_income_min",
        "first_year_income_max",
        "employment_city",
        "data_year",
        "credibility",
        "verification_status",
        "issue_codes",
    ]
    with CLEANED_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "source_row_number": row.source_row_number,
                "school_name": row.school_name,
                "major_name": row.major_name,
                "degree_level": row.degree_level,
                "job_directions": "；".join(row.job_directions),
                "employers": "；".join(row.employers),
                "employer_tiers": "；".join(row.employer_tiers),
                "monthly_salary_min": row.monthly_salary_min,
                "monthly_salary_max": row.monthly_salary_max,
                "annual_bonus_min": row.annual_bonus_min,
                "annual_bonus_max": row.annual_bonus_max,
                "first_year_income_min": row.first_year_income_min,
                "first_year_income_max": row.first_year_income_max,
                "employment_city": row.employment_city,
                "data_year": row.data_year,
                "credibility": row.credibility,
                "verification_status": row.verification_status,
                "issue_codes": "；".join(row.issue_codes),
            })


def write_issues_csv(rows: list[CleanRow]) -> None:
    fields = [
        "source_row_number",
        "school_name",
        "major_name",
        "degree_level",
        "issue_codes",
        "monthly_salary_min",
        "monthly_salary_max",
        "first_year_income_min",
        "first_year_income_max",
    ]
    with ISSUES_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if not row.issue_codes:
                continue
            writer.writerow({
                "source_row_number": row.source_row_number,
                "school_name": row.school_name,
                "major_name": row.major_name,
                "degree_level": row.degree_level,
                "issue_codes": "；".join(row.issue_codes),
                "monthly_salary_min": row.monthly_salary_min,
                "monthly_salary_max": row.monthly_salary_max,
                "first_year_income_min": row.first_year_income_min,
                "first_year_income_max": row.first_year_income_max,
            })


def write_sql(rows: list[CleanRow]) -> None:
    lines: list[str] = [
        "begin;",
        "",
        "-- Run supabase/migrations/015_job_data_import_foundation.sql before this import file.",
        "",
        "insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)",
        "values ('job_excel_school_major_2026', '学校专业就业数据.xlsx', '人工整理就业样本', 2026, '中', '按批次更新', '学校专业就业样本批量导入')",
        "on conflict (source_key) do update set",
        "  source_name = excluded.source_name,",
        "  source_type = excluded.source_type,",
        "  source_year = excluded.source_year,",
        "  credibility = excluded.credibility,",
        "  update_frequency = excluded.update_frequency,",
        "  notes = excluded.notes;",
        "",
        f"delete from public.job_data_import_staging where import_batch = {sql_literal(IMPORT_BATCH)};",
        "",
        "insert into public.job_data_import_staging (",
        "  import_batch, source_row_number, school_name, major_name, degree_level,",
        "  job_directions, employers, employer_tiers,",
        "  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max,",
        "  first_year_income_min, first_year_income_max, employment_city, data_year,",
        "  credibility, verification_status, issue_codes, raw_payload",
        ") values",
    ]

    value_lines: list[str] = []
    for row in rows:
        payload = json.dumps(row.raw_payload, ensure_ascii=False, default=str)
        values = [
            sql_literal(IMPORT_BATCH),
            sql_literal(row.source_row_number),
            sql_literal(row.school_name),
            sql_literal(row.major_name),
            sql_literal(row.degree_level),
            sql_text_array(row.job_directions),
            sql_text_array(row.employers),
            sql_text_array(row.employer_tiers),
            sql_literal(row.monthly_salary_min),
            sql_literal(row.monthly_salary_max),
            sql_literal(row.annual_bonus_min),
            sql_literal(row.annual_bonus_max),
            sql_literal(row.first_year_income_min),
            sql_literal(row.first_year_income_max),
            sql_literal(row.employment_city),
            sql_literal(row.data_year),
            sql_literal(row.credibility),
            sql_literal(row.verification_status),
            sql_text_array(row.issue_codes),
            f"{sql_literal(payload)}::jsonb",
        ]
        suffix = "," if row is not rows[-1] else ";"
        value_lines.append("  (" + ", ".join(values) + ")" + suffix)
    lines.extend(value_lines)
    lines.extend([
        "",
        "delete from public.job_data",
        f"where source_id = (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)});",
        "",
        "insert into public.job_data (",
        "  school_code, school_name, major_code, major_name, degree_level,",
        "  job_directions, employers, employer_tiers,",
        "  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max,",
        "  first_year_income_min, first_year_income_max, employment_city, data_year,",
        "  source_id, credibility, verification_status, notes",
        ")",
        "select",
        "  sp.school_code,",
        "  s.school_name,",
        "  mp.major_code,",
        "  s.major_name,",
        "  s.degree_level,",
        "  s.job_directions,",
        "  s.employers,",
        "  s.employer_tiers,",
        "  s.monthly_salary_min,",
        "  s.monthly_salary_max,",
        "  s.annual_bonus_min,",
        "  s.annual_bonus_max,",
        "  s.first_year_income_min,",
        "  s.first_year_income_max,",
        "  s.employment_city,",
        "  s.data_year,",
        f"  (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)}),",
        "  s.credibility,",
        "  s.verification_status,",
        "  case",
        "    when cardinality(s.issue_codes) > 0 then 'Excel row ' || s.source_row_number || ': ' || array_to_string(s.issue_codes, ',')",
        "    else 'Excel row ' || s.source_row_number",
        "  end",
        "from public.job_data_import_staging s",
        "left join lateral (",
        "  select school_code",
        "  from public.school_profiles",
        "  where public.normalize_school_name(school_name) = public.normalize_school_name(s.school_name)",
        "     or school_name = s.school_name",
        "  order by case when school_name = s.school_name then 0 else 1 end, school_code",
        "  limit 1",
        ") sp on true",
        "left join lateral (",
        "  select major_code",
        "  from public.major_profiles",
        "  where major_name = s.major_name",
        "  order by major_code",
        "  limit 1",
        ") mp on true",
        f"where s.import_batch = {sql_literal(IMPORT_BATCH)}",
        "  and s.school_name is not null",
        "  and s.major_name is not null;",
        "",
        "commit;",
        "",
    ])
    IMPORT_SQL.write_text("\n".join(lines), encoding="utf-8")


def staging_insert_sql(rows: list[CleanRow], terminate: bool = True) -> str:
    lines = [
        "insert into public.job_data_import_staging (",
        "  import_batch, source_row_number, school_name, major_name, degree_level,",
        "  job_directions, employers, employer_tiers,",
        "  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max,",
        "  first_year_income_min, first_year_income_max, employment_city, data_year,",
        "  credibility, verification_status, issue_codes, raw_payload",
        ") values",
    ]
    value_lines: list[str] = []
    for row in rows:
        payload = json.dumps(row.raw_payload, ensure_ascii=False, default=str)
        values = [
            sql_literal(IMPORT_BATCH),
            sql_literal(row.source_row_number),
            sql_literal(row.school_name),
            sql_literal(row.major_name),
            sql_literal(row.degree_level),
            sql_text_array(row.job_directions),
            sql_text_array(row.employers),
            sql_text_array(row.employer_tiers),
            sql_literal(row.monthly_salary_min),
            sql_literal(row.monthly_salary_max),
            sql_literal(row.annual_bonus_min),
            sql_literal(row.annual_bonus_max),
            sql_literal(row.first_year_income_min),
            sql_literal(row.first_year_income_max),
            sql_literal(row.employment_city),
            sql_literal(row.data_year),
            sql_literal(row.credibility),
            sql_literal(row.verification_status),
            sql_text_array(row.issue_codes),
            f"{sql_literal(payload)}::jsonb",
        ]
        suffix = "," if row is not rows[-1] else (";" if terminate else "")
        value_lines.append("  (" + ", ".join(values) + ")" + suffix)
    return "\n".join(lines + value_lines) + "\n"


def write_chunked_sql(rows: list[CleanRow]) -> None:
    IMPORT_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in IMPORT_CHUNKS_DIR.glob("*.sql"):
        old_file.unlink()

    prepare = "\n".join([
        "-- 001_prepare.sql",
        "-- Run supabase/migrations/015_job_data_import_foundation.sql first.",
        "insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)",
        "values ('job_excel_school_major_2026', '学校专业就业数据.xlsx', '人工整理就业样本', 2026, '中', '按批次更新', '学校专业就业样本批量导入')",
        "on conflict (source_key) do update set",
        "  source_name = excluded.source_name,",
        "  source_type = excluded.source_type,",
        "  source_year = excluded.source_year,",
        "  credibility = excluded.credibility,",
        "  update_frequency = excluded.update_frequency,",
        "  notes = excluded.notes;",
        "",
        f"delete from public.job_data_import_staging where import_batch = {sql_literal(IMPORT_BATCH)};",
        "delete from public.job_data",
        f"where source_id = (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)});",
        "",
    ])
    (IMPORT_CHUNKS_DIR / "001_prepare.sql").write_text(prepare, encoding="utf-8")

    chunk_index = 2
    for start in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[start:start + CHUNK_SIZE]
        filename = f"{chunk_index:03d}_staging_rows_{chunk[0].source_row_number}_{chunk[-1].source_row_number}.sql"
        (IMPORT_CHUNKS_DIR / filename).write_text(staging_insert_sql(chunk), encoding="utf-8")
        chunk_index += 1

    finalize = "\n".join([
        "-- 999_finalize.sql",
        "insert into public.job_data (",
        "  school_code, school_name, major_code, major_name, degree_level,",
        "  job_directions, employers, employer_tiers,",
        "  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max,",
        "  first_year_income_min, first_year_income_max, employment_city, data_year,",
        "  source_id, credibility, verification_status, notes",
        ")",
        "select",
        "  sp.school_code,",
        "  s.school_name,",
        "  mp.major_code,",
        "  s.major_name,",
        "  s.degree_level,",
        "  s.job_directions,",
        "  s.employers,",
        "  s.employer_tiers,",
        "  s.monthly_salary_min,",
        "  s.monthly_salary_max,",
        "  s.annual_bonus_min,",
        "  s.annual_bonus_max,",
        "  s.first_year_income_min,",
        "  s.first_year_income_max,",
        "  s.employment_city,",
        "  s.data_year,",
        f"  (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)}),",
        "  s.credibility,",
        "  s.verification_status,",
        "  case",
        "    when cardinality(s.issue_codes) > 0 then 'Excel row ' || s.source_row_number || ': ' || array_to_string(s.issue_codes, ',')",
        "    else 'Excel row ' || s.source_row_number",
        "  end",
        "from public.job_data_import_staging s",
        "left join lateral (",
        "  select school_code",
        "  from public.school_profiles",
        "  where public.normalize_school_name(school_name) = public.normalize_school_name(s.school_name)",
        "     or school_name = s.school_name",
        "  order by case when school_name = s.school_name then 0 else 1 end, school_code",
        "  limit 1",
        ") sp on true",
        "left join lateral (",
        "  select major_code",
        "  from public.major_profiles",
        "  where major_name = s.major_name",
        "  order by major_code",
        "  limit 1",
        ") mp on true",
        f"where s.import_batch = {sql_literal(IMPORT_BATCH)}",
        "  and s.school_name is not null",
        "  and s.major_name is not null;",
        "",
        "select",
        "  count(*) filter (where credibility in ('高', '中') and verification_status in ('verified', 'reviewed')) as visible_rows,",
        "  count(*) filter (where verification_status = 'pending') as pending_rows,",
        "  count(*) as imported_rows",
        "from public.job_data",
        f"where source_id = (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)});",
        "",
    ])
    (IMPORT_CHUNKS_DIR / "999_finalize.sql").write_text(finalize, encoding="utf-8")


def write_summary(rows: list[CleanRow]) -> None:
    issue_counts: dict[str, int] = {}
    for row in rows:
        for issue in row.issue_codes:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    summary = {
        "source": str(SOURCE_XLSX),
        "import_batch": IMPORT_BATCH,
        "rows": len(rows),
        "visible_rows": sum(1 for row in rows if row.credibility in {"高", "中"} and row.verification_status == "reviewed"),
        "pending_rows": sum(1 for row in rows if row.verification_status == "pending"),
        "school_count": len({row.school_name for row in rows if row.school_name}),
        "major_count": len({row.major_name for row in rows if row.major_name}),
        "issue_counts": dict(sorted(issue_counts.items())),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_cleaned_csv(rows)
    write_issues_csv(rows)
    write_sql(rows)
    write_chunked_sql(rows)
    write_summary(rows)
    print(json.dumps(json.loads(SUMMARY_JSON.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
