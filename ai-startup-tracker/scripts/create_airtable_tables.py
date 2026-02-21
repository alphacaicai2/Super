"""
通过 Airtable Meta API 在指定 Base 中创建 5 张表及字段。

要求：
- 使用 Personal Access Token（PAT），并勾选 scope: schema.bases:write
- 创建方式：开发者文档 https://airtable.com/developers/web/api/create-table
- 环境变量：.env 中 AIRTABLE_API_KEY（填 PAT）、AIRTABLE_BASE_ID（Base 的 ID，如 appXXXX）

使用：在项目根目录执行
  python scripts/create_airtable_tables.py

若表已存在则跳过；不会删除或修改已有表。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import httpx

BASE_URL = "https://api.airtable.com/v0/meta/bases"
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "").strip()
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "").strip()


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }


def list_bases() -> list[dict]:
    """GET 当前 PAT 可访问的 bases（用于诊断）。"""
    resp = httpx.get(f"{BASE_URL.replace('/bases', '')}/bases", headers=_headers(), timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get("bases", [])


def get_tables(base_id: str) -> list[dict]:
    """GET base 的 tables 列表（含 id、name）。"""
    url = f"{BASE_URL}/{base_id}/tables"
    resp = httpx.get(url, headers=_headers(), timeout=30)
    if resp.status_code == 404:
        print("404 Not Found. 请检查：")
        print("  1. AIRTABLE_BASE_ID 是否为该 Base 的 ID（URL 中 airtable.com/ 后面的 appXXXX...，不要带 table/ 等）")
        print("  2. PAT 是否勾选 schema.bases:read 和 schema.bases:write")
        print("  3. 该 Token 的「可访问的 base」中是否包含此 Base")
        raise SystemExit(1)
    if resp.status_code == 403:
        print("403 Forbidden. PAT 需包含 scope: schema.bases:read 与 schema.bases:write，且 Base 在 Token 访问范围内。")
        raise SystemExit(1)
    resp.raise_for_status()
    data = resp.json()
    return data.get("tables", [])


def create_table(base_id: str, name: str, fields: list[dict]) -> dict:
    """POST 创建一张表，返回表信息（含 id）。"""
    url = f"{BASE_URL}/{base_id}/tables"
    resp = httpx.post(
        url,
        headers=_headers(),
        json={"name": name, "fields": fields},
        timeout=30,
    )
    if resp.status_code == 422:
        print(f"422 创建表「{name}」失败，API 返回：")
        print(resp.text[:1500])
        raise SystemExit(1)
    resp.raise_for_status()
    return resp.json()


def single_select(name: str, choices: list[str]) -> dict:
    return {
        "name": name,
        "type": "singleSelect",
        "options": {"choices": [{"name": c} for c in choices]},
    }


def sources_fields() -> list[dict]:
    return [
        {"name": "title", "type": "singleLineText"},
        single_select("type", ["rss_article", "manual_article", "meeting_note", "memo", "webhook_article", "voice_transcript"]),
        {"name": "url", "type": "url"},
        {"name": "author", "type": "singleLineText"},
        {"name": "published_at", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "source_channel", "type": "singleSelect", "options": {"choices": [{"name": c} for c in ["miniflux", "manual", "meeting", "wechat"]]}},
        {"name": "content_hash", "type": "singleLineText"},
        {"name": "has_funding_signal", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
        single_select("processing_status", ["new", "extracted", "needs_review", "done", "skipped"]),
        {"name": "raw_text", "type": "multilineText"},
        {"name": "raw_text_url", "type": "url"},
        {"name": "tags", "type": "multipleSelects", "options": {"choices": []}},
    ]


def companies_fields() -> list[dict]:
    return [
        {"name": "name_cn", "type": "singleLineText"},
        {"name": "name_en", "type": "singleLineText"},
        {"name": "aliases", "type": "multilineText"},
        {"name": "sector", "type": "multipleSelects", "options": {"choices": [{"name": c} for c in ["LLM", "机器人", "自动驾驶", "AI医疗", "AI芯片", "AI安全", "AI基础设施", "AI应用", "具身智能", "计算机视觉", "NLP", "AI for Science", "其他"]]}},
        {"name": "description", "type": "multilineText"},
        {"name": "website", "type": "url"},
        single_select("status", ["active", "acquired", "closed"]),
        {"name": "founded_year", "type": "number", "options": {"precision": 0}},
        {"name": "first_seen_at", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "last_seen_at", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "notes", "type": "multilineText"},
    ]


def orgs_fields() -> list[dict]:
    return [
        {"name": "name", "type": "singleLineText"},
        {"name": "aliases", "type": "multilineText"},
        single_select("type", ["VC", "PE", "CVC", "Government", "Angel", "Accelerator"]),
        {"name": "website", "type": "url"},
        {"name": "notes", "type": "multilineText"},
    ]


def funding_rounds_fields(companies_table_id: str, orgs_table_id: str, sources_table_id: str) -> list[dict]:
    stages = ["Angel", "Pre-Seed", "Seed", "Pre-A", "A", "A+", "B", "B+", "C", "C+", "D", "E+", "Pre-IPO", "IPO", "Strategic", "Acquisition", "Undisclosed"]
    return [
        {"name": "round_label", "type": "singleLineText"},  # primary, 用于显示
        {"name": "company", "type": "multipleRecordLinks", "options": {"linkedTableId": companies_table_id}},
        single_select("stage", stages),
        {"name": "date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "amount_value", "type": "number", "options": {"precision": 0}},
        single_select("amount_currency", ["CNY", "USD", "EUR", "HKD"]),
        {"name": "amount_raw", "type": "singleLineText"},
        {"name": "valuation_value", "type": "number", "options": {"precision": 0}},
        single_select("valuation_currency", ["CNY", "USD", "EUR", "HKD"]),
        {"name": "valuation_raw", "type": "singleLineText"},
        {"name": "lead_investors", "type": "multipleRecordLinks", "options": {"linkedTableId": orgs_table_id}},
        {"name": "co_investors", "type": "multipleRecordLinks", "options": {"linkedTableId": orgs_table_id}},
        {"name": "source_primary", "type": "multipleRecordLinks", "options": {"linkedTableId": sources_table_id}},
        {"name": "evidence_text", "type": "multilineText"},
        {"name": "confidence", "type": "rating", "options": {"icon": "star", "color": "yellowBright", "max": 5}},
        single_select("verification_status", ["unverified", "verified", "disputed"]),
        {"name": "needs_review", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
        {"name": "review_notes", "type": "multilineText"},
        {"name": "extracted_at", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "model_version", "type": "singleLineText"},
    ]


def extraction_log_fields(sources_table_id: str) -> list[dict]:
    return [
        {"name": "model", "type": "singleLineText"},
        {"name": "source", "type": "multipleRecordLinks", "options": {"linkedTableId": sources_table_id}},
        {"name": "run_at", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        {"name": "input_tokens", "type": "number", "options": {"precision": 0}},
        {"name": "output_tokens", "type": "number", "options": {"precision": 0}},
        single_select("status", ["success", "failed", "partial", "no_funding"]),
        {"name": "error_message", "type": "multilineText"},
        {"name": "raw_output", "type": "multilineText"},
        {"name": "rounds_extracted", "type": "number", "options": {"precision": 0}},
    ]


def main() -> None:
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("请设置环境变量 AIRTABLE_API_KEY（Personal Access Token，需勾选 schema.bases:write）和 AIRTABLE_BASE_ID")
        sys.exit(1)

    # 诊断：列出可访问的 bases，便于核对 BASE_ID
    bases = list_bases()
    if bases:
        print("当前 PAT 可访问的 Base：")
        for b in bases:
            bid = b.get("id", "")
            name = b.get("name", "")
            mark = " <-- 当前" if bid == AIRTABLE_BASE_ID else ""
            print(f"  {bid}  {name}{mark}")
        print()
    elif AIRTABLE_BASE_ID:
        print("(无法列出 bases，请确认 PAT 含 schema.bases:read)\n")

    existing = {t["name"]: t["id"] for t in get_tables(AIRTABLE_BASE_ID)}
    table_ids: dict[str, str] = {}

    # 1. Sources
    if "Sources" not in existing:
        t = create_table(AIRTABLE_BASE_ID, "Sources", sources_fields())
        table_ids["Sources"] = t["id"]
        print("Created table: Sources")
    else:
        table_ids["Sources"] = existing["Sources"]
        print("Table already exists: Sources")

    # 2. Companies
    if "Companies" not in existing:
        t = create_table(AIRTABLE_BASE_ID, "Companies", companies_fields())
        table_ids["Companies"] = t["id"]
        print("Created table: Companies")
    else:
        table_ids["Companies"] = existing["Companies"]
        print("Table already exists: Companies")

    # 3. Orgs
    if "Orgs" not in existing:
        t = create_table(AIRTABLE_BASE_ID, "Orgs", orgs_fields())
        table_ids["Orgs"] = t["id"]
        print("Created table: Orgs")
    else:
        table_ids["Orgs"] = existing["Orgs"]
        print("Table already exists: Orgs")

    # 4. FundingRounds（依赖前三张表的 id）
    if "FundingRounds" not in existing:
        t = create_table(
            AIRTABLE_BASE_ID,
            "FundingRounds",
            funding_rounds_fields(table_ids["Companies"], table_ids["Orgs"], table_ids["Sources"]),
        )
        table_ids["FundingRounds"] = t["id"]
        print("Created table: FundingRounds")
    else:
        print("Table already exists: FundingRounds")

    # 5. ExtractionLog
    if "ExtractionLog" not in existing:
        t = create_table(AIRTABLE_BASE_ID, "ExtractionLog", extraction_log_fields(table_ids["Sources"]))
        print("Created table: ExtractionLog")
    else:
        print("Table already exists: ExtractionLog")

    print("Done. Base 中表名与 config.py 中 TABLE_* 一致即可被 Pipeline 使用。")


if __name__ == "__main__":
    main()
