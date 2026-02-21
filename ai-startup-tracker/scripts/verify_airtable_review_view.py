"""
验证「待复核」视图对应的数据：统计 FundingRounds 中 needs_review=勾选 的记录数并列出前几条。
与 Airtable 里「待复核」视图（筛选 needs_review Is checked）应一致。

在 ai-startup-tracker 目录下执行：
  python scripts/verify_airtable_review_view.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import config
from pyairtable import Api


def main() -> None:
    api_key = (config.AIRTABLE_API_KEY or "").strip()
    base_id = (config.AIRTABLE_BASE_ID or "").strip()
    if not api_key or not base_id:
        print("请设置 AIRTABLE_API_KEY 和 AIRTABLE_BASE_ID")
        sys.exit(1)

    table = Api(api_key).table(base_id, config.TABLE_FUNDING_ROUNDS)
    # 与「待复核」视图一致：needs_review 为勾选
    formula = "{needs_review}=1"
    records = table.all(formula=formula, max_records=100)

    print(f"待复核记录数（needs_review=勾选）: {len(records)}")
    if records:
        print("前 5 条（round_label / company / stage）:")
        for r in records[:5]:
            fields = r.get("fields", {})
            # company 是 link，可能是 list of record ids
            company = fields.get("company") or []
            if isinstance(company, list) and company:
                company = company[0]  # 只显示第一个 link 的 id
            print(f"  - {fields.get('round_label', '')} | company={company} | stage={fields.get('stage', '')}")
    else:
        print("（当前无待复核记录，视图应为空，属正常。）")
    print("\n若上述数量与 Airtable 中「待复核」视图记录数一致，则视图验证通过。")


if __name__ == "__main__":
    main()
