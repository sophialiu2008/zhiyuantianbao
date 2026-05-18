#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge public school-profile sources into generated school profiles.

Inputs are cached files under data/external/school_sources. Network fetching is
kept outside this script so the merge is reproducible and can be reviewed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from docx import Document


def normalize_school_name(name: str) -> str:
    text = name or ""
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\[[^\]]*]", "", text)
    text = re.sub(r"\(([^)]*(市|按高考|八协|地方专项|少数民族预科|国际合作|京津冀职教)[^)]*)\)", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def base_school_name(name: str) -> str:
    text = normalize_school_name(name)
    text = re.sub(r"\(([^)]*(校区|中外合作办学|合作办学|分校|学院|项目)[^)]*)\)", "", text)
    return text.strip()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_double_first_class(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\u3000", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    entries: dict[str, list[str]] = {}
    current_school = ""
    current_subject = ""
    for line in lines:
        if line.startswith(("附件", "第二轮", "（按", "—")):
            continue
        if "：" in line:
            if current_school:
                entries[current_school] = split_subjects(current_subject)
            current_school, current_subject = line.split("：", 1)
            current_school = normalize_school_name(current_school)
        elif current_school:
            current_subject += line
    if current_school:
        entries[current_school] = split_subjects(current_subject)
    return entries


def split_subjects(text: str) -> list[str]:
    text = text.strip()
    if not text or "自主确定" in text:
        return []
    text = text.replace("、", ";").replace("，", ";").replace(",", ";")
    return [item.strip() for item in text.split(";") if item.strip()]


def parse_postgrad_full(path: Path) -> set[str]:
    tables = pd.read_html(path)
    names: set[str] = set()
    for table in tables:
        if "学校名称" not in table.columns:
            continue
        for name in table["学校名称"].dropna().astype(str):
            names.add(normalize_school_name(name))
    return names


def parse_postgrad_new(path: Path) -> set[str]:
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    text = re.sub(r"^附件\s*新增推免资格高校备案名单", "", text)
    names = re.split(r"[、,\s]+", text)
    return {normalize_school_name(name) for name in names if normalize_school_name(name) and "名单" not in name}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", default="data/enriched/school_profiles/school_profiles.json")
    parser.add_argument("--sources", default="data/external/school_sources")
    parser.add_argument("--output", default="data/enriched/school_profiles")
    args = parser.parse_args()

    output_dir = Path(args.output)
    source_dir = Path(args.sources)
    profiles = read_json(Path(args.profiles))
    ranking_rows = read_json(source_dir / "shanghairanking_2025.json")
    dfc = parse_double_first_class(source_dir / "moe_double_first_class_2022.txt")
    postgrad_full = parse_postgrad_full(source_dir / "postgrad_recommend_2025_cnur.html")
    postgrad_new = parse_postgrad_new(source_dir / "moe_postgrad_recommend_new_2025.docx")
    postgrad_names = postgrad_full | postgrad_new

    ranking_by_name = {normalize_school_name(row["school_name"]): row for row in ranking_rows}
    ranking_output: list[dict[str, Any]] = []
    ranking_matched = 0
    dfc_matched = 0
    postgrad_matched = 0
    profile_rows: list[dict[str, Any]] = []

    for profile in profiles:
        normalized = normalize_school_name(profile["school_name_normalized"] or profile["school_name"])
        simple = base_school_name(normalized)

        ranking = ranking_by_name.get(normalized) or ranking_by_name.get(simple)
        if ranking:
            ranking_matched += 1
            profile["school_type"] = profile.get("school_type") or ranking.get("school_type")
            tags = set(profile.get("school_tags") or [])
            tags.update(ranking.get("tags") or [])
            profile["school_tags"] = sorted(tags, key=lambda value: (value not in {"985", "211", "双一流"}, value))
            ranking_output.append({
                "school_code": profile["school_code"],
                "school_name": profile["school_name"],
                "ranking_name": ranking["ranking_name"],
                "ranking_year": ranking["ranking_year"],
                "rank_no": ranking["rank_no"],
                "rank_label": ranking["rank_label"],
            })

        subjects = dfc.get(normalized) or dfc.get(simple)
        if subjects is not None:
            dfc_matched += 1
            profile["is_double_first_class"] = True
            tags = set(profile.get("school_tags") or [])
            tags.add("双一流")
            profile["school_tags"] = sorted(tags, key=lambda value: (value not in {"985", "211", "双一流"}, value))
            profile["double_first_class_subjects"] = subjects

        if normalized in postgrad_names or simple in postgrad_names:
            postgrad_matched += 1
            profile["has_postgrad_recommend"] = True

        notes = profile.get("notes") or ""
        source_note = "已合并软科2025排名、教育部第二轮双一流名单、推免资格公开名单；推免率和推免去向仍需学校官网/研究生院公示补充。"
        profile["notes"] = source_note if not notes else f"{notes} {source_note}"
        profile_rows.append(profile)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "school_profiles_enriched.json").write_text(
        json.dumps(profile_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "school_rankings.json").write_text(
        json.dumps(ranking_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    profile_csv_rows = []
    for row in profile_rows:
        item = dict(row)
        for key in ("school_tags", "double_first_class_subjects", "postgrad_destinations"):
            item[key] = ";".join(item.get(key) or [])
        profile_csv_rows.append(item)
    profile_columns = [
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
    write_csv(output_dir / "school_profiles_enriched.csv", profile_csv_rows, profile_columns)
    write_csv(
        output_dir / "school_rankings.csv",
        ranking_output,
        ["school_code", "school_name", "ranking_name", "ranking_year", "rank_no", "rank_label"],
    )

    report = {
        "profile_count": len(profile_rows),
        "ranking_source_count": len(ranking_rows),
        "ranking_matched_profile_rows": ranking_matched,
        "double_first_class_source_count": len(dfc),
        "double_first_class_matched_profile_rows": dfc_matched,
        "postgrad_full_count": len(postgrad_full),
        "postgrad_new_count": len(postgrad_new),
        "postgrad_matched_profile_rows": postgrad_matched,
        "remaining_without_ranking": sum(1 for row in profile_rows if not any(r["school_code"] == row["school_code"] for r in ranking_output)),
        "remaining_without_postgrad_flag": sum(1 for row in profile_rows if row.get("has_postgrad_recommend") is not True),
        "tags": Counter(tag for row in profile_rows for tag in row.get("school_tags") or []),
    }
    (output_dir / "school_public_sources_merge_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=dict),
        encoding="utf-8",
    )
    report_md = [
        "# 院校公开源补充报告",
        "",
        f"- 院校画像记录：{report['profile_count']}",
        f"- 软科 2025 源记录：{report['ranking_source_count']}",
        f"- 匹配到软科排名的投档院校记录：{report['ranking_matched_profile_rows']}",
        f"- 教育部双一流源高校：{report['double_first_class_source_count']}",
        f"- 匹配到双一流学科的投档院校记录：{report['double_first_class_matched_profile_rows']}",
        f"- 推免资格完整名单记录：{report['postgrad_full_count']}",
        f"- 教育部 2025 新增推免资格记录：{report['postgrad_new_count']}",
        f"- 匹配到推免资格的投档院校记录：{report['postgrad_matched_profile_rows']}",
        "",
        "## 仍需官网补充",
        "- 推免率、推免去向：需要各校研究生院/教务处年度公示。",
        "- 学科评估等级：需要教育部学科评估公开表或人工整理表。",
        "- 部分未进入软科榜单的院校没有综合排名，前端应展示“待补充”。",
    ]
    (output_dir / "school_public_sources_merge_report.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")
    print(f"Merged public school sources -> {output_dir}")
    print(json.dumps(report, ensure_ascii=False, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
