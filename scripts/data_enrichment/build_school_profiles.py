#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build school profile seed data from cleaned Hebei admission/location data.

This script intentionally fills only fields that can be inferred reliably from
local data or stable school-name lists. Ranking, discipline evaluation and
precise postgraduate recommendation rates stay in their dedicated templates.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CITY_TIERS = {
    "北京": "一线",
    "北京市": "一线",
    "上海": "一线",
    "上海市": "一线",
    "广州": "一线",
    "广州市": "一线",
    "深圳": "一线",
    "深圳市": "一线",
    "成都": "新一线",
    "成都市": "新一线",
    "杭州": "新一线",
    "杭州市": "新一线",
    "重庆": "新一线",
    "重庆市": "新一线",
    "武汉": "新一线",
    "武汉市": "新一线",
    "西安": "新一线",
    "西安市": "新一线",
    "苏州": "新一线",
    "苏州市": "新一线",
    "天津": "新一线",
    "天津市": "新一线",
    "南京": "新一线",
    "南京市": "新一线",
    "长沙": "新一线",
    "长沙市": "新一线",
    "郑州": "新一线",
    "郑州市": "新一线",
    "东莞": "新一线",
    "东莞市": "新一线",
    "青岛": "新一线",
    "青岛市": "新一线",
    "沈阳": "新一线",
    "沈阳市": "新一线",
    "宁波": "新一线",
    "宁波市": "新一线",
    "佛山": "新一线",
    "佛山市": "新一线",
    "合肥": "新一线",
    "合肥市": "新一线",
    "石家庄": "二线",
    "石家庄市": "二线",
    "保定": "三线",
    "保定市": "三线",
    "唐山": "三线",
    "唐山市": "三线",
    "廊坊": "三线",
    "廊坊市": "三线",
    "秦皇岛": "三线",
    "秦皇岛市": "三线",
    "邯郸": "三线",
    "邯郸市": "三线",
    "邢台": "四线",
    "邢台市": "四线",
    "沧州": "三线",
    "沧州市": "三线",
    "衡水": "四线",
    "衡水市": "四线",
    "张家口": "四线",
    "张家口市": "四线",
    "承德": "四线",
    "承德市": "四线",
}

N985 = {
    "北京大学", "中国人民大学", "清华大学", "北京航空航天大学", "北京理工大学", "中国农业大学", "北京师范大学",
    "中央民族大学", "南开大学", "天津大学", "大连理工大学", "东北大学", "吉林大学", "哈尔滨工业大学",
    "复旦大学", "同济大学", "上海交通大学", "华东师范大学", "南京大学", "东南大学", "浙江大学",
    "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学", "武汉大学", "华中科技大学",
    "湖南大学", "中南大学", "中山大学", "华南理工大学", "四川大学", "重庆大学", "电子科技大学",
    "西安交通大学", "西北工业大学", "西北农林科技大学", "兰州大学", "国防科技大学",
}

N211_ONLY = {
    "北京交通大学", "北京工业大学", "北京科技大学", "北京化工大学", "北京邮电大学", "北京林业大学",
    "北京中医药大学", "北京外国语大学", "中国传媒大学", "中央财经大学", "对外经济贸易大学",
    "北京体育大学", "中央音乐学院", "中国政法大学", "华北电力大学", "天津医科大学", "河北工业大学",
    "太原理工大学", "内蒙古大学", "辽宁大学", "大连海事大学", "延边大学", "东北师范大学",
    "哈尔滨工程大学", "东北农业大学", "东北林业大学", "华东理工大学", "东华大学", "上海外国语大学",
    "上海财经大学", "上海大学", "苏州大学", "南京航空航天大学", "南京理工大学", "中国矿业大学",
    "河海大学", "江南大学", "南京农业大学", "中国药科大学", "南京师范大学", "安徽大学", "合肥工业大学",
    "福州大学", "南昌大学", "中国石油大学(华东)", "郑州大学", "武汉理工大学", "华中农业大学",
    "华中师范大学", "中南财经政法大学", "湖南师范大学", "暨南大学", "华南师范大学", "海南大学",
    "广西大学", "西南交通大学", "四川农业大学", "西南大学", "西南财经大学", "贵州大学", "云南大学",
    "西藏大学", "西北大学", "西安电子科技大学", "长安大学", "陕西师范大学", "青海大学", "宁夏大学",
    "新疆大学", "石河子大学", "中国矿业大学(北京)", "中国石油大学(北京)", "中国地质大学(北京)",
    "中国地质大学(武汉)", "第二军医大学", "第四军医大学",
}

DOUBLE_FIRST_CLASS_EXTRA = {
    "中国科学院大学", "中国社会科学院大学", "首都师范大学", "外交学院", "中国人民公安大学",
    "中国音乐学院", "中央美术学院", "中央戏剧学院", "天津工业大学", "天津中医药大学",
    "上海海洋大学", "上海中医药大学", "上海体育大学", "上海音乐学院", "上海科技大学",
    "南京邮电大学", "南京林业大学", "南京信息工程大学", "南京中医药大学", "宁波大学",
    "中国美术学院", "河南大学", "湘潭大学", "广州医科大学", "广州中医药大学", "南方科技大学",
    "成都理工大学", "成都中医药大学", "西南石油大学", "南京医科大学", "山西大学", "上海纽约大学",
}


def normalize_school_name(name: str) -> str:
    text = re.sub(r"\[[^\]]*]", "", name or "")
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\(([^)]*(市|按高考|八协|地方专项|少数民族预科|国际合作|京津冀职教)[^)]*)\)", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def base_school_name(name: str) -> str:
    text = normalize_school_name(name)
    text = re.sub(r"\(([^)]*(校区|中外合作办学|合作办学|分校|学院|项目)[^)]*)\)", "", text)
    return text.strip()


def infer_school_type(name: str) -> str:
    mapping = [
        ("医科", "医药"),
        ("医学", "医药"),
        ("中医药", "医药"),
        ("药科", "医药"),
        ("师范", "师范"),
        ("财经", "财经"),
        ("财贸", "财经"),
        ("金融", "财经"),
        ("政法", "政法"),
        ("警察", "政法"),
        ("公安", "政法"),
        ("外国语", "语言"),
        ("语言", "语言"),
        ("传媒", "艺术传媒"),
        ("音乐", "艺术传媒"),
        ("美术", "艺术传媒"),
        ("戏剧", "艺术传媒"),
        ("艺术", "艺术传媒"),
        ("体育", "体育"),
        ("农业", "农林"),
        ("农林", "农林"),
        ("林业", "农林"),
        ("水利", "理工"),
        ("电力", "理工"),
        ("电子", "理工"),
        ("邮电", "理工"),
        ("科技", "理工"),
        ("理工", "理工"),
        ("工业", "理工"),
        ("工程", "理工"),
        ("交通", "理工"),
        ("航天", "理工"),
        ("航空", "理工"),
        ("矿业", "理工"),
        ("石油", "理工"),
        ("地质", "理工"),
        ("海事", "理工"),
        ("民族", "民族"),
        ("军事", "军事"),
    ]
    for keyword, school_type in mapping:
        if keyword in name:
            return school_type
    if "学院" in name and "大学" not in name:
        return "应用本科"
    return "综合"


def infer_ownership(tag_counts: Counter[str], name: str) -> str:
    if tag_counts["内地与港澳台地区合作办学"] or tag_counts["香港"]:
        return "内地与港澳台合作办学"
    if tag_counts["中外合作办学"] or "中外合作" in name:
        return "中外合作办学"
    if tag_counts["公办"] >= max(tag_counts["民办"], tag_counts["独立学院"], 1):
        return "公办"
    if tag_counts["民办"] or tag_counts["独立学院"]:
        return "民办"
    return "待核实"


def city_tier(city: str | None) -> str | None:
    if not city:
        return None
    return CITY_TIERS.get(city) or CITY_TIERS.get(city.removesuffix("市")) or "其他城市"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/cleaned")
    parser.add_argument("--output", default="data/enriched/school_profiles")
    args = parser.parse_args()

    data_dir = Path(args.data)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    admission_rows = read_json(data_dir / "admission" / "all_admission.json")
    location_rows = read_json(data_dir / "school_locations" / "school_locations.json")
    locations = {row["school_name_normalized"]: row for row in location_rows}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in admission_rows:
        school_code = row.get("school_code")
        if not school_code:
            continue
        grouped[school_code].append(row)

    profiles: list[dict[str, Any]] = []
    missing_location: list[dict[str, str]] = []
    for school_code, rows in sorted(grouped.items()):
        latest = sorted(rows, key=lambda r: (r.get("year") or 0, -(r.get("source_row") or 0)), reverse=True)[0]
        school_name = latest.get("school_name") or normalized
        normalized = normalize_school_name(school_name)
        simple_name = base_school_name(school_name)
        tag_counts = Counter(tag for row in rows for tag in (row.get("school_tags") or []))
        tags = sorted(tag_counts, key=lambda tag: (-tag_counts[tag], tag))
        loc = locations.get(normalized) or locations.get(simple_name) or locations.get(base_school_name(normalized))
        if not loc:
            missing_location.append({"school_code": school_code, "school_name": school_name, "normalized": normalized})

        is_985 = simple_name in N985
        is_211 = is_985 or simple_name in N211_ONLY
        is_dfc = is_211 or simple_name in DOUBLE_FIRST_CLASS_EXTRA
        province = loc.get("province") if loc else None
        city = loc.get("city") if loc else None
        campus_city = loc.get("campus_city") if loc else None
        effective_city = campus_city or city
        ownership = infer_ownership(tag_counts, school_name)
        profile_tags = []
        if is_985:
            profile_tags.append("985")
        if is_211:
            profile_tags.append("211")
        if is_dfc:
            profile_tags.append("双一流")
        if ownership != "待核实":
            profile_tags.append(ownership)

        profile = {
            "school_code": school_code,
            "school_name": school_name,
            "school_name_normalized": normalized,
            "school_tags": profile_tags or tags,
            "province": province,
            "city": city,
            "campus_city": campus_city,
            "city_tier": city_tier(effective_city),
            "school_type": infer_school_type(simple_name),
            "ownership": ownership,
            "is_985": is_985,
            "is_211": is_211,
            "is_double_first_class": is_dfc,
            "double_first_class_subjects": [],
            "has_postgrad_recommend": True if is_211 or is_985 else None,
            "postgrad_recommend_rate": None,
            "postgrad_destinations": [],
            "notes": "由本地投档数据、院校所在地数据和稳定院校名单自动生成；排名、学科评估、推免率需通过专项模板补充。",
        }
        profiles.append(profile)

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
    json_ready = []
    for profile in profiles:
        row = dict(profile)
        json_ready.append(row)
    (output_dir / "school_profiles.json").write_text(json.dumps(json_ready, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_rows = []
    for profile in profiles:
        row = dict(profile)
        for key in ("school_tags", "double_first_class_subjects", "postgrad_destinations"):
            row[key] = ";".join(row[key] or [])
        csv_rows.append(row)
    write_csv(output_dir / "school_profiles.csv", csv_rows, columns)

    report = {
        "profile_count": len(profiles),
        "missing_location_count": len(missing_location),
        "ownership": Counter(row["ownership"] for row in profiles),
        "school_type": Counter(row["school_type"] for row in profiles),
        "city_tier": Counter(row["city_tier"] or "未知" for row in profiles),
        "tier_counts": {
            "985": sum(1 for row in profiles if row["is_985"]),
            "211": sum(1 for row in profiles if row["is_211"]),
            "double_first_class": sum(1 for row in profiles if row["is_double_first_class"]),
        },
        "missing_location_samples": missing_location[:50],
    }
    report_text = [
        "# 院校画像自动填充报告",
        "",
        f"- 院校画像记录：{report['profile_count']}",
        f"- 缺少所在地匹配：{report['missing_location_count']}",
        f"- 985：{report['tier_counts']['985']}",
        f"- 211：{report['tier_counts']['211']}",
        f"- 双一流：{report['tier_counts']['double_first_class']}",
        "",
        "## 办学性质分布",
        *[f"- {k}: {v}" for k, v in report["ownership"].most_common()],
        "",
        "## 院校类型分布",
        *[f"- {k}: {v}" for k, v in report["school_type"].most_common()],
        "",
        "## 城市能级分布",
        *[f"- {k}: {v}" for k, v in report["city_tier"].most_common()],
        "",
        "## 说明",
        "- 本文件填充院校详情页可稳定展示的基础画像字段。",
        "- 软科排名、学科评估、精确推免率和推免去向不从投档表推断，请使用 templates 下对应 CSV 维护后导入。",
    ]
    (output_dir / "school_profile_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")
    (output_dir / "school_profile_report.md").write_text("\n".join(report_text) + "\n", encoding="utf-8")

    print(f"Generated {len(profiles)} school profiles -> {output_dir}")
    print(f"Missing location: {len(missing_location)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
