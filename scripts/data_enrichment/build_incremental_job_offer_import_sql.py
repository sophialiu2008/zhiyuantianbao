from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_XLSX = Path(r"E:\抖音\douyin_pipeline\data\results\jiuye_feijige_offer_extract.xlsx")
OUTPUT_DIR = ROOT / "data" / "enriched" / "jiuye_feijige_job_data"
CHUNKS_DIR = OUTPUT_DIR / "import_chunks"
OFFERS_CSV = OUTPUT_DIR / "incremental_job_offers_cleaned.csv"
COMPANY_ALIASES_CSV = OUTPUT_DIR / "company_name_aliases.csv"
COMPANY_REVIEW_CSV = OUTPUT_DIR / "company_name_review_required.csv"
ISSUES_CSV = OUTPUT_DIR / "incremental_job_offer_issues.csv"
SUMMARY_JSON = OUTPUT_DIR / "incremental_job_offer_summary.json"

IMPORT_BATCH = "就业飞机哥_2026_20260521"
SOURCE_KEY = "jiuye_feijige_offer_extract_2026"
SOURCE_NAME = "jiuye_feijige_offer_extract.xlsx"
SOURCE_TYPE = "视频转写/OCR整理就业offer"
OFFER_CHUNK_SIZE = 80
ALIAS_CHUNK_SIZE = 300

KNOWN_COMPANY_ALIASES: dict[str, tuple[str, str, str | None, str]] = {
    "JD.COM": ("京东", "中", "https://www.jd.com/", "英文品牌名标准化"),
    "京东": ("京东", "中", "https://www.jd.com/", "常用品牌名"),
    "美团": ("美团", "中", "https://about.meituan.com/", "常用品牌名"),
    "大疆": ("大疆", "中", "https://www.dji.com/cn", "常用品牌名"),
    "大疆创新": ("大疆", "中", "https://www.dji.com/cn", "公司/品牌标准化"),
    "华为": ("华为", "高", "https://www.huawei.com/cn/corporate-information", "官网标准名称"),
    "腾讯": ("腾讯", "高", "https://www.tencent.com/zh-cn/about.html", "官网标准名称"),
    "字节跳动": ("字节跳动", "高", "https://www.bytedance.com/zh/", "官网标准名称"),
    "阿里巴巴": ("阿里巴巴集团", "高", "https://www.alibabagroup.com/about-alibaba", "简称标准化"),
    "阿里巴巴集团": ("阿里巴巴集团", "高", "https://www.alibabagroup.com/about-alibaba", "官网标准名称"),
    "百度": ("百度", "中", "https://www.baidu.com/", "常用品牌名"),
    "拼多多": ("拼多多", "中", "https://www.pinduoduo.com/", "常用品牌名"),
    "快手": ("快手", "中", "https://www.kuaishou.com/", "常用品牌名"),
    "小红书": ("小红书", "中", "https://www.xiaohongshu.com/", "常用品牌名"),
    "小米": ("小米", "中", "https://www.mi.com/about/", "常用品牌名"),
    "OPPO": ("OPPO", "中", "https://www.oppo.com/cn/about/", "官网品牌名"),
    "bilibili": ("哔哩哔哩", "中", "https://www.bilibili.com/blackboard/aboutUs.html", "英文品牌名标准化"),
    "哔哩哔哩": ("哔哩哔哩", "中", "https://www.bilibili.com/blackboard/aboutUs.html", "常用品牌名"),
    "滴滴": ("滴滴", "中", "https://www.didiglobal.com/", "常用品牌名"),
    "携程": ("携程", "中", "https://www.trip.com/group/", "常用品牌名"),
    "Ctrip": ("携程", "中", "https://www.trip.com/group/", "英文品牌名标准化"),
    "比亚迪": ("比亚迪", "中", "https://www.byd.com/cn", "常用品牌名"),
    "宁德时代": ("宁德时代", "中", "https://www.catl.com/", "常用品牌名"),
    "迈瑞": ("迈瑞医疗", "中", "https://www.mindray.com/cn", "简称标准化"),
    "迈瑞医疗": ("迈瑞医疗", "中", "https://www.mindray.com/cn", "常用名称"),
    "联影": ("联影医疗", "中", "https://www.united-imaging.com/cn", "简称标准化"),
    "联影医疗": ("联影医疗", "中", "https://www.united-imaging.com/cn", "常用名称"),
    "sensetime": ("商汤科技", "中", "https://www.sensetime.com/cn", "英文品牌名标准化"),
    "商汤": ("商汤科技", "中", "https://www.sensetime.com/cn", "简称标准化"),
    "商汤科技": ("商汤科技", "中", "https://www.sensetime.com/cn", "常用名称"),
    "DAMO ACADEMY": ("阿里巴巴达摩院", "中", "https://damo.alibaba.com/", "英文机构名标准化"),
    "达摩院": ("阿里巴巴达摩院", "中", "https://damo.alibaba.com/", "简称标准化"),
    "SUNWODA": ("欣旺达", "中", "https://www.sunwoda.com/", "英文品牌名标准化"),
    "欣旺达": ("欣旺达", "中", "https://www.sunwoda.com/", "常用名称"),
    "Midea": ("美的集团", "中", "https://www.midea.com/cn/about-midea", "英文品牌名标准化"),
    "美的": ("美的集团", "中", "https://www.midea.com/cn/about-midea", "简称标准化"),
    "VOLKSWAGEN": ("大众汽车集团", "中", "https://www.volkswagen-group.com/", "英文品牌名标准化"),
    "Schlumberger": ("斯伦贝谢", "中", "https://www.slb.com/", "英文品牌名标准化"),
    "国家电网": ("国家电网", "中", "https://www.sgcc.com.cn/", "常用名称"),
    "中兴": ("中兴通讯", "中", "https://www.zte.com.cn/", "简称标准化"),
    "中兴通讯": ("中兴通讯", "中", "https://www.zte.com.cn/", "常用名称"),
    "Momenta": ("Momenta", "中", "https://www.momenta.cn/", "官网品牌名"),
    "蚂蚁集团": ("蚂蚁集团", "中", "https://www.antgroup.com/", "常用品牌名"),
    "米哈游": ("米哈游", "中", "https://www.mihoyo.com/", "常用品牌名"),
}

PATTERN_COMPANY_ALIASES: list[tuple[re.Pattern[str], tuple[str, str, str | None, str]]] = [
    (re.compile(r"JD\.?COM|京东", re.I), ("京东", "中", "https://www.jd.com/", "包含京东/JD关键词")),
    (re.compile(r"美团", re.I), ("美团", "中", "https://about.meituan.com/", "包含美团关键词")),
    (re.compile(r"快手", re.I), ("快手", "中", "https://www.kuaishou.com/", "包含快手关键词")),
    (re.compile(r"小米|Xiaomi", re.I), ("小米", "中", "https://www.mi.com/about/", "包含小米/Xiaomi关键词")),
    (re.compile(r"OPPO", re.I), ("OPPO", "中", "https://www.oppo.com/cn/about/", "包含OPPO关键词")),
    (re.compile(r"bilibili|哔哩", re.I), ("哔哩哔哩", "中", "https://www.bilibili.com/blackboard/aboutUs.html", "包含bilibili关键词")),
    (re.compile(r"滴滴|DIDI", re.I), ("滴滴", "中", "https://www.didiglobal.com/", "包含滴滴/DIDI关键词")),
    (re.compile(r"大疆|DJI", re.I), ("大疆", "中", "https://www.dji.com/cn", "包含大疆/DJI关键词")),
    (re.compile(r"HUAWEI|华为", re.I), ("华为", "中", "https://www.huawei.com/cn/corporate-information", "包含华为/HUAWEI关键词")),
    (re.compile(r"Tencent|腾讯", re.I), ("腾讯", "中", "https://www.tencent.com/zh-cn/about.html", "包含腾讯/Tencent关键词")),
    (re.compile(r"ByteDance|字节|头条", re.I), ("字节跳动", "中", "https://www.bytedance.com/zh/", "包含字节/ByteDance关键词")),
    (re.compile(r"Alibaba|阿里巴巴", re.I), ("阿里巴巴集团", "中", "https://www.alibabagroup.com/about-alibaba", "包含阿里巴巴/Alibaba关键词")),
    (re.compile(r"Momenta", re.I), ("Momenta", "中", "https://www.momenta.cn/", "包含Momenta关键词")),
    (re.compile(r"迈瑞|Mindray", re.I), ("迈瑞医疗", "中", "https://www.mindray.com/cn", "包含迈瑞/Mindray关键词")),
    (re.compile(r"联影|United Imaging", re.I), ("联影医疗", "中", "https://www.united-imaging.com/cn", "包含联影关键词")),
    (re.compile(r"sensetime|商汤", re.I), ("商汤科技", "中", "https://www.sensetime.com/cn", "包含商汤/SenseTime关键词")),
    (re.compile(r"DAMO|达摩院", re.I), ("阿里巴巴达摩院", "中", "https://damo.alibaba.com/", "包含达摩院/DAMO关键词")),
    (re.compile(r"SUNWODA|欣旺达", re.I), ("欣旺达", "中", "https://www.sunwoda.com/", "包含欣旺达/SUNWODA关键词")),
    (re.compile(r"Midea|美的", re.I), ("美的集团", "中", "https://www.midea.com/cn/about-midea", "包含美的/Midea关键词")),
    (re.compile(r"VOLKSWAGEN|大众", re.I), ("大众汽车集团", "中", "https://www.volkswagen-group.com/", "包含大众/VOLKSWAGEN关键词")),
    (re.compile(r"Schlumberger|SLB", re.I), ("斯伦贝谢", "中", "https://www.slb.com/", "包含Schlumberger/SLB关键词")),
    (re.compile(r"Ctrip|携程", re.I), ("携程", "中", "https://www.trip.com/group/", "包含携程/Ctrip关键词")),
    (re.compile(r"ZTE|中兴", re.I), ("中兴通讯", "中", "https://www.zte.com.cn/", "包含中兴/ZTE关键词")),
]


@dataclass
class CompanyAlias:
    raw_name: str
    standard_name: str
    verification_status: str
    source_url: str | None
    notes: str
    count: int = 0


@dataclass
class OfferRow:
    source_row_number: int
    offer_index: int
    video_filename: str | None
    school_name: str
    major_name: str
    degree_level: str
    data_year: int | None
    company_name_raw: str | None
    company_name_standard: str | None
    company_verification_status: str
    monthly_salary: int | None
    annual_bonus: int | None
    first_year_income: int | None
    work_content: str | None
    employment_city: str | None
    salary_verification_status: str
    credibility: str
    verification_status: str
    issue_codes: list[str] = field(default_factory=list)
    extraction_notes: str | None = None
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
    number = int(round(number))
    return number if number > 0 else None


def normalize_monthly(value: int | None, issues: list[str]) -> int | None:
    if value is None:
        return None
    if value > 100_000 and value % 10 == 0:
        issues.append("monthly_salary_scaled_down_by_10")
        return value // 10
    if value > 100_000:
        issues.append("monthly_salary_suspect")
    return value


def normalize_pair(school_name: str | None, major_name: str | None) -> tuple[str, str] | None:
    school = clean_text(school_name)
    major = clean_text(major_name)
    if not school or not major:
        return None
    return ("".join(school.split()), "".join(major.split()))


def sql_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value)) if float(value).is_integer() else str(value)
    return "'" + str(value).replace("'", "''") + "'"


def sql_text_array(values: list[str]) -> str:
    if not values:
        return "'{}'::text[]"
    return "array[" + ", ".join(sql_literal(value) for value in values) + "]::text[]"


def sql_json(value: dict[str, Any]) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    return sql_literal(text) + "::jsonb"


def read_env() -> tuple[str, str]:
    env_path = ROOT / "frontend" / ".env.local"
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values["VITE_SUPABASE_URL"].rstrip("/"), values["VITE_SUPABASE_ANON_KEY"]


def fetch_existing_pairs() -> set[tuple[str, str]]:
    supabase_url, anon_key = read_env()
    pairs: set[tuple[str, str]] = set()
    offset = 0
    page_size = 1000
    while True:
        query = urllib.parse.urlencode({
            "select": "school_name,major_name",
            "limit": page_size,
            "offset": offset,
        })
        request = urllib.request.Request(
            f"{supabase_url}/rest/v1/job_data?{query}",
            headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            rows = json.loads(response.read().decode("utf-8"))
        for row in rows:
            pair = normalize_pair(row.get("school_name"), row.get("major_name"))
            if pair:
                pairs.add(pair)
        if len(rows) < page_size:
            break
        offset += page_size
    return pairs


def standardize_company(raw_name: str | None) -> CompanyAlias | None:
    if not raw_name:
        return None
    raw = raw_name.strip()
    if raw in KNOWN_COMPANY_ALIASES:
        standard, status, source_url, notes = KNOWN_COMPANY_ALIASES[raw]
        return CompanyAlias(raw, standard, status, source_url, notes)
    for pattern, target in PATTERN_COMPANY_ALIASES:
        if pattern.search(raw):
            standard, status, source_url, notes = target
            return CompanyAlias(raw, standard, status, source_url, notes)
    if re.fullmatch(r"[A-Za-z0-9 .&()/-]{2,}", raw):
        return CompanyAlias(raw, raw, "待核实", None, "纯英文或缩写企业名，需人工复核")
    if len(raw) <= 2 or raw.upper() in {"XX", "X"}:
        return CompanyAlias(raw, raw, "待核实", None, "企业名过短或匿名化，需人工复核")
    return CompanyAlias(raw, raw, "中", None, "按原表企业名保留，未命中已知别名库")


def row_has_offer(record: pd.Series, index: int) -> bool:
    fields = [
        f"offer{index}_企业名称",
        f"offer{index}_月薪",
        f"offer{index}_年终奖金",
        f"offer{index}_首年收入",
        f"offer{index}_工作内容",
        f"offer{index}_工作城市",
    ]
    return any(clean_text(record.get(field)) is not None or clean_int(record.get(field)) is not None for field in fields)


def build_offer_rows(source_xlsx: Path, existing_pairs: set[tuple[str, str]]) -> tuple[list[OfferRow], OrderedDict[str, CompanyAlias], dict[str, int]]:
    df = pd.read_excel(source_xlsx, sheet_name=0)
    offers: list[OfferRow] = []
    aliases: OrderedDict[str, CompanyAlias] = OrderedDict()
    skipped_existing_rows = 0
    skipped_no_school_major_rows = 0
    skipped_no_offer_rows = 0

    for excel_index, record in df.iterrows():
        source_row_number = int(excel_index) + 2
        school_name = clean_text(record.get("学校名称"))
        major_name = clean_text(record.get("专业名称"))
        pair = normalize_pair(school_name, major_name)
        if not pair or not school_name or not major_name:
            skipped_no_school_major_rows += 1
            continue
        if pair in existing_pairs:
            skipped_existing_rows += 1
            continue

        row_offer_count = 0
        for offer_index in range(1, 5):
            if not row_has_offer(record, offer_index):
                continue
            row_offer_count += 1

            issues: list[str] = []
            raw_company = clean_text(record.get(f"offer{offer_index}_企业名称"))
            alias = standardize_company(raw_company)
            if alias:
                existing = aliases.get(alias.raw_name)
                if existing:
                    existing.count += 1
                else:
                    alias.count = 1
                    aliases[alias.raw_name] = alias

            monthly_salary = normalize_monthly(clean_int(record.get(f"offer{offer_index}_月薪")), issues)
            annual_bonus = clean_int(record.get(f"offer{offer_index}_年终奖金"))
            first_year_income = clean_int(record.get(f"offer{offer_index}_首年收入"))
            data_year = clean_int(record.get("毕业年份"))
            degree_level = clean_text(record.get("学历层次")) or "待补充"
            work_content = clean_text(record.get(f"offer{offer_index}_工作内容"))
            employment_city = clean_text(record.get(f"offer{offer_index}_工作城市"))

            if not raw_company:
                issues.append("missing_company")
            if not work_content:
                issues.append("missing_work_content")
            if not employment_city:
                issues.append("missing_work_city")
            if data_year is None:
                issues.append("missing_data_year")
            elif data_year < 2020 or data_year > 2030:
                issues.append("data_year_suspect")
            if first_year_income is not None and first_year_income > 2_500_000:
                issues.append("first_year_income_suspect")
            if annual_bonus is not None and annual_bonus > 800_000:
                issues.append("annual_bonus_suspect")

            salary_status = "reviewed" if not any(code.endswith("_suspect") for code in issues) else "pending"
            if monthly_salary is None and first_year_income is None:
                salary_status = "pending"
                issues.append("missing_salary_core")

            raw_payload = {
                key: (None if pd.isna(value) else value)
                for key, value in record.to_dict().items()
                if key not in {"语音转写内容", "画面字幕OCR"}
            }

            offers.append(OfferRow(
                source_row_number=source_row_number,
                offer_index=offer_index,
                video_filename=clean_text(record.get("视频文件名")),
                school_name=school_name,
                major_name=major_name,
                degree_level=degree_level,
                data_year=data_year,
                company_name_raw=raw_company,
                company_name_standard=alias.standard_name if alias else raw_company,
                company_verification_status=alias.verification_status if alias else "待核实",
                monthly_salary=monthly_salary,
                annual_bonus=annual_bonus,
                first_year_income=first_year_income,
                work_content=work_content,
                employment_city=employment_city,
                salary_verification_status=salary_status,
                credibility="中" if raw_company else "待核实",
                verification_status="reviewed" if raw_company else "pending",
                issue_codes=sorted(set(issues)),
                extraction_notes=clean_text(record.get("提取备注")),
                raw_payload=raw_payload,
            ))

        if row_offer_count == 0:
            skipped_no_offer_rows += 1

    return offers, aliases, {
        "source_rows": int(len(df)),
        "skipped_existing_school_major_rows": skipped_existing_rows,
        "skipped_no_school_major_rows": skipped_no_school_major_rows,
        "skipped_no_offer_rows": skipped_no_offer_rows,
    }


def write_csvs(offers: list[OfferRow], aliases: OrderedDict[str, CompanyAlias]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OFFERS_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        fields = [
            "source_row_number", "offer_index", "school_name", "major_name", "degree_level", "data_year",
            "company_name_raw", "company_name_standard", "company_verification_status",
            "monthly_salary", "annual_bonus", "first_year_income", "work_content", "employment_city",
            "salary_verification_status", "credibility", "verification_status", "issue_codes",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for offer in offers:
            writer.writerow({
                "source_row_number": offer.source_row_number,
                "offer_index": offer.offer_index,
                "school_name": offer.school_name,
                "major_name": offer.major_name,
                "degree_level": offer.degree_level,
                "data_year": offer.data_year,
                "company_name_raw": offer.company_name_raw,
                "company_name_standard": offer.company_name_standard,
                "company_verification_status": offer.company_verification_status,
                "monthly_salary": offer.monthly_salary,
                "annual_bonus": offer.annual_bonus,
                "first_year_income": offer.first_year_income,
                "work_content": offer.work_content,
                "employment_city": offer.employment_city,
                "salary_verification_status": offer.salary_verification_status,
                "credibility": offer.credibility,
                "verification_status": offer.verification_status,
                "issue_codes": ",".join(offer.issue_codes),
            })

    alias_fields = ["raw_name", "standard_name", "verification_status", "source_url", "notes", "count"]
    with COMPANY_ALIASES_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=alias_fields)
        writer.writeheader()
        for alias in aliases.values():
            writer.writerow(alias.__dict__)

    with COMPANY_REVIEW_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=alias_fields)
        writer.writeheader()
        for alias in aliases.values():
            if alias.verification_status == "待核实":
                writer.writerow(alias.__dict__)

    with ISSUES_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["source_row_number", "offer_index", "school_name", "major_name", "company_name_raw", "issue_codes"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for offer in offers:
            if offer.issue_codes:
                writer.writerow({
                    "source_row_number": offer.source_row_number,
                    "offer_index": offer.offer_index,
                    "school_name": offer.school_name,
                    "major_name": offer.major_name,
                    "company_name_raw": offer.company_name_raw,
                    "issue_codes": ",".join(offer.issue_codes),
                })


def alias_values_sql(aliases: list[CompanyAlias]) -> str:
    rows = []
    for alias in aliases:
        rows.append("(" + ", ".join([
            sql_literal(alias.raw_name),
            sql_literal(alias.standard_name),
            sql_literal(alias.verification_status),
            sql_literal(alias.source_url),
            sql_literal(alias.notes),
        ]) + ")")
    return ",\n".join(rows)


def staging_values_sql(offers: list[OfferRow]) -> str:
    rows = []
    for offer in offers:
        rows.append("(" + ", ".join([
            sql_literal(IMPORT_BATCH),
            sql_literal(offer.source_row_number),
            sql_literal(offer.offer_index),
            sql_literal(offer.video_filename),
            sql_literal(offer.school_name),
            sql_literal(offer.major_name),
            sql_literal(offer.degree_level),
            sql_literal(offer.data_year),
            sql_literal(offer.company_name_raw),
            sql_literal(offer.company_name_standard),
            sql_literal(offer.company_verification_status),
            sql_literal(offer.monthly_salary),
            sql_literal(offer.annual_bonus),
            sql_literal(offer.first_year_income),
            sql_literal(offer.work_content),
            sql_literal(offer.employment_city),
            sql_literal(offer.salary_verification_status),
            sql_literal(offer.credibility),
            sql_literal(offer.verification_status),
            sql_text_array(offer.issue_codes),
            sql_literal(offer.extraction_notes),
            sql_json(offer.raw_payload),
        ]) + ")")
    return ",\n".join(rows)


def write_sql_chunks(offers: list[OfferRow], aliases: OrderedDict[str, CompanyAlias]) -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in CHUNKS_DIR.glob("*.sql"):
        old_file.unlink()

    prepare = f"""insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)
values ({sql_literal(SOURCE_KEY)}, {sql_literal(SOURCE_NAME)}, {sql_literal(SOURCE_TYPE)}, 2026, '中', '按批次更新', '就业飞机哥视频提取结果；语音转写和画面字幕OCR仅作离线参考，不作为正式字段入库；按院校+专业与既有job_data去重后增量补充')
on conflict (source_key) do update set
  source_name = excluded.source_name,
  source_type = excluded.source_type,
  source_year = excluded.source_year,
  credibility = excluded.credibility,
  update_frequency = excluded.update_frequency,
  notes = excluded.notes;

delete from public.latest_job_offer_import_staging
where import_batch = {sql_literal(IMPORT_BATCH)};
"""
    (CHUNKS_DIR / "001_prepare_incremental_source.sql").write_text(prepare, encoding="utf-8")

    chunk_index = 2
    alias_list = list(aliases.values())
    for start in range(0, len(alias_list), ALIAS_CHUNK_SIZE):
        subset = alias_list[start:start + ALIAS_CHUNK_SIZE]
        sql = "insert into public.company_name_aliases (raw_name, standard_name, verification_status, source_url, notes)\nvalues\n"
        sql += alias_values_sql(subset)
        sql += "\non conflict (raw_name) do update set\n"
        sql += "  standard_name = excluded.standard_name,\n"
        sql += "  verification_status = excluded.verification_status,\n"
        sql += "  source_url = excluded.source_url,\n"
        sql += "  notes = excluded.notes,\n"
        sql += "  updated_at = now();\n"
        (CHUNKS_DIR / f"{chunk_index:03d}_company_aliases_{start + 1}_{start + len(subset)}.sql").write_text(sql, encoding="utf-8")
        chunk_index += 1

    for start in range(0, len(offers), OFFER_CHUNK_SIZE):
        subset = offers[start:start + OFFER_CHUNK_SIZE]
        sql = """insert into public.latest_job_offer_import_staging (
  import_batch, source_row_number, offer_index, video_filename, school_name, major_name, degree_level, data_year,
  company_name_raw, company_name_standard, company_verification_status,
  monthly_salary, annual_bonus, first_year_income, work_content, employment_city,
  salary_verification_status, credibility, verification_status, issue_codes, extraction_notes, raw_payload
)
values
"""
        sql += staging_values_sql(subset)
        sql += "\non conflict (import_batch, source_row_number, offer_index) do update set\n"
        sql += "  video_filename = excluded.video_filename,\n"
        sql += "  school_name = excluded.school_name,\n"
        sql += "  major_name = excluded.major_name,\n"
        sql += "  degree_level = excluded.degree_level,\n"
        sql += "  data_year = excluded.data_year,\n"
        sql += "  company_name_raw = excluded.company_name_raw,\n"
        sql += "  company_name_standard = excluded.company_name_standard,\n"
        sql += "  company_verification_status = excluded.company_verification_status,\n"
        sql += "  monthly_salary = excluded.monthly_salary,\n"
        sql += "  annual_bonus = excluded.annual_bonus,\n"
        sql += "  first_year_income = excluded.first_year_income,\n"
        sql += "  work_content = excluded.work_content,\n"
        sql += "  employment_city = excluded.employment_city,\n"
        sql += "  salary_verification_status = excluded.salary_verification_status,\n"
        sql += "  credibility = excluded.credibility,\n"
        sql += "  verification_status = excluded.verification_status,\n"
        sql += "  issue_codes = excluded.issue_codes,\n"
        sql += "  extraction_notes = excluded.extraction_notes,\n"
        sql += "  raw_payload = excluded.raw_payload;\n"
        (CHUNKS_DIR / f"{chunk_index:03d}_staging_offers_{start + 1}_{start + len(subset)}.sql").write_text(sql, encoding="utf-8")
        chunk_index += 1

    finalize = f"""insert into public.job_data (
  school_code, school_name, major_code, major_name, degree_level, job_directions, employers, employer_tiers,
  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max, first_year_income_min, first_year_income_max,
  employment_city, data_year, source_id, credibility, verification_status, notes, offer_index, company_name_raw,
  company_name_standard, company_verification_status, salary_verification_status, video_filename, extraction_notes
)
select
  sp.school_code,
  s.school_name,
  mp.major_code,
  s.major_name,
  s.degree_level,
  case when s.work_content is null then '{{}}'::text[] else array[s.work_content]::text[] end,
  case when s.company_name_standard is null then '{{}}'::text[] else array[s.company_name_standard]::text[] end,
  '{{}}'::text[],
  s.monthly_salary,
  s.monthly_salary,
  s.annual_bonus,
  s.annual_bonus,
  s.first_year_income,
  s.first_year_income,
  s.employment_city,
  s.data_year,
  (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)}),
  s.credibility,
  s.verification_status,
  'Excel row ' || s.source_row_number || ', offer ' || s.offer_index || case when cardinality(s.issue_codes) > 0 then ': ' || array_to_string(s.issue_codes, ',') else '' end,
  s.offer_index,
  s.company_name_raw,
  s.company_name_standard,
  s.company_verification_status,
  s.salary_verification_status,
  s.video_filename,
  s.extraction_notes
from public.latest_job_offer_import_staging s
left join lateral (
  select school_code from public.school_profiles
  where public.normalize_school_name(school_name) = public.normalize_school_name(s.school_name)
     or school_name = s.school_name
  order by case when school_name = s.school_name then 0 else 1 end, school_code
  limit 1
) sp on true
left join lateral (
  select major_code from public.major_profiles
  where major_name = s.major_name
  order by major_code
  limit 1
) mp on true
where s.import_batch = {sql_literal(IMPORT_BATCH)}
  and s.school_name is not null
  and s.major_name is not null
  and s.company_name_raw is not null
  and not exists (
    select 1
    from public.job_data jd
    where public.normalize_school_name(jd.school_name) = public.normalize_school_name(s.school_name)
      and trim(jd.major_name) = trim(s.major_name)
  );

select
  count(*) filter (where source_id = (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)})) as imported_this_source,
  count(distinct school_name || '|' || major_name) filter (where source_id = (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)})) as imported_school_major_pairs,
  count(*) filter (where credibility in ('高', '中') and verification_status in ('verified', 'reviewed')) as visible_rows,
  count(*) as total_job_rows
from public.job_data;
"""
    (CHUNKS_DIR / f"{chunk_index:03d}_finalize_insert_offers.sql").write_text(finalize, encoding="utf-8")


def main() -> int:
    source_xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE_XLSX
    if not source_xlsx.exists():
        raise FileNotFoundError(source_xlsx)

    existing_pairs = fetch_existing_pairs()
    offers, aliases, counters = build_offer_rows(source_xlsx, existing_pairs)
    write_csvs(offers, aliases)
    write_sql_chunks(offers, aliases)

    summary = {
        "source_file": str(source_xlsx),
        "import_batch": IMPORT_BATCH,
        "existing_school_major_pairs_seen": len(existing_pairs),
        "candidate_offer_rows": len(offers),
        "candidate_school_major_pairs": len({normalize_pair(row.school_name, row.major_name) for row in offers}),
        "company_alias_count": len(aliases),
        "company_review_required_count": sum(1 for alias in aliases.values() if alias.verification_status == "待核实"),
        "sql_chunk_count": len(list(CHUNKS_DIR.glob("*.sql"))),
        **counters,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
