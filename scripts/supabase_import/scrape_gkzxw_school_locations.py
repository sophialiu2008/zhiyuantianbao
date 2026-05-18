#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scrape the 2025 MOE ordinary higher-education list reposted by gkzxw.com."""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


PROVINCE_PAGES = {
    "北京": "https://www.gkzxw.com/Article/202506/71449.html",
    "天津": "https://www.gkzxw.com/Article/202506/71450.html",
    "河北": "https://www.gkzxw.com/Article/202506/71451.html",
    "山西": "https://www.gkzxw.com/Article/202506/71452.html",
    "内蒙古": "https://www.gkzxw.com/Article/202506/71453.html",
    "辽宁": "https://www.gkzxw.com/Article/202506/71454.html",
    "吉林": "https://www.gkzxw.com/Article/202506/71455.html",
    "黑龙江": "https://www.gkzxw.com/Article/202506/71456.html",
    "上海": "https://www.gkzxw.com/Article/202506/71457.html",
    "江苏": "https://www.gkzxw.com/Article/202506/71458.html",
    "浙江": "https://www.gkzxw.com/Article/202506/71459.html",
    "安徽": "https://www.gkzxw.com/Article/202506/71460.html",
    "福建": "https://www.gkzxw.com/Article/202506/71461.html",
    "江西": "https://www.gkzxw.com/Article/202506/71462.html",
    "山东": "https://www.gkzxw.com/Article/202506/71463.html",
    "河南": "https://www.gkzxw.com/Article/202506/71464.html",
    "湖北": "https://www.gkzxw.com/Article/202506/71465.html",
    "湖南": "https://www.gkzxw.com/Article/202506/71466.html",
    "广东": "https://www.gkzxw.com/Article/202506/71467.html",
    "广西": "https://www.gkzxw.com/Article/202506/71468.html",
    "海南": "https://www.gkzxw.com/Article/202506/71469.html",
    "重庆": "https://www.gkzxw.com/Article/202506/71470.html",
    "四川": "https://www.gkzxw.com/Article/202506/71471.html",
    "贵州": "https://www.gkzxw.com/Article/202506/71472.html",
    "云南": "https://www.gkzxw.com/Article/202506/71473.html",
    "西藏": "https://www.gkzxw.com/Article/202506/71474.html",
    "陕西": "https://www.gkzxw.com/Article/202506/71475.html",
    "甘肃": "https://www.gkzxw.com/Article/202506/71476.html",
    "青海": "https://www.gkzxw.com/Article/202506/71477.html",
    "宁夏": "https://www.gkzxw.com/Article/202506/71478.html",
    "新疆": "https://www.gkzxw.com/Article/202506/71479.html",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def normalize_school_name(name: str, strip_location_suffix: bool = True) -> str:
    name = re.sub(r"\[[^\]]+\]", "", name).replace("（", "(").replace("）", ")")
    if strip_location_suffix:
        name = re.sub(r"\([^)]*(市|校区|中外合作|按高考|八协|地方专项|少数民族预科|国际合作|京津冀职教)[^)]*\)", "", name)
    return re.sub(r"\s+", "", name).strip()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    content = raw.decode("utf-8", errors="ignore")
    parser = TextExtractor()
    parser.feed(content)
    return "\n".join(html.unescape(part) for part in parser.parts)


def parse_page(province: str, url: str) -> list[dict[str, str | None]]:
    text = fetch_text(url)
    tokens = [line.strip() for line in text.splitlines() if line.strip()]
    records: list[dict[str, str | None]] = []
    start = 0
    for index, token in enumerate(tokens):
        if token == "备注":
            start = index + 1
            break
    i = start
    while i < len(tokens) - 5:
        if not re.fullmatch(r"\d+", tokens[i]):
            i += 1
            continue
        if not re.fullmatch(r"\d{10}", tokens[i + 2]):
            i += 1
            continue
        school_name = tokens[i + 1]
        code = tokens[i + 2]
        department = tokens[i + 3]
        city = tokens[i + 4]
        level = tokens[i + 5]
        if level not in {"本科", "专科"}:
            i += 1
            continue
        remark = ""
        next_index = i + 6
        if next_index < len(tokens) and not re.fullmatch(r"\d+", tokens[next_index]):
            if tokens[next_index] in {"民办", "中外合作办学", "内地与港澳台地区合作办学"}:
                remark = tokens[next_index]
                next_index += 1
        records.append(
            {
                "school_name": school_name,
                "school_name_normalized": normalize_school_name(school_name),
                "moe_school_code": code,
                "province": province,
                "city": city,
                "department": department,
                "education_level": level,
                "remark": remark or "",
                "campus_city": None,
                "location_note": "",
                "location_source": f"教育部全国高等学校名单转载页: {url}",
                "confidence": "high",
            }
        )
        i = next_index
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/cleaned/school_locations/school_locations.json")
    args = parser.parse_args()

    all_records: list[dict[str, str | None]] = []
    for province, url in PROVINCE_PAGES.items():
        records = parse_page(province, url)
        print(f"{province}: {len(records)}")
        all_records.extend(records)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(all_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"total: {len(all_records)}")
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
