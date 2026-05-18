#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import school locations from the Ministry of Education school list.

Input should contain columns similar to:
  学校名称, 学校标识码, 主管部门, 所在地, 办学层次, 备注

Usage:
  python scripts/supabase_import/import_school_locations.py --input path/to/moe_school_list.xlsx --out data/cleaned/reports/location_match_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

try:
    import openpyxl
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: openpyxl. Install with `pip install openpyxl`.") from exc


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).strip()


def normalize_school_name(name: str, strip_location_suffix: bool = True) -> str:
    name = clean_text(name)
    name = re.sub(r"\[[^\]]+\]", "", name)
    name = name.replace("（", "(").replace("）", ")")
    if strip_location_suffix:
        name = re.sub(r"\([^)]*(市|校区|中外合作|按高考|八协|地方专项|少数民族预科|国际合作|京津冀职教)[^)]*\)", "", name)
    return re.sub(r"\s+", "", name).strip()


def read_cleaned_admission_schools(data_dir: Path) -> set[str]:
    records = json.loads((data_dir / "admission" / "all_admission.json").read_text(encoding="utf-8"))
    return {normalize_school_name(row["school_name"]) for row in records if row.get("school_name")}


def header_map(headers: list[str]) -> dict[str, int]:
    aliases = {
        "school_name": ["学校名称", "院校名称"],
        "moe_school_code": ["学校标识码", "标识码", "院校代码"],
        "department": ["主管部门"],
        "city": ["所在地", "所在城市", "所在地市"],
        "education_level": ["办学层次", "层次"],
        "remark": ["备注"],
    }
    result: dict[str, int] = {}
    for key, names in aliases.items():
        for name in names:
            if name in headers:
                result[key] = headers.index(name)
                break
    if "school_name" not in result or "city" not in result:
        raise ValueError(f"Cannot find required columns in headers: {headers}")
    return result


def infer_province_from_rows(rows: list[list[str]], file_name: str) -> str:
    provinces = [
        "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
        "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
        "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
        "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    ]
    for row in rows[:8]:
        joined = " ".join(row)
        for province in provinces:
            if province in joined or province in file_name:
                return province
    return ""


def read_xlsx(path: Path) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    output: list[dict[str, Any]] = []
    try:
        for ws in wb.worksheets:
            rows = [[clean_text(cell) for cell in row] for row in ws.iter_rows(values_only=True)]
            if not rows:
                continue
            province = infer_province_from_rows(rows, path.name)
            header_index = None
            mapping = None
            for index, row in enumerate(rows[:20]):
                try:
                    mapping = header_map(row)
                    header_index = index
                    break
                except ValueError:
                    continue
            if header_index is None or mapping is None:
                continue
            for source_row, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
                school_name = clean_text(row[mapping["school_name"]] if mapping["school_name"] < len(row) else "")
                city = clean_text(row[mapping["city"]] if mapping["city"] < len(row) else "")
                if not school_name or school_name == "学校名称" or not city:
                    continue
                output.append(
                    {
                        "school_name": school_name,
                        "school_name_normalized": normalize_school_name(school_name),
                        "moe_school_code": clean_text(row[mapping["moe_school_code"]]) if "moe_school_code" in mapping and mapping["moe_school_code"] < len(row) else "",
                        "province": province,
                        "city": city,
                        "department": clean_text(row[mapping["department"]]) if "department" in mapping and mapping["department"] < len(row) else "",
                        "education_level": clean_text(row[mapping["education_level"]]) if "education_level" in mapping and mapping["education_level"] < len(row) else "",
                        "remark": clean_text(row[mapping["remark"]]) if "remark" in mapping and mapping["remark"] < len(row) else "",
                        "campus_city": None,
                        "location_note": "",
                        "location_source": "教育部全国高等学校名单",
                        "confidence": "high",
                        "source_file": path.name,
                        "source_sheet": ws.title,
                        "source_row": source_row,
                    }
                )
    finally:
        wb.close()
    return output


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    output = []
    for index, row in enumerate(rows, start=2):
        school_name = clean_text(row.get("学校名称") or row.get("院校名称"))
        city = clean_text(row.get("所在地") or row.get("所在城市") or row.get("所在地市"))
        province = clean_text(row.get("省份") or row.get("省"))
        if not school_name or not city:
            continue
        output.append(
            {
                "school_name": school_name,
                "school_name_normalized": normalize_school_name(school_name),
                "moe_school_code": clean_text(row.get("学校标识码") or row.get("标识码")),
                "province": province,
                "city": city,
                "department": clean_text(row.get("主管部门")),
                "education_level": clean_text(row.get("办学层次")),
                "remark": clean_text(row.get("备注")),
                "campus_city": clean_text(row.get("校区城市")) or None,
                "location_note": clean_text(row.get("所在地备注")),
                "location_source": clean_text(row.get("来源")) or "教育部全国高等学校名单",
                "confidence": clean_text(row.get("可信度")) or "high",
                "source_file": path.name,
                "source_sheet": "",
                "source_row": index,
            }
        )
    return output


def write_outputs(records: list[dict[str, Any]], data_dir: Path, out_report: Path) -> None:
    admission_schools = read_cleaned_admission_schools(data_dir)
    location_names = {record["school_name_normalized"] for record in records}
    matched = sorted(admission_schools & location_names)
    missing = sorted(admission_schools - location_names)

    json_path = data_dir / "school_locations" / "school_locations.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(
        json.dumps(
            {
                "location_count": len(records),
                "admission_school_count": len(admission_schools),
                "matched_count": len(matched),
                "missing_count": len(missing),
                "missing_schools": missing,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"location_count: {len(records)}")
    print(f"matched_count: {len(matched)}")
    print(f"missing_count: {len(missing)}")
    print(f"json: {json_path}")
    print(f"report: {out_report}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="MOE school list xlsx/csv")
    parser.add_argument("--data", default="data/cleaned")
    parser.add_argument("--out", default="data/cleaned/reports/location_match_report.json")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    data_dir = Path(args.data).resolve()
    out_report = Path(args.out).resolve()
    if input_path.suffix.lower() in {".xlsx", ".xlsm"}:
        records = read_xlsx(input_path)
    elif input_path.suffix.lower() == ".csv":
        records = read_csv(input_path)
    else:
        raise SystemExit("Input must be .xlsx, .xlsm, or .csv")
    write_outputs(records, data_dir, out_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
