from __future__ import annotations

import csv
import json
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE_XLSX = ROOT / "最新就业资料.xlsx"
OUTPUT_DIR = ROOT / "data" / "enriched" / "latest_job_data"
CHUNKS_DIR = OUTPUT_DIR / "import_chunks"

OFFERS_CSV = OUTPUT_DIR / "latest_job_offers_cleaned.csv"
COMPANY_ALIASES_CSV = OUTPUT_DIR / "company_name_aliases.csv"
COMPANY_REVIEW_CSV = OUTPUT_DIR / "company_name_review_required.csv"
ISSUES_CSV = OUTPUT_DIR / "latest_job_offer_issues.csv"
SUMMARY_JSON = OUTPUT_DIR / "latest_job_offer_summary.json"

IMPORT_BATCH = "最新就业资料_2026_20260513"
SOURCE_KEY = "latest_job_excel_offer_2026"
ALIAS_CHUNK_SIZE = 220
OFFER_CHUNK_SIZE = 40

OFFICIAL_SOURCES = {
    "华为": "https://www.huawei.com/cn/corporate-information",
    "腾讯": "https://www.tencent.com/zh-cn/about.html",
    "字节跳动": "https://www.bytedance.com/zh/",
    "阿里巴巴集团": "https://www.alibabagroup.com/about-alibaba",
    "Momenta": "https://www.momenta.cn/",
}

EXACT_ALIASES: dict[str, tuple[str, str, str, str]] = {
    "HUAWEI": ("华为", "高", OFFICIAL_SOURCES["华为"], "英文品牌名按华为官网标准化"),
    "HUAWEH": ("华为", "中", OFFICIAL_SOURCES["华为"], "疑似OCR错误，结合语音/OCR按华为处理"),
    "HUA": ("华为", "待核实", OFFICIAL_SOURCES["华为"], "缩写过短，需人工复核"),
    "华为": ("华为", "高", OFFICIAL_SOURCES["华为"], "标准名称"),
    "华为诺亚方舟实验室": ("华为诺亚方舟实验室", "中", OFFICIAL_SOURCES["华为"], "华为实验室/部门名称"),
    "腾讯": ("腾讯", "高", OFFICIAL_SOURCES["腾讯"], "标准名称"),
    "Tencent腾讯": ("腾讯", "高", OFFICIAL_SOURCES["腾讯"], "中英文混写标准化"),
    "Tenaent": ("腾讯", "中", OFFICIAL_SOURCES["腾讯"], "疑似Tencent OCR错误"),
    "ByteDance 头条": ("字节跳动", "高", OFFICIAL_SOURCES["字节跳动"], "品牌/产品混写标准化"),
    "ByteDance": ("字节跳动", "高", OFFICIAL_SOURCES["字节跳动"], "英文品牌名标准化"),
    "字节跳动": ("字节跳动", "高", OFFICIAL_SOURCES["字节跳动"], "标准名称"),
    "阿里巴巴": ("阿里巴巴集团", "高", OFFICIAL_SOURCES["阿里巴巴集团"], "简称标准化"),
    "阿里巴巴集团": ("阿里巴巴集团", "高", OFFICIAL_SOURCES["阿里巴巴集团"], "标准名称"),
    "AlibabaGroup": ("阿里巴巴集团", "高", OFFICIAL_SOURCES["阿里巴巴集团"], "英文品牌名标准化"),
    "AlibabaGl 阿里巴巴集团": ("阿里巴巴集团", "高", OFFICIAL_SOURCES["阿里巴巴集团"], "OCR混写标准化"),
    "阿里巴巴 Alibaba": ("阿里巴巴集团", "高", OFFICIAL_SOURCES["阿里巴巴集团"], "中英文混写标准化"),
    "阿里云": ("阿里云", "中", "https://www.aliyun.com/", "阿里云品牌名"),
    "MMOMENTA": ("Momenta", "中", OFFICIAL_SOURCES["Momenta"], "疑似Momenta OCR错误"),
    "AIMOMENTA": ("Momenta", "中", OFFICIAL_SOURCES["Momenta"], "疑似Momenta OCR错误"),
    "Momenta": ("Momenta", "高", OFFICIAL_SOURCES["Momenta"], "标准名称"),
    "中信证券股份有限公司": ("中信证券", "中", "https://www.citics.com/", "公司全称标准化为常用简称"),
    "中信证券": ("中信证券", "中", "https://www.citics.com/", "标准简称"),
    "京东": ("京东", "中", "https://www.jd.com/", "常用品牌名"),
    "拼多多": ("拼多多", "中", "https://www.pinduoduo.com/", "常用品牌名"),
    "米哈游": ("米哈游", "中", "https://www.mihoyo.com/", "常用品牌名"),
    "蚂蚁集团": ("蚂蚁集团", "中", "https://www.antgroup.com/", "常用品牌名"),
    "携程": ("携程", "中", "https://www.trip.com/group/", "常用品牌名"),
    "携程Ctrip": ("携程", "中", "https://www.trip.com/group/", "中英文混写标准化"),
    "携程ctrip": ("携程", "中", "https://www.trip.com/group/", "中英文混写标准化"),
    "Ctrip 携程": ("携程", "中", "https://www.trip.com/group/", "中英文混写标准化"),
    "Ctrip": ("携程", "中", "https://www.trip.com/group/", "英文品牌名标准化"),
    "得物": ("得物", "中", "https://www.dewu.com/", "常用品牌名"),
    "小红书": ("小红书", "中", "https://www.xiaohongshu.com/", "常用品牌名"),
    "美团": ("美团", "中", "https://about.meituan.com/", "常用品牌名"),
    "百度": ("百度", "中", "https://www.baidu.com/", "常用品牌名"),
    "NVIDIA": ("英伟达", "中", "https://www.nvidia.cn/", "英文品牌名标准化"),
    "英伟达": ("英伟达", "中", "https://www.nvidia.cn/", "常用中文名"),
    "ZTE中兴": ("中兴通讯", "中", "https://www.zte.com.cn/", "中英文混写标准化"),
    "中兴": ("中兴通讯", "中", "https://www.zte.com.cn/", "常用简称"),
    "地平线": ("地平线", "中", "https://www.horizon.cc/", "常用品牌名"),
    "Shopee": ("Shopee", "中", "https://shopee.com/", "英文品牌名"),
    "大疆": ("大疆", "中", "https://www.dji.com/cn", "常用品牌名"),
    "大疆创新": ("大疆", "中", "https://www.dji.com/cn", "公司/品牌标准化"),
    "比亚迪": ("比亚迪", "中", "https://www.byd.com/cn", "常用品牌名"),
    "宁德时代": ("宁德时代", "中", "https://www.catl.com/", "常用品牌名"),
    "CATL 时代新能源": ("宁德时代", "中", "https://www.catl.com/", "品牌混写标准化"),
    "国家电网": ("国家电网", "中", "https://www.sgcc.com.cn/", "常用名称"),
}

PATTERN_ALIASES: list[tuple[re.Pattern[str], tuple[str, str, str, str]]] = [
    (re.compile(r"HUAWEI|华为"), ("华为", "中", OFFICIAL_SOURCES["华为"], "包含华为/HUAWEI关键字")),
    (re.compile(r"Tencent|腾讯", re.I), ("腾讯", "中", OFFICIAL_SOURCES["腾讯"], "包含腾讯/Tencent关键字")),
    (re.compile(r"ByteDance|字节|头条", re.I), ("字节跳动", "中", OFFICIAL_SOURCES["字节跳动"], "包含字节/ByteDance/头条关键字")),
    (re.compile(r"Alibaba|阿里巴巴", re.I), ("阿里巴巴集团", "中", OFFICIAL_SOURCES["阿里巴巴集团"], "包含阿里巴巴/Alibaba关键字")),
    (re.compile(r"Momenta|MOMENTA", re.I), ("Momenta", "中", OFFICIAL_SOURCES["Momenta"], "包含Momenta关键字")),
    (re.compile(r"Ctrip|携程", re.I), ("携程", "中", "https://www.trip.com/group/", "包含携程/Ctrip关键字")),
    (re.compile(r"NVIDIA|英伟达", re.I), ("英伟达", "中", "https://www.nvidia.cn/", "包含英伟达/NVIDIA关键字")),
    (re.compile(r"ZTE|中兴", re.I), ("中兴通讯", "中", "https://www.zte.com.cn/", "包含中兴/ZTE关键字")),
]

MANUAL_MAJOR_FIXES = {
    4: "图形图像算法",
    410: "计算机",
}


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
    school_name: str | None
    major_name: str | None
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


def standardize_company(raw_name: str | None) -> CompanyAlias | None:
    if not raw_name:
        return None
    raw = raw_name.strip()
    if raw in EXACT_ALIASES:
        standard, status, source_url, notes = EXACT_ALIASES[raw]
        return CompanyAlias(raw, standard, status, source_url, notes)
    for pattern, target in PATTERN_ALIASES:
        if pattern.search(raw):
            standard, status, source_url, notes = target
            return CompanyAlias(raw, standard, status, source_url, notes)
    if re.fullmatch(r"[A-Za-z0-9 .&-]{2,}", raw):
        return CompanyAlias(raw, raw, "待核实", None, "纯英文/缩写企业名，需核对官网或OCR上下文")
    if len(raw) <= 2:
        return CompanyAlias(raw, raw, "待核实", None, "企业名过短，需人工复核")
    if any(token in raw for token in ["大学", "学院"]) and not any(token in raw for token in ["附属", "医院"]):
        return CompanyAlias(raw, raw, "待核实", None, "疑似学校名误入企业字段")
    return CompanyAlias(raw, raw, "待核实", None, "未命中标准别名库")


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


def build_offer_rows() -> tuple[list[OfferRow], dict[str, CompanyAlias]]:
    df = pd.read_excel(SOURCE_XLSX, sheet_name=0)
    offers: list[OfferRow] = []
    aliases: dict[str, CompanyAlias] = OrderedDict()

    for excel_index, record in df.iterrows():
        source_row_number = excel_index + 2
        school_name = clean_text(record.get("学校名称"))
        major_name = clean_text(record.get("专业名称"))
        if source_row_number in MANUAL_MAJOR_FIXES and not major_name:
            major_name = MANUAL_MAJOR_FIXES[source_row_number]

        for offer_index in range(1, 5):
            if not row_has_offer(record, offer_index):
                continue

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

            if not school_name:
                issues.append("missing_school_name")
            if not major_name:
                issues.append("missing_major_name")
            if not raw_company:
                issues.append("missing_company")
            if not clean_text(record.get(f"offer{offer_index}_工作内容")):
                issues.append("missing_work_content")
            if not clean_text(record.get(f"offer{offer_index}_工作城市")):
                issues.append("missing_work_city")
            if data_year is None:
                issues.append("missing_data_year")
            elif data_year < 2020 or data_year > 2030:
                issues.append("data_year_suspect")
            if first_year_income is not None and first_year_income > 2_500_000:
                issues.append("first_year_income_suspect")
            if annual_bonus is not None and annual_bonus > 800_000:
                issues.append("annual_bonus_suspect")

            company_status = alias.verification_status if alias else "待核实"
            salary_status = "reviewed" if not any(code.endswith("_suspect") for code in issues) else "pending"
            if monthly_salary is None and first_year_income is None:
                salary_status = "pending"
                issues.append("missing_salary_core")

            credibility = "中"
            verification_status = "reviewed"
            if not school_name or not major_name or not raw_company:
                credibility = "待核实"
                verification_status = "pending"

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
                company_verification_status=company_status,
                monthly_salary=monthly_salary,
                annual_bonus=annual_bonus,
                first_year_income=first_year_income,
                work_content=clean_text(record.get(f"offer{offer_index}_工作内容")),
                employment_city=clean_text(record.get(f"offer{offer_index}_工作城市")),
                salary_verification_status=salary_status,
                credibility=credibility,
                verification_status=verification_status,
                issue_codes=sorted(set(issues)),
                extraction_notes=clean_text(record.get("提取备注")),
                raw_payload=raw_payload,
            ))
    return offers, aliases


def sql_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    text = (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f"E'{text}'"


def sql_text_array(values: list[str]) -> str:
    if not values:
        return "'{}'::text[]"
    return "array[" + ", ".join(sql_literal(value) for value in values) + "]::text[]"


def write_csvs(offers: list[OfferRow], aliases: dict[str, CompanyAlias]) -> None:
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
                "issue_codes": "；".join(offer.issue_codes),
            })

    with COMPANY_ALIASES_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["raw_name", "standard_name", "verification_status", "count", "source_url", "notes"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for alias in sorted(aliases.values(), key=lambda item: (-item.count, item.raw_name)):
            writer.writerow(alias.__dict__)

    with COMPANY_REVIEW_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["raw_name", "standard_name", "verification_status", "count", "source_url", "notes"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for alias in sorted(aliases.values(), key=lambda item: (-item.count, item.raw_name)):
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
                    "issue_codes": "；".join(offer.issue_codes),
                })


def alias_values_sql(aliases: list[CompanyAlias]) -> str:
    lines = [
        "insert into public.company_name_aliases (raw_name, standard_name, verification_status, source_url, notes)",
        "values",
    ]
    vals = []
    for alias in aliases:
        row = [
            sql_literal(alias.raw_name),
            sql_literal(alias.standard_name),
            sql_literal(alias.verification_status),
            sql_literal(alias.source_url),
            sql_literal(alias.notes),
        ]
        vals.append("  (" + ", ".join(row) + ")" + ("," if alias is not aliases[-1] else ""))
    lines.extend(vals)
    lines.extend([
        "on conflict (raw_name) do update set",
        "  standard_name = excluded.standard_name,",
        "  verification_status = excluded.verification_status,",
        "  source_url = excluded.source_url,",
        "  notes = excluded.notes,",
        "  updated_at = now();",
    ])
    return "\n".join(lines)


def staging_values_sql(offers: list[OfferRow]) -> str:
    lines = [
        "insert into public.latest_job_offer_import_staging (",
        "  import_batch, source_row_number, offer_index, video_filename,",
        "  school_name, major_name, degree_level, data_year, company_name_raw, company_name_standard,",
        "  company_verification_status, monthly_salary, annual_bonus, first_year_income, work_content,",
        "  employment_city, salary_verification_status, credibility, verification_status, issue_codes, extraction_notes, raw_payload",
        ") values",
    ]
    vals = []
    for offer in offers:
        payload = json.dumps(offer.raw_payload, ensure_ascii=False, default=str)
        row = [
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
            f"{sql_literal(payload)}::jsonb",
        ]
        vals.append("  (" + ", ".join(row) + ")" + ("," if offer is not offers[-1] else ";"))
    return "\n".join(lines + vals)


def write_sql_chunks(offers: list[OfferRow], aliases: dict[str, CompanyAlias]) -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in CHUNKS_DIR.glob("*.sql"):
        old_file.unlink()

    prepare = "\n".join([
        "-- Run supabase/migrations/019_latest_job_offer_schema.sql first.",
        "insert into public.data_sources (source_key, source_name, source_type, source_year, credibility, update_frequency, notes)",
        "values ('latest_job_excel_offer_2026', '最新就业资料.xlsx', '视频转写/OCR整理就业offer', 2026, '中', '按批次更新', '每行最多拆分4个offer')",
        "on conflict (source_key) do update set",
        "  source_name = excluded.source_name,",
        "  source_type = excluded.source_type,",
        "  source_year = excluded.source_year,",
        "  credibility = excluded.credibility,",
        "  update_frequency = excluded.update_frequency,",
        "  notes = excluded.notes;",
        "",
        "-- User requested replacing all old employment data.",
        "delete from public.job_data;",
        f"delete from public.latest_job_offer_import_staging where import_batch = {sql_literal(IMPORT_BATCH)};",
        "",
    ])
    (CHUNKS_DIR / "001_prepare_clear_old_job_data.sql").write_text(prepare, encoding="utf-8")

    alias_list = list(aliases.values())
    for start in range(0, len(alias_list), ALIAS_CHUNK_SIZE):
        chunk = alias_list[start:start + ALIAS_CHUNK_SIZE]
        filename = f"{2 + start // ALIAS_CHUNK_SIZE:03d}_company_aliases_{start + 1}_{start + len(chunk)}.sql"
        (CHUNKS_DIR / filename).write_text(alias_values_sql(chunk), encoding="utf-8")

    offset = 2 + (len(alias_list) + ALIAS_CHUNK_SIZE - 1) // ALIAS_CHUNK_SIZE
    for start in range(0, len(offers), OFFER_CHUNK_SIZE):
        chunk = offers[start:start + OFFER_CHUNK_SIZE]
        filename = f"{offset + start // OFFER_CHUNK_SIZE:03d}_staging_offers_{chunk[0].source_row_number}_{chunk[-1].source_row_number}.sql"
        (CHUNKS_DIR / filename).write_text(staging_values_sql(chunk), encoding="utf-8")

    finalize = "\n".join([
        "insert into public.job_data (",
        "  school_code, school_name, major_code, major_name, degree_level, job_directions, employers, employer_tiers,",
        "  monthly_salary_min, monthly_salary_max, annual_bonus_min, annual_bonus_max, first_year_income_min, first_year_income_max,",
        "  employment_city, data_year, source_id, credibility, verification_status, notes, offer_index, company_name_raw,",
        "  company_name_standard, company_verification_status, salary_verification_status, video_filename, extraction_notes",
        ")",
        "select",
        "  sp.school_code,",
        "  s.school_name,",
        "  mp.major_code,",
        "  s.major_name,",
        "  s.degree_level,",
        "  case when s.work_content is null then '{}'::text[] else array[s.work_content]::text[] end,",
        "  case when s.company_name_standard is null then '{}'::text[] else array[s.company_name_standard]::text[] end,",
        "  '{}'::text[],",
        "  s.monthly_salary,",
        "  s.monthly_salary,",
        "  s.annual_bonus,",
        "  s.annual_bonus,",
        "  s.first_year_income,",
        "  s.first_year_income,",
        "  s.employment_city,",
        "  s.data_year,",
        f"  (select id from public.data_sources where source_key = {sql_literal(SOURCE_KEY)}),",
        "  s.credibility,",
        "  s.verification_status,",
        "  'Excel row ' || s.source_row_number || ', offer ' || s.offer_index || case when cardinality(s.issue_codes) > 0 then ': ' || array_to_string(s.issue_codes, ',') else '' end,",
        "  s.offer_index,",
        "  s.company_name_raw,",
        "  s.company_name_standard,",
        "  s.company_verification_status,",
        "  s.salary_verification_status,",
        "  s.video_filename,",
        "  s.extraction_notes",
        "from public.latest_job_offer_import_staging s",
        "left join lateral (",
        "  select school_code from public.school_profiles",
        "  where public.normalize_school_name(school_name) = public.normalize_school_name(s.school_name)",
        "     or school_name = s.school_name",
        "  order by case when school_name = s.school_name then 0 else 1 end, school_code",
        "  limit 1",
        ") sp on true",
        "left join lateral (",
        "  select major_code from public.major_profiles",
        "  where major_name = s.major_name",
        "  order by major_code",
        "  limit 1",
        ") mp on true",
        f"where s.import_batch = {sql_literal(IMPORT_BATCH)}",
        "  and s.school_name is not null",
        "  and s.major_name is not null",
        "  and s.company_name_raw is not null;",
        "",
        "select",
        "  count(*) filter (where credibility in ('高', '中') and verification_status in ('verified', 'reviewed')) as visible_rows,",
        "  count(*) filter (where company_verification_status = '待核实') as company_pending_rows,",
        "  count(*) filter (where salary_verification_status = 'pending') as salary_pending_rows,",
        "  count(*) as imported_offer_rows",
        "from public.job_data;",
        "",
    ])
    (CHUNKS_DIR / "999_finalize_insert_offers.sql").write_text(finalize, encoding="utf-8")


def write_summary(offers: list[OfferRow], aliases: dict[str, CompanyAlias]) -> None:
    issue_counts = Counter(code for offer in offers for code in offer.issue_codes)
    summary = {
        "source": str(SOURCE_XLSX),
        "import_batch": IMPORT_BATCH,
        "source_rows": 568,
        "offer_rows": len(offers),
        "visible_offer_rows": sum(1 for offer in offers if offer.credibility in {"高", "中"} and offer.verification_status == "reviewed"),
        "company_alias_count": len(aliases),
        "company_pending_alias_count": sum(1 for alias in aliases.values() if alias.verification_status == "待核实"),
        "salary_pending_rows": sum(1 for offer in offers if offer.salary_verification_status == "pending"),
        "school_count": len({offer.school_name for offer in offers if offer.school_name}),
        "major_count": len({offer.major_name for offer in offers if offer.major_name}),
        "issue_counts": dict(sorted(issue_counts.items())),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    offers, aliases = build_offer_rows()
    write_csvs(offers, aliases)
    write_sql_chunks(offers, aliases)
    write_summary(offers, aliases)
    print(SUMMARY_JSON.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
