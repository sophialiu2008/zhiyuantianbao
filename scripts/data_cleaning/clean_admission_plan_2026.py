#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean 2026 Hebei admission-plan CSV exports into app-ready JSON/CSV.

Usage:
  python scripts/data_cleaning/clean_admission_plan_2026.py \
    --input "C:/Users/liuli/Desktop/招生计划/hebei_admission_crawler/output" \
    --output data/cleaned/admission_plan
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SUBJECT_PHYSICS = "physics"
SUBJECT_HISTORY = "history"

PLAN_FILE_KEYWORDS = (
    "河北省招生计划汇总.csv",
    "本科提前批A段招生计划汇总.csv",
    "本科提前批B段招生计划汇总.csv",
    "本科提前批C段招生计划汇总.csv",
    "专科提前批招生计划汇总.csv",
    "专科批招生计划汇总.csv",
)


@dataclass
class AdmissionPlan:
    year: int
    subject: str
    batch: str
    plan_nature: str
    volunteer_mode: str
    school_code: str
    school_name: str
    school_name_raw: str
    school_name_normalized: str
    school_tags: list[str]
    major_code: str
    major_name: str
    major_name_normalized: str
    major_remark: str
    subject_requirement: str
    plan_count: int | None
    duration_years: int | None
    tuition: int | None
    source_file: str
    source_page: int | None
    source_row: int | None
    entry: str
    crawled_at: str | None
    raw_payload: dict[str, Any]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("_x000D_", "").replace("\ufeff", "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def to_int(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.0+)?", text)
    if not match:
        return None
    try:
        return int(float(match.group(0)))
    except ValueError:
        return None


def normalize_subject(value: str) -> str:
    if "历史" in value:
        return SUBJECT_HISTORY
    return SUBJECT_PHYSICS


def normalize_school_name(value: str) -> str:
    text = re.sub(r"\[[^\]]*\]", "", value)
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(
        r"\(([^)]*(市|地方专项|国家专项|中外合作|按高考|八协|少数民族预科|国际合作|国际本科学术互认|京津冀职教)[^)]*)\)",
        "",
        text,
    )
    text = re.sub(r"\s+", "", text)
    return text.strip()


def normalize_major_name(value: str) -> str:
    text = re.sub(r"[（(].*?[）)]", "", value)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def split_school_name(raw: str) -> tuple[str, list[str]]:
    tags = re.findall(r"\[([^\]]+)\]", raw)
    name = re.sub(r"\[[^\]]*\]", "", raw).strip()
    return name, tags


def parse_crawled_at(value: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return text


def iter_plan_files(input_dir: Path) -> list[Path]:
    files = []
    for name in PLAN_FILE_KEYWORDS:
        path = input_dir / name
        if path.exists():
            files.append(path)
    return files


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_file(path: Path, year: int) -> list[AdmissionPlan]:
    records: list[AdmissionPlan] = []
    for index, row in enumerate(read_csv_rows(path), start=2):
        raw_school_name = clean_text(row.get("院校名称"))
        major_name = clean_text(row.get("专业名称"))
        school_code = clean_text(row.get("院校代号"))
        major_code = clean_text(row.get("专业代号"))
        if not raw_school_name or not major_name or not school_code or not major_code:
            continue

        school_name, school_tags = split_school_name(raw_school_name)
        batch = clean_text(row.get("批次")) or infer_batch_from_filename(path.name)
        plan_nature = clean_text(row.get("计划性质")) or "非定向"
        volunteer_mode = clean_text(row.get("志愿模式"))

        records.append(
            AdmissionPlan(
                year=year,
                subject=normalize_subject(clean_text(row.get("科类"))),
                batch=batch,
                plan_nature=plan_nature,
                volunteer_mode=volunteer_mode,
                school_code=school_code,
                school_name=school_name,
                school_name_raw=raw_school_name,
                school_name_normalized=normalize_school_name(raw_school_name),
                school_tags=school_tags,
                major_code=major_code,
                major_name=major_name,
                major_name_normalized=normalize_major_name(major_name),
                major_remark=clean_text(row.get("专业备注")),
                subject_requirement=clean_text(row.get("再选科目要求")),
                plan_count=to_int(row.get("计划数")),
                duration_years=to_int(row.get("学制")),
                tuition=to_int(row.get("学费元/年")),
                source_file=path.name,
                source_page=to_int(row.get("来源页码")),
                source_row=to_int(row.get("页内行号")) or index,
                entry=clean_text(row.get("入口")),
                crawled_at=parse_crawled_at(clean_text(row.get("抓取时间"))),
                raw_payload={clean_text(k): clean_text(v) for k, v in row.items()},
            )
        )
    return records


def infer_batch_from_filename(name: str) -> str:
    if "本科提前批A段" in name:
        return "本科提前批A段"
    if "本科提前批B段" in name:
        return "本科提前批B段"
    if "本科提前批C段" in name:
        return "本科提前批C段"
    if "专科提前批" in name:
        return "专科提前批"
    if "专科批" in name:
        return "专科批"
    return "本科批"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[AdmissionPlan]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    rows = [asdict(record) for record in records]
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row["school_tags"] = json.dumps(row["school_tags"], ensure_ascii=False)
            row["raw_payload"] = json.dumps(row["raw_payload"], ensure_ascii=False)
            writer.writerow(row)


def build_report(input_dir: Path, output_dir: Path, files: list[Path], records: list[AdmissionPlan]) -> dict[str, Any]:
    by_batch = Counter(record.batch for record in records)
    by_subject = Counter(record.subject for record in records)
    zero_plan = [record for record in records if record.plan_count == 0]
    missing_plan = [record for record in records if record.plan_count is None]
    duplicate_keys = Counter(
        (
            record.year,
            record.subject,
            record.batch,
            record.plan_nature,
            record.volunteer_mode,
            record.school_code,
            record.major_code,
            record.major_name,
            record.major_remark,
        )
        for record in records
    )
    duplicates = [key for key, count in duplicate_keys.items() if count > 1]
    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "source_files": [path.name for path in files],
        "record_count": len(records),
        "by_batch": dict(sorted(by_batch.items())),
        "by_subject": dict(sorted(by_subject.items())),
        "zero_plan_count": len(zero_plan),
        "missing_plan_count": len(missing_plan),
        "duplicate_key_count": len(duplicates),
        "zero_plan_examples": [asdict(record) for record in zero_plan[:20]],
        "missing_plan_examples": [asdict(record) for record in missing_plan[:20]],
    }


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# 2026 河北招生计划清洗报告",
        "",
        f"- 输入目录：`{report['input_dir']}`",
        f"- 输出目录：`{report['output_dir']}`",
        f"- 来源文件：{', '.join(report['source_files'])}",
        f"- 记录数：{report['record_count']}",
        f"- 计划数为 0：{report['zero_plan_count']}",
        f"- 计划数缺失：{report['missing_plan_count']}",
        f"- 重复唯一键：{report['duplicate_key_count']}",
        "",
        "## 批次分布",
        "",
    ]
    for batch, count in report["by_batch"].items():
        lines.append(f"- {batch}: {count}")
    lines.extend(["", "## 科类分布", ""])
    for subject, count in report["by_subject"].items():
        lines.append(f"- {subject}: {count}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Directory containing crawler CSV output")
    parser.add_argument("--output", default="data/cleaned/admission_plan", help="Directory for cleaned output")
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    files = iter_plan_files(input_dir)
    if not files:
        raise SystemExit(f"No known 2026 admission-plan CSV files found in {input_dir}")

    records: list[AdmissionPlan] = []
    for path in files:
        file_records = parse_file(path, args.year)
        records.extend(file_records)
        print(f"{path.name}: {len(file_records)}")

    payload = [asdict(record) for record in records]
    write_json(output_dir / f"admission_plan_{args.year}_physics.json", payload)
    write_csv(output_dir / f"admission_plan_{args.year}_physics.csv", records)
    report = build_report(input_dir, output_dir, files, records)
    write_json(output_dir / "reports" / f"admission_plan_{args.year}_report.json", report)
    write_markdown_report(output_dir / "reports" / f"admission_plan_{args.year}_report.md", report)

    print(f"Plan records: {len(records)}")
    print(f"Report: {output_dir / 'reports' / f'admission_plan_{args.year}_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
