# AI 创业公司数据提取系统 — 详细方案

> 基于 ChatGPT 对话复盘，补充缺失环节，给出可直接执行的实施方案。

---

## 〇、复盘：原方案优缺点

### ✅ 原方案做对了什么

| 方面 | 评价 |
|------|------|
| 三段式架构（采集 → 抽取 → 归一化） | 工程上正确，职责清晰 |
| evidence + confidence 硬约束 | 数据可追溯性的关键，必须有 |
| 人在回路（Human-in-the-loop） | 实际上这类信息抽取任务 80% 收益来自此 |
| 先跑 Schema 抽取、延迟微调 | 符合成本效益：微调投入大，早期数据不够 |
| Claims 表做冲突管理 | 多来源融资数据必然有矛盾，这是正确的信息治理思路 |
| Sources 统一入口 | 把"输入渠道"和"事实对象"解耦，架构上干净 |

### ❌ 原方案缺什么 / 需要改进

| 缺失项 | 影响 |
|--------|------|
| **没选技术栈** | 用什么语言、什么 LLM、怎么部署？全是空白 |
| **没有成本估算** | LLM API 按 token 收费，Airtable 有行数上限（Pro 100K），不算账会踩坑 |
| **Airtable 局限性没讨论** | API 限速 5 req/s、无全文搜索、Automation 有限 → 数据量大了就撞墙 |
| **没给实际 Prompt / JSON Schema** | 只说"用 Schema 抽取"但没给能直接用的模板 |
| **实体归一化只说了方向** | "做 Entity Resolution"容易说，怎么实现？规则？向量？LLM？ |
| **无错误处理设计** | LLM 返回非法 JSON、漏字段、幻觉实体怎么办？ |
| **无部署 / 调度方案** | Pipeline 怎么跑？定时？Webhook？哪里跑？ |
| **无监控告警** | Pipeline 挂了谁知道？抽取质量下降了怎么发现？ |
| **数据量估算空白** | 每天多少篇？每月多少条融资？决定了你选什么架构 |

---

## 一、需求澄清 & 数据量估算

### 1.1 核心目标

从中文 AI/科技类公众号和新闻源中，**自动抽取结构化的融资事件数据**，存进关系型数据库，支持查询、分析和人工复核。

### 1.2 数据量假设（请根据实际调整）

| 指标 | 估算 | 影响 |
|------|------|------|
| RSS 源数量 | 30–100 个公众号/媒体 | 决定采集频率 |
| 日均新文章 | 50–200 篇 | 决定 LLM 调用量和成本 |
| 其中涉及融资的 | ~10–30%（5–60 篇/天） | 只有这些需要走抽取 |
| 月均新增融资事件 | 100–500 条 | 决定 Airtable 是否够用 |
| 人工复核量 | 抽取量的 10–20% | 决定复核 UI 投入 |

### 1.3 数据量结论

- 年融资事件 ≈ 1,200–6,000 条，加上公司/机构实体，**Airtable Pro（100K 行/base）1–2 年内完全够用**。
- 如果未来量级剧增（>10 万行），再迁移到 Supabase/PostgreSQL。
- **MVP 阶段用 Airtable 没问题，不要过早上数据库。**

---

## 二、技术栈选型

| 层 | 选择 | 理由 |
|----|------|------|
| **语言** | Python 3.11+ | 生态最全：LLM SDK、数据处理、Airtable SDK |
| **LLM** | Claude 3.5 Sonnet（主力）或 GPT-4o-mini（成本敏感时） | 中文结构化抽取准确率高；4o-mini 便宜但中文弱一档 |
| **采集** | Miniflux（你已有）+ pyairtable | Miniflux API 拉文章，pyairtable 写 Airtable |
| **调度** | GitHub Actions（免费 2000 min/月）或本地 cron | MVP 阶段不需要 Airflow/Prefect |
| **存储** | Airtable（主库）+ 本地 JSON 日志（备份/审计） | Airtable 做查询和复核 UI；JSON 做训练数据沉淀 |
| **复核 UI** | Airtable Interface（内建，零开发） | 不需要单独写前端 |
| **监控** | 简单：每次运行写日志 + 失败发 Telegram/微信通知 | MVP 不上 Prometheus |

### 成本估算（月）

| 项目 | 费用 |
|------|------|
| Claude Sonnet（假设 30 篇/天 × 30 天 × ~3K tokens/篇） | ~$5–15 |
| Airtable Pro | $20/月 |
| Miniflux（自建） | $0（已有） |
| GitHub Actions | $0（免费额度内） |
| **合计** | **~$25–35/月** |

---

## 三、数据模型（Airtable 表结构）

原方案的 6 张表设计思路对，但 MVP 应精简为 **4 张主表 + 1 张辅助表**，后续按需加。

### 3.1 MVP 表结构（5 张表）

#### 表 1：Sources（来源，统一入口）

> 替代原方案的 Articles 表，同时兼容手动输入。

| 字段 | 类型 | 说明 |
|------|------|------|
| source_id | Auto Number | 主键 |
| type | Single Select | `rss_article` / `manual_article` / `meeting_note` / `memo` |
| title | Single Line | 标题 |
| url | URL | 原文链接（文章有，笔记无） |
| author | Single Line | 公众号名 / 作者 |
| published_at | Date | 发表时间 |
| created_at | Created Time | 入库时间 |
| source_channel | Single Select | `miniflux` / `manual` / `meeting` / `wechat` |
| content_hash | Single Line | MD5 去重 |
| has_funding_signal | Checkbox | 标题/正文是否命中融资关键词 |
| processing_status | Single Select | `new` / `extracted` / `needs_review` / `done` / `skipped` |
| raw_text_url | URL | 正文存外部（R2/S3/GitHub），Airtable 只存链接 |
| tags | Multiple Select | 自由标签 |

> **注意**：Airtable 长文本字段有 100K 字符上限。公众号文章正文建议存外部对象存储（Cloudflare R2 免费 10GB），Airtable 只存链接和摘要。

#### 表 2：Companies（公司）

| 字段 | 类型 | 说明 |
|------|------|------|
| company_id | Auto Number | 主键 |
| name_cn | Single Line | 中文名 |
| name_en | Single Line | 英文名 |
| aliases | Long Text | 其他名称，逗号分隔 |
| sector | Multiple Select | `LLM` / `机器人` / `自动驾驶` / `AI医疗` / `AI芯片` / ... |
| description | Long Text | 一句话描述 |
| website | URL | 官网 |
| status | Single Select | `active` / `acquired` / `closed` |
| founded_year | Number | 成立年份 |
| funding_rounds | Link to FundingRounds | 反向关联 |
| first_seen_at | Date | 首次出现时间 |
| last_seen_at | Date | 最近一次出现 |
| notes | Long Text | 备注 |

#### 表 3：Orgs（投资机构）

| 字段 | 类型 | 说明 |
|------|------|------|
| org_id | Auto Number | 主键 |
| name | Single Line | 机构名 |
| aliases | Long Text | 别名（红杉中国, Sequoia China, HongShan...） |
| type | Single Select | `VC` / `PE` / `CVC` / `Government` / `Angel` / `Accelerator` |
| website | URL | 官网 |
| funding_rounds_lead | Link to FundingRounds | 领投的轮次 |
| funding_rounds_participated | Link to FundingRounds | 参投的轮次 |
| notes | Long Text | 备注 |

#### 表 4：FundingRounds（融资轮次）⭐ 核心表

| 字段 | 类型 | 说明 |
|------|------|------|
| round_id | Auto Number | 主键 |
| company | Link to Companies | 融资公司 |
| stage | Single Select | `Angel` / `Pre-Seed` / `Seed` / `Pre-A` / `A` / `A+` / `B` / `C` / `D` / `E+` / `Pre-IPO` / `IPO` / `Strategic` / `Acquisition` / `Undisclosed` |
| date | Date | 融资日期 |
| amount_value | Number | 金额数值 |
| amount_currency | Single Select | `CNY` / `USD` / `EUR` / `HKD` |
| amount_raw | Single Line | 原文表述（如"数亿元"） |
| valuation_value | Number | 估值数值（若有） |
| valuation_currency | Single Select | 币种 |
| valuation_raw | Single Line | 原文表述 |
| lead_investors | Link to Orgs | 领投方（多选） |
| co_investors | Link to Orgs | 跟投方（多选） |
| source_primary | Link to Sources | 主要信息来源 |
| evidence_text | Long Text | 原文证据片段（直接引用） |
| confidence | Rating (1–5) | 模型置信度 |
| verification_status | Single Select | `unverified` / `verified` / `disputed` |
| needs_review | Checkbox | 是否需人工复核 |
| review_notes | Long Text | 复核备注 |
| extracted_at | Date | 抽取时间 |
| model_version | Single Line | 用的什么模型 |

#### 表 5：ExtractionLog（抽取日志，辅助表）

| 字段 | 类型 | 说明 |
|------|------|------|
| log_id | Auto Number | 主键 |
| source | Link to Sources | 处理的来源 |
| run_at | Created Time | 运行时间 |
| model | Single Line | 模型名+版本 |
| input_tokens | Number | 输入 token 数 |
| output_tokens | Number | 输出 token 数 |
| status | Single Select | `success` / `failed` / `partial` / `no_funding` |
| error_message | Long Text | 失败原因 |
| raw_output | Long Text | 模型原始输出（JSON） |
| rounds_extracted | Number | 抽出了几条融资事件 |

> **第二阶段再加的表**：People（人物）、Claims（多来源冲突声明）、Evidence（独立证据表）。MVP 先把证据文本直接存 FundingRounds 的 `evidence_text` 字段。

---

## 四、Pipeline 架构

```
                          ┌────────────────┐
                          │   Miniflux     │
                          │  (RSS 采集)     │
                          └───────┬────────┘
                                  │ API 拉取新文章
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Pipeline                           │
│                                                              │
│  ① 采集 ──→ ② 预处理 ──→ ③ 过滤 ──→ ④ 抽取 ──→ ⑤ 归一化   │
│                                                              │
│  ① Miniflux API 拉 unread 文章                               │
│  ② 清洗 HTML：去导航/广告/二维码/推荐阅读                      │
│  ③ 关键词匹配：含"融资/估值/轮/领投/跟投"等才继续               │
│  ④ LLM 结构化抽取（JSON Schema + evidence + confidence）      │
│  ⑤ 实体归一化：公司名/机构名查 Airtable 已有记录做匹配          │
│                                                              │
│              ┌──────────┐                                    │
│              │ ⑥ 写入    │                                    │
│              │ Airtable  │                                    │
│              └──────────┘                                    │
│                                                              │
│  confidence < 3 或 金额缺失 或 实体未匹配 → needs_review=true  │
│                                                              │
│  ⑦ 日志写入 ExtractionLog + 本地 JSONL 备份                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                     ┌─────────────────────┐
                     │  Airtable Interface  │
                     │  （人工复核 UI）       │
                     │                      │
                     │  左：原文片段+抽取结果 │
                     │  右：修正字段、选实体   │
                     └─────────────────────┘
                                  │
                                  ▼
                     ┌─────────────────────┐
                     │  训练数据沉淀         │
                     │  改动前 vs 改动后     │
                     │  → JSONL 存本地/R2   │
                     └─────────────────────┘
```

---

## 五、核心实现细节

### 5.1 预处理（决定质量上限）

```python
import re
from bs4 import BeautifulSoup

def clean_article(html: str) -> str:
    """清洗公众号/新闻 HTML，只保留正文。"""
    soup = BeautifulSoup(html, "html.parser")

    # 删除无关元素
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # 删除常见公众号干扰段
    noise_patterns = [
        r"扫码关注", r"长按识别", r"点击阅读原文",
        r"推荐阅读", r"往期精选", r"版权声明",
        r"免责声明", r"转载请注明", r"广告",
    ]
    text = soup.get_text(separator="\n", strip=True)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if any(re.search(p, line) for p in noise_patterns):
            continue
        if len(line.strip()) < 2:
            continue
        cleaned.append(line.strip())
    return "\n".join(cleaned)


FUNDING_KEYWORDS = [
    "融资", "估值", "轮融", "领投", "跟投", "天使轮",
    "Pre-A", "A轮", "B轮", "C轮", "D轮", "IPO",
    "战略投资", "种子轮", "亿元", "亿美元", "万美元",
    "获投", "完成融资", "宣布融资",
]

def has_funding_signal(title: str, text: str) -> bool:
    """判断文章是否涉及融资。"""
    combined = title + " " + text[:500]
    return any(kw in combined for kw in FUNDING_KEYWORDS)
```

### 5.2 LLM 结构化抽取（完整 Prompt + JSON Schema）

这是**整个系统最核心的部分**。原方案只说了方向，这里给出可直接使用的 Prompt。

#### JSON Schema（抽取目标结构）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "has_funding_info": {
      "type": "boolean",
      "description": "文章是否包含具体的融资事件信息"
    },
    "funding_rounds": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "company_name_cn": { "type": "string" },
          "company_name_en": { "type": ["string", "null"] },
          "company_sector": {
            "type": "string",
            "enum": ["LLM", "机器人", "自动驾驶", "AI医疗", "AI芯片",
                     "AI安全", "AI基础设施", "AI应用", "具身智能",
                     "计算机视觉", "NLP", "AI for Science", "其他"]
          },
          "stage": {
            "type": "string",
            "enum": ["Angel", "Pre-Seed", "Seed", "Pre-A", "A", "A+",
                     "B", "B+", "C", "C+", "D", "E+", "Pre-IPO", "IPO",
                     "Strategic", "Acquisition", "Undisclosed"]
          },
          "date": {
            "type": ["string", "null"],
            "description": "YYYY-MM-DD 格式，从文中推断"
          },
          "amount": {
            "type": ["object", "null"],
            "properties": {
              "value": { "type": "number" },
              "currency": { "type": "string", "enum": ["CNY", "USD", "EUR", "HKD"] },
              "raw_text": { "type": "string", "description": "原文表述，如'数亿元人民币'" }
            }
          },
          "valuation": {
            "type": ["object", "null"],
            "properties": {
              "value": { "type": "number" },
              "currency": { "type": "string" },
              "raw_text": { "type": "string" }
            }
          },
          "lead_investors": {
            "type": "array",
            "items": { "type": "string" },
            "description": "领投方名称列表"
          },
          "co_investors": {
            "type": "array",
            "items": { "type": "string" },
            "description": "跟投方名称列表"
          },
          "evidence": {
            "type": "string",
            "description": "支撑此融资事件的原文片段，直接引用，不要改写"
          },
          "confidence": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "1=非常不确定, 3=有依据但有缺失, 5=明确完整"
          },
          "confidence_notes": {
            "type": "string",
            "description": "置信度低的原因，如'金额为推测'、'轮次未明确提及'"
          }
        },
        "required": ["company_name_cn", "stage", "evidence", "confidence"]
      }
    }
  },
  "required": ["has_funding_info", "funding_rounds"]
}
```

#### System Prompt

```text
你是一个专业的 AI 创投信息抽取助手。你的任务是从中文科技/财经文章中提取结构化的融资事件数据。

## 规则

1. **只抽取文中明确提到的信息**，不要推测、补充或编造任何内容。
2. 每个融资事件必须有 `evidence` 字段——直接引用原文中的关键句子，不要改写。
3. 如果文章提到多个公司/多轮融资，为每个事件分别输出一条记录。
4. 金额处理：
   - "数亿元" → value 留空(null)，raw_text 填 "数亿元人民币"
   - "超过5亿美元" → value: 500000000, currency: "USD", raw_text: "超过5亿美元"
   - "近1亿元" → value: 100000000, currency: "CNY", raw_text: "近1亿元人民币"
   - 如果完全没提金额，amount 整体为 null
5. 轮次映射：
   - "A轮" / "Series A" / "A round" → "A"
   - "天使轮" → "Angel"
   - "战略融资" / "战略投资" → "Strategic"
   - "被收购" / "并购" → "Acquisition"
   - 如果文章只说"获得融资"但没说轮次 → "Undisclosed"
6. 日期：尽量从文中推断，格式 YYYY-MM-DD。如果只提到"近日"、"日前"，用文章发表日期。
7. confidence 打分标准：
   - 5 = 公司名+轮次+金额+投资方全部明确
   - 4 = 缺少一项（如金额未披露，但其他明确）
   - 3 = 缺少两项或有模糊表述
   - 2 = 信息零散，需推断
   - 1 = 仅隐约提及，高度不确定
8. 如果文章不包含任何融资信息，返回 `{"has_funding_info": false, "funding_rounds": []}`

## 输出格式

严格按照提供的 JSON Schema 输出，不要添加额外字段，不要输出 JSON 以外的任何文字。
```

#### User Prompt 模板

```text
请从以下文章中提取融资事件信息。

文章标题：{title}
发表日期：{published_at}
来源：{source_channel}

---

{cleaned_text}
```

### 5.3 实体归一化（具体策略）

原方案只说"做 Entity Resolution"，这里给出 **MVP 可落地的三步法**：

#### Step 1：精确匹配 + 别名查表

```python
def find_existing_entity(name: str, table: str, airtable_client) -> str | None:
    """在 Airtable 中查找已有实体。"""
    # 1. 精确匹配 name 字段
    records = airtable_client.search(table, field="name", value=name)
    if records:
        return records[0]["id"]

    # 2. 查别名字段（aliases 是逗号分隔的文本）
    all_records = airtable_client.get_all(table, fields=["name", "aliases"])
    for record in all_records:
        aliases = record.get("aliases", "") or ""
        alias_list = [a.strip() for a in aliases.split(",")]
        if name in alias_list:
            return record["id"]

    return None  # 没找到，需要新建
```

#### Step 2：模糊匹配（中英文 + 缩写）

```python
# 常见中英文映射规则
KNOWN_MAPPINGS = {
    "红杉": ["红杉中国", "红杉资本", "Sequoia China", "HongShan"],
    "高瓴": ["高瓴创投", "高瓴资本", "Hillhouse Capital", "Hillhouse"],
    "经纬": ["经纬创投", "经纬中国", "Matrix Partners China"],
    "真格": ["真格基金", "ZhenFund"],
    "IDG": ["IDG资本", "IDG Capital"],
    # ... 维护一份核心投资机构别名表（约 50-100 家）
}

def fuzzy_match_org(name: str) -> str | None:
    """模糊匹配机构名。"""
    for canonical, aliases in KNOWN_MAPPINGS.items():
        if name in aliases or canonical in name:
            return canonical
    return None
```

#### Step 3：未匹配实体 → 新建 + 标记复核

```python
def resolve_entity(name: str, entity_type: str, airtable_client):
    """归一化实体：已有的 link，没有的新建。"""
    table = "Companies" if entity_type == "company" else "Orgs"

    # 先精确查
    existing_id = find_existing_entity(name, table, airtable_client)
    if existing_id:
        return existing_id

    # 再模糊查（仅对机构）
    if entity_type == "org":
        canonical = fuzzy_match_org(name)
        if canonical:
            existing_id = find_existing_entity(canonical, table, airtable_client)
            if existing_id:
                # 把当前名字加入 aliases
                update_aliases(existing_id, name, table, airtable_client)
                return existing_id

    # 都没匹配 → 新建，标记为待复核
    new_record = airtable_client.create(table, {
        "name" if entity_type == "org" else "name_cn": name,
        "notes": "⚠️ 自动创建，待复核",
    })
    return new_record["id"]
```

### 5.4 写入 Airtable + needs_review 触发规则

```python
REVIEW_TRIGGERS = [
    lambda r: r["confidence"] <= 3,                        # 低置信度
    lambda r: r["amount"] is None and r["stage"] != "Undisclosed",  # 有轮次但无金额
    lambda r: len(r["lead_investors"]) == 0,               # 无领投方
    lambda r: r["stage"] == "Undisclosed",                 # 轮次不明
    # 未来加：同公司同轮次已有记录 → 冲突
]

def should_review(extracted_round: dict) -> bool:
    return any(trigger(extracted_round) for trigger in REVIEW_TRIGGERS)
```

### 5.5 错误处理（原方案完全缺失）

```python
import json
import time

MAX_RETRIES = 2

def extract_with_retry(text: str, title: str, published_at: str, source_channel: str):
    """带重试和校验的 LLM 抽取。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_output = call_llm(text, title, published_at, source_channel)

            # 1. 尝试解析 JSON
            result = json.loads(raw_output)

            # 2. Schema 校验（必须有 has_funding_info 和 funding_rounds）
            assert "has_funding_info" in result
            assert "funding_rounds" in result
            assert isinstance(result["funding_rounds"], list)

            # 3. 每条融资必须有必填字段
            for r in result["funding_rounds"]:
                assert "company_name_cn" in r
                assert "stage" in r
                assert "evidence" in r
                assert "confidence" in r

            return result

        except (json.JSONDecodeError, AssertionError, KeyError) as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            else:
                return {
                    "error": str(e),
                    "raw_output": raw_output[:2000],
                    "has_funding_info": None,
                    "funding_rounds": [],
                }
```

---

## 六、复核流程

### 6.1 Airtable Interface 设计

在 Airtable 中创建一个 Interface（零代码）：

**视图名**：`🔍 待复核`

**筛选条件**：`needs_review = true` AND `verification_status = unverified`

**布局**：

| 左侧面板 | 右侧面板 |
|-----------|----------|
| `evidence_text`（原文片段） | `company`（可改） |
| `source_primary.title`（来源标题） | `stage`（可改） |
| `source_primary.url`（原文链接） | `amount_value` / `amount_currency` |
| `confidence` + `confidence_notes` | `lead_investors` / `co_investors` |
| `model_version` | `verification_status`（改为 verified） |
| | `review_notes`（写备注） |

### 6.2 复核后沉淀训练数据

每当 `verification_status` 从 `unverified` 变为 `verified`，用 Airtable Automation 触发一个 Webhook：

```jsonl
{
  "article_title": "...",
  "article_text_snippet": "...(前 2000 字)...",
  "model_output": { ... 原始抽取结果 ... },
  "human_corrected": { ... 修正后结果 ... },
  "correction_type": "amount_fixed | entity_changed | stage_changed | ...",
  "corrected_at": "2026-02-21T10:00:00Z"
}
```

存到本地 `training_data/corrections.jsonl`，后续微调时直接可用。

---

## 七、分阶段实施路线图

> 原则：每个 Phase 结束后系统都是**可用的**，不存在"做完一半不能跑"的情况。
> 每个 Phase 都标注了：目标、具体任务、产出物、验收标准、预估时间。

---

### Phase 0：项目脚手架 + Airtable 建表（Day 1 上午）

**目标**：建好项目骨架和数据库，后续所有代码都在这个结构里写。

#### 任务清单

| # | 任务 | 产出 |
|---|------|------|
| 0.1 | 创建项目目录 `ai-startup-tracker/`，初始化 git | 空仓库 |
| 0.2 | 创建 `requirements.txt`，锁定核心依赖版本 | 依赖清单 |
| 0.3 | 创建 `.env.example`，列出所有需要的环境变量 | 配置模板 |
| 0.4 | 创建 `config.py`，定义常量、表名、枚举映射 | 配置中心 |
| 0.5 | 在 Airtable 建 5 张表：Sources, Companies, Orgs, FundingRounds, ExtractionLog | 可查看的空表 |
| 0.6 | 写 `storage/base.py`（StorageBackend 抽象接口） | 存储层接口 |
| 0.7 | 写 `storage/airtable_backend.py`（Airtable 实现） | MVP 存储实现 |

#### 依赖清单（requirements.txt）

```
anthropic>=0.40.0         # Claude SDK（主力 LLM）
litellm>=1.50.0           # LLM 代理层（方便换模型）
pydantic>=2.5.0           # 数据校验
pyairtable>=2.3.0         # Airtable SDK
beautifulsoup4>=4.12.0    # HTML 清洗
httpx>=0.27.0             # HTTP 客户端（Miniflux API）
tenacity>=8.2.0           # 重试
python-dotenv>=1.0.0      # 环境变量
```

#### 环境变量（.env.example）

```
ANTHROPIC_API_KEY=sk-ant-...
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...
MINIFLUX_URL=https://your-miniflux.example.com
MINIFLUX_API_KEY=...
TELEGRAM_BOT_TOKEN=...       # Phase 2 才需要
TELEGRAM_CHAT_ID=...         # Phase 2 才需要
```

#### 项目文件结构（Phase 0 结束时）

```
ai-startup-tracker/
├── .env.example
├── .gitignore
├── requirements.txt
├── config.py
├── storage/
│   ├── __init__.py
│   ├── base.py                 # StorageBackend 抽象接口
│   └── airtable_backend.py     # Airtable 实现
├── adapters/
│   ├── __init__.py
│   └── base.py                 # SourceAdapter 抽象基类
├── prompts/
│   ├── system_prompt.txt
│   └── extraction_schema.json
└── data/
    └── org_aliases.json        # 先放空 {}
```

#### 验收标准

- [ ] `pip install -r requirements.txt` 成功
- [ ] Airtable 5 张表建好，字段类型正确，Link 关系已建立
- [ ] `storage/airtable_backend.py` 能跑通：创建一条 Sources 记录 → 读回来 → 删除

---

### 多 Agent 并行开发指南

**结论：可以多 Agent 并行**，前提是**先定好接口、按轨道分工、避免改同一文件**。

#### 原则

1. **接口先行**：Phase 0 的 `StorageBackend`、`SourceAdapter`、`config.py` 和 Pydantic 数据模型先定好，各轨道只依赖接口不依赖实现细节。
2. **按轨道分文件**：每个 Agent 负责一组文件，尽量不交叉（减少 merge 冲突）。
3. **串行关卡**：Phase 0 必须全部完成后，Phase 1 的轨道才能并行；`run_pipeline.py` 依赖所有 pipeline 模块，放在最后或由一人收尾。

#### Phase 0 并行分工

| 轨道 | Agent | 负责内容 | 依赖 |
|------|--------|----------|------|
| **A：基础** | Agent 1 | 目录结构、`requirements.txt`、`.env.example`、`config.py`、`.gitignore` | 无 |
| **B：存储** | Agent 2 | `storage/base.py`、`storage/airtable_backend.py`、`storage/__init__.py` | 需 config（A 先提交） |
| **C：适配器与资源** | Agent 3 | `adapters/base.py`、`adapters/__init__.py`、`prompts/system_prompt.txt`、`prompts/extraction_schema.json`、`data/org_aliases.json` | 无（与 A 可同时） |
| **D：建表清单** | Agent 4 或人工 | `docs/airtable-setup-checklist.md`（建表字段与步骤） | 无 |

**推荐顺序**：A 先做并 push → B、C、D 可同时进行（B/C 依赖 A 的 config 与目录）。

#### Phase 1 并行分工

| 轨道 | Agent | 负责文件 | 依赖 |
|------|--------|----------|------|
| **P1：采集+预处理** | Agent 1 | `adapters/rss_article.py`、`pipeline/fetch_miniflux.py`、`pipeline/preprocess.py`、`pipeline/__init__.py` | Phase 0 完成；StorageBackend、SourceAdapter 接口 |
| **P2：抽取+模型** | Agent 2 | `models/schemas.py`、`models/__init__.py`、`pipeline/extract.py` | Phase 0 完成；prompts、config |
| **P3：归一化+写入** | Agent 3 | `pipeline/normalize.py`、`pipeline/write_airtable.py` | Phase 0 完成；StorageBackend、config、data/org_aliases.json |
| **P4：编排+测试** | Agent 4 或 1 | `run_pipeline.py`、`tests/test_preprocess.py`、`tests/test_extract.py`、`tests/sample_articles/` | P1、P2、P3 均完成 |

**依赖关系**：P1、P2、P3 之间**无代码依赖**（只共享 `config`、`storage`、`models`），可并行开发。P4 必须在 P1～P3 合并后再做。

#### 接口契约（各轨道需遵守）

- **StorageBackend**（B 轨道实现，P1/P3 调用）：`create_source`、`get_pending_sources`、`update_source_status`、`find_company`、`find_org`、`create_company`、`create_org`、`create_funding_round`、`create_extraction_log`。见 `storage/base.py`。
- **SourceAdapter**（C 轨道定义，P1 使用）：`preprocess(raw_content, metadata) -> ProcessedContent`、`default_reliability() -> str`。见 `adapters/base.py`。
- **抽取输出**（P2 产出，P3 消费）：Pydantic 模型 `ExtractionResult`，含 `has_funding_info`、`funding_rounds: list[FundingRound]`。见 `models/schemas.py`。

#### 风险与注意

- **同一文件多人改**：避免。若必须（如 `config.py` 加新常量），约定由 A 轨道负责人统一改。
- **合并顺序**：建议 A → B/C/D 合并 → P1/P2/P3 合并 → P4 合并；每次合并后跑一遍 `pip install -r requirements.txt` 和最小冒烟测试（如创建一条 Source）。
- **Airtable 建表**：只能人工在 Airtable 里操作，可与 Phase 0 代码并行；建表清单文档由 D 轨道产出，便于多人/多 Agent 对齐。

---

### Phase 1：单通道 MVP — RSS 采集 + 抽取（Day 1 下午 – Day 3）

**目标**：从 Miniflux 拉文章 → LLM 抽取 → 写入 Airtable。**一条命令跑通全流程。**

#### 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | 写 RSS 采集适配器 | `adapters/rss_article.py` | Adapter 模式第一个实现：清洗 HTML + 去公众号噪声 |
| 1.2 | 写 Miniflux 采集模块 | `pipeline/fetch_miniflux.py` | 调 Miniflux API 拉 unread 文章 → 去重(content_hash) → 写入 Sources(status=new) |
| 1.3 | 写预处理 + 过滤模块 | `pipeline/preprocess.py` | 调用 Adapter 做清洗 + 融资关键词过滤(has_funding_signal) |
| 1.4 | 写 LLM 抽取模块 | `pipeline/extract.py` | System Prompt + JSON Schema + Pydantic 校验 + 重试 |
| 1.5 | 写实体归一化模块 | `pipeline/normalize.py` | 精确匹配 → 别名查表 → 新建+标记复核 |
| 1.6 | 写主入口 | `run_pipeline.py` | 串联：fetch → preprocess → filter → extract → normalize → write |
| 1.7 | 写 ExtractionLog 记录 | 集成在 `run_pipeline.py` | 每次抽取记录 token 数、状态、错误信息 |
| 1.8 | 手动测试 10 篇文章 | — | 验证抽取质量，调优 Prompt |

#### 数据流（Phase 1）

```
Miniflux API
    │
    ▼
fetch_miniflux.py ──→ Sources 表 (status=new)
    │
    ▼
run_pipeline.py 读取 status=new 的 Sources
    │
    ├─ preprocess.py (RSSArticleAdapter 清洗)
    │
    ├─ has_funding_signal? ──No──→ status=skipped, 结束
    │                     └─Yes─┐
    │                           ▼
    ├─ extract.py (LLM → JSON → Pydantic 校验)
    │
    ├─ normalize.py (公司名/机构名 → Airtable 实体)
    │
    ├─ write_airtable.py (→ FundingRounds)
    │   └─ should_review? → needs_review=true
    │
    └─ ExtractionLog 记录
```

#### 文件结构（Phase 1 结束时新增）

```
ai-startup-tracker/
├── adapters/
│   ├── base.py
│   └── rss_article.py          ← new
├── pipeline/
│   ├── __init__.py              ← new
│   ├── fetch_miniflux.py        ← new
│   ├── preprocess.py            ← new
│   ├── extract.py               ← new
│   ├── normalize.py             ← new
│   └── write_airtable.py        ← new
├── models/
│   ├── __init__.py              ← new
│   └── schemas.py               ← new (Pydantic models)
├── run_pipeline.py              ← new
└── tests/
    ├── test_preprocess.py       ← new
    ├── test_extract.py          ← new
    └── sample_articles/         ← new (10 篇测试文章)
```

#### 验收标准

- [ ] `python run_pipeline.py` 一条命令跑完全流程
- [ ] 10 篇测试文章中：含融资的正确抽取 ≥ 70%，不含融资的正确跳过 ≥ 90%
- [ ] FundingRounds 表中出现结构化记录，evidence 字段有原文引用
- [ ] ExtractionLog 记录了每次运行的 token 数和状态
- [ ] 重复运行不会产生重复数据（content_hash 去重生效）

---

### Phase 2：闭环运行 — 复核 + 自动调度 + 监控（Day 4 – Day 6）

**目标**：系统能无人值守运行，你只需每天打开 Airtable 花 10 分钟复核。

#### 任务清单

| # | 任务 | 文件/位置 | 说明 |
|---|------|-----------|------|
| 2.1 | 搭 Airtable Interface 复核视图 | Airtable 界面 | 筛选 needs_review=true，左边原文右边修改 |
| 2.2 | 搭 Airtable 统计 Dashboard | Airtable 界面 | 本周新增融资数、待复核数、各轮次分布 |
| 2.3 | 写 GitHub Actions 定时任务 | `.github/workflows/extract.yml` | 每 6 小时跑一次 run_pipeline.py |
| 2.4 | 写通知模块 | `pipeline/notify.py` | 运行成功/失败发 Telegram 消息 |
| 2.5 | 写投资机构别名表（种子数据） | `data/org_aliases.json` | 先手工整理 50 家头部机构的中英文别名 |
| 2.6 | 运行日报 | 集成在 notify.py | 每天汇总：新采集 X 篇，含融资 Y 篇，抽取 Z 条，待复核 W 条 |

#### GitHub Actions 定时调度

```yaml
# .github/workflows/extract.yml
name: Extract Funding Data
on:
  schedule:
    - cron: '0 */6 * * *'   # 每 6 小时
  workflow_dispatch:          # 手动触发

jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python run_pipeline.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          AIRTABLE_API_KEY: ${{ secrets.AIRTABLE_API_KEY }}
          AIRTABLE_BASE_ID: ${{ secrets.AIRTABLE_BASE_ID }}
          MINIFLUX_URL: ${{ secrets.MINIFLUX_URL }}
          MINIFLUX_API_KEY: ${{ secrets.MINIFLUX_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

#### Telegram 通知格式

```
✅ 融资抽取完成 (2026-02-21 14:00)

📥 新采集: 45 篇
🔍 含融资: 12 篇
📊 新增轮次: 8 条
⚠️ 待复核: 3 条
💰 LLM 成本: $0.42 (12,600 tokens)

前往复核 → [Airtable 链接]
```

#### 验收标准

- [ ] GitHub Actions 定时触发成功，日志正常
- [ ] 运行成功/失败都能收到 Telegram 通知
- [ ] Airtable Interface 复核视图可用：能看到 evidence + 修改字段
- [ ] 别名表生效：红杉中国/Sequoia China 等不会建成多条记录
- [ ] 连续 3 天无人干预运行正常

---

### Phase 3：多入口扩展 — Ingest API + Webhook + 手动输入（Week 2）

**目标**：除了 RSS，其他渠道也能往系统里灌数据。

#### 架构升级

```
Phase 1-2:  Miniflux ──→ Pipeline ──→ Airtable   （单入口）

Phase 3:
  Miniflux RSS ─────┐
  微信 Webhook ─────┤
  手动输入 ──────────┼──→ Ingest API (FastAPI) ──→ Sources 表 ──→ Pipeline
  会议纪要 ──────────┤                              (status=new)
  语音转写 ──────────┘
```

#### 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 3.1 | 写 Ingest API | `api/ingest.py` | FastAPI 应用，POST /ingest 统一入口 |
| 3.2 | 写 Webhook 适配器 | `adapters/webhook_article.py` | 处理公众号 webhook 推送的 HTML |
| 3.3 | 写会议纪要适配器 | `adapters/meeting_note.py` | 纯文本，加参会人信息，reliability=low |
| 3.4 | 写手动输入适配器 | `adapters/manual_input.py` | 最简单：直接存 raw_text |
| 3.5 | 改造 Pipeline 用 Adapter 注册表 | `pipeline/preprocess.py` | 按 source.type 自动选 Adapter |
| 3.6 | 加 reliability 字段到 FundingRounds | Airtable | 区分不同来源的可信度 |
| 3.7 | 部署 Ingest API | Cloudflare Workers / Railway / 本地 | 提供 HTTPS 端点 |

#### Ingest API 接口设计

```
POST /ingest
Content-Type: application/json

{
  "type": "rss_article | webhook_article | meeting_note | voice_transcript | manual",
  "title": "某AI公司完成B轮融资",
  "content": "正文内容或 HTML...",
  "metadata": {
    "source_channel": "wechat_webhook",
    "author": "量子位",
    "url": "https://mp.weixin.qq.com/s/...",
    "published_at": "2026-02-20",
    "speakers": ["张三", "李四"],      // 会议场景
    "language": "zh"
  }
}

Response 200:
{
  "source_id": "rec...",
  "status": "queued",
  "content_hash": "abc123...",
  "duplicate": false
}

Response 409 (重复):
{
  "source_id": "rec...(已存在的)",
  "status": "duplicate",
  "content_hash": "abc123..."
}
```

#### Adapter 注册表

```python
# adapters/__init__.py
from adapters.rss_article import RSSArticleAdapter
from adapters.webhook_article import WebhookArticleAdapter
from adapters.meeting_note import MeetingNoteAdapter
from adapters.manual_input import ManualInputAdapter

ADAPTER_REGISTRY: dict[str, SourceAdapter] = {
    "rss_article":      RSSArticleAdapter(),
    "webhook_article":  WebhookArticleAdapter(),
    "meeting_note":     MeetingNoteAdapter(),
    "manual":           ManualInputAdapter(),
    # Phase 4 加：
    # "voice_transcript": VoiceTranscriptAdapter(),
}
```

#### 文件结构（Phase 3 结束时新增）

```
ai-startup-tracker/
├── api/
│   ├── __init__.py              ← new
│   ├── ingest.py                ← new (FastAPI 应用)
│   └── auth.py                  ← new (API Key 校验)
├── adapters/
│   ├── base.py
│   ├── rss_article.py
│   ├── webhook_article.py       ← new
│   ├── meeting_note.py          ← new
│   └── manual_input.py          ← new
└── ...
```

#### 验收标准

- [ ] `curl -X POST /ingest` 能成功创建 Sources 记录
- [ ] 重复 content 返回 409，不会重复入库
- [ ] 手动通过 API 提交一篇会议纪要 → 走完抽取流程 → FundingRounds 有记录 + reliability=low
- [ ] 微信 Webhook 推送一篇文章 → 自动入库 + 抽取
- [ ] 不同 type 的 Source 用不同 Adapter 预处理，Pipeline 主流程代码无改动

---

### Phase 4：数据治理 — 冲突检测 + Claims + 训练数据（Week 3–4）

**目标**：处理多来源冲突，沉淀高质量训练数据，为后续优化做准备。

#### 任务清单

| # | 任务 | 文件/位置 | 说明 |
|---|------|-----------|------|
| 4.1 | 在 Airtable 新增 Claims 表 | Airtable | claim_id, type, subject, value, source, evidence_span, confidence, resolved_to |
| 4.2 | 写冲突检测逻辑 | `pipeline/conflict_detection.py` | 同公司+同轮次+近期 → 检查金额/投资方是否矛盾 |
| 4.3 | 冲突 → 自动创建 Claims + 标 disputed | 集成在写入流程 | FundingRound.verification_status = disputed |
| 4.4 | 复核修正自动沉淀 | `pipeline/training_sink.py` | Airtable Automation webhook → 记录 model_output vs human_corrected |
| 4.5 | 在 Airtable 新增 People 表 | Airtable | person_id, name, title, company(link), notes |
| 4.6 | 扩展 Prompt 抽取 Founder 信息 | `prompts/system_prompt.txt` | JSON Schema 加 founders 字段 |
| 4.7 | 写定期合并脚本 | `scripts/merge_entities.py` | 找疑似重复的 Companies/Orgs，列出候选 → 人工确认合并 |

#### Claims 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| claim_id | Auto Number | 主键 |
| claim_type | Single Select | `amount` / `valuation` / `stage` / `lead_investor` / `date` |
| subject_round | Link to FundingRounds | 关于哪条融资事件 |
| claimed_value | Single Line | 这条来源声称的值 |
| source | Link to Sources | 来自哪条来源 |
| evidence_span | Long Text | 原文片段 |
| confidence | Rating (1–5) | 置信度 |
| status | Single Select | `pending` / `accepted` / `rejected` |
| resolved_to | Single Line | 最终采用的值 |

#### 冲突检测规则

```
当新 FundingRound 写入时：
  1. 查 FundingRounds：同 company + 同 stage + date 在 ±90 天内 → 疑似同一轮
  2. 如果已有记录：
     a. 金额不同 → 创建 2 条 Claims (旧值+新值)，标 disputed
     b. 领投方不同 → 同上
     c. 信息完全一致 → 只更新 last_seen_at，不创建重复
  3. 进入复核队列
```

#### 训练数据格式（corrections.jsonl）

```jsonl
{"id": "corr_001", "source_id": "rec_xxx", "article_title": "...", "article_text": "...(截取 2000 字)...", "model_output": {"company_name_cn": "智元机器人", "stage": "B", "amount": {"value": 500000000, "currency": "CNY"}, "lead_investors": ["高瓴创投"], "confidence": 4}, "human_corrected": {"company_name_cn": "智元机器人", "stage": "B+", "amount": {"value": 600000000, "currency": "CNY"}, "lead_investors": ["高瓴创投", "经纬创投"], "confidence": 5}, "corrections": ["stage: B → B+", "amount: 5亿 → 6亿", "co_investor added: 经纬创投"], "corrected_at": "2026-03-05T10:30:00Z"}
```

#### 验收标准

- [ ] 同公司同轮次的两篇文章 → 自动检测为冲突 → Claims 表有记录 → FundingRound 标 disputed
- [ ] 人工在 Airtable 改了 FundingRound → corrections.jsonl 自动多了一行
- [ ] People 表能关联到 Companies
- [ ] merge_entities.py 能列出疑似重复的公司/机构候选

---

### Phase 5：语音 + ASR 入口（Week 5–6，按需）

**目标**：语音转文字直接进系统。

#### 任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 5.1 | 写语音转写适配器 | `adapters/voice_transcript.py` | 去 ASR 噪声（嗯啊/重复）、补标点、识别 speaker |
| 5.2 | 集成 ASR 服务 | `pipeline/asr.py` | 选项：Whisper API / FunASR(你已有) / 讯飞 |
| 5.3 | Ingest API 加语音上传端点 | `api/ingest.py` | POST /ingest/audio，接收音频 → ASR → 入 Sources |
| 5.4 | 语音场景专用 Prompt | `prompts/system_prompt_voice.txt` | 针对口语化表达调优抽取规则 |

#### 语音处理流程

```
音频文件 (mp3/wav/m4a)
    │
    ▼
POST /ingest/audio
    │
    ├─ ASR 转写（Whisper / FunASR）
    │
    ├─ VoiceTranscriptAdapter
    │   ├─ 去填充词（嗯、啊、那个）
    │   ├─ 合并重复句段
    │   └─ 补标点
    │
    ├─ 写入 Sources (type=voice_transcript, reliability=low)
    │
    └─ 进入标准 Pipeline
```

#### 验收标准

- [ ] 上传一段含融资信息的会议录音 → ASR → 抽取 → FundingRound 有记录
- [ ] reliability=low，needs_review=true

---

### Phase 6：规模化 + 数据分析（Month 2–3，按触发条件）

**目标**：当数据量增长到一定程度，做基础设施升级和数据分析。

#### 触发条件 → 任务

| 触发条件 | 任务 | 说明 |
|----------|------|------|
| Airtable 长文本字段频繁超限 | 正文存 Cloudflare R2 | Sources.raw_text_url 指向 R2 对象 |
| corrections.jsonl > 300 条 | 评估微调可行性 | 分析修正类型分布，决定微调什么 |
| FundingRounds > 500 条 | 加 Dashboard | 融资趋势（月度折线）、赛道分布（饼图）、热门公司（排行） |
| Airtable 行数 > 50K | 评估迁移 Supabase/PostgreSQL | 写 SupabaseBackend，Repository 模式保证零改动 |
| 日均 > 500 篇需处理 | 引入消息队列 | Redis Queue / Cloudflare Queue 替代 Sources 表轮询 |
| Pipeline 运行 > 30 分钟 | 并行处理 | asyncio 并发抽取，Airtable 批量写入 |

#### 数据库迁移路径（Repository 模式保障）

```python
# config.py — 换数据库只改这里
STORAGE_BACKEND = "airtable"   # 改为 "supabase" 即可

# main
from config import STORAGE_BACKEND
if STORAGE_BACKEND == "airtable":
    backend = AirtableBackend(api_key=..., base_id=...)
elif STORAGE_BACKEND == "supabase":
    backend = SupabaseBackend(url=..., key=...)

# Pipeline 代码完全不变
pipeline = Pipeline(storage=backend)
pipeline.run()
```

#### 微调决策树

```
corrections.jsonl 积累 >300 条？
  │
  ├─ No → 继续用 Prompt Engineering，优化 system_prompt
  │
  └─ Yes → 分析修正类型分布
              │
              ├─ 80% 修正是"轮次映射/金额格式" → 加规则，不微调
              │
              ├─ 80% 修正是"漏抽/错抽实体" → 微调小模型做 NER
              │
              └─ 修正类型分散 → 微调抽取器（输入:正文 → 输出:JSON）
                    │
                    ├─ 选模型：Qwen2.5-7B / Llama-3-8B（成本低）
                    ├─ 训练框架：LLaMA-Factory / OpenAI Fine-tuning API
                    └─ 评估：字段级 F1 + 事件级完整率
```

---

### 总时间线一览

```
Week 1
├── Day 1 AM     Phase 0: 脚手架 + Airtable 建表
├── Day 1 PM     Phase 1: 开始写 Pipeline
├── Day 2-3      Phase 1: 完成 MVP，测试 10 篇
├── Day 4-5      Phase 2: 复核 UI + 自动调度 + 监控
└── Day 6        Phase 2: 别名表 + 验证连续运行

Week 2
└── Phase 3: Ingest API + 多入口（Webhook/手动/会议纪要）

Week 3-4
└── Phase 4: 冲突检测 + Claims + 训练数据沉淀 + People 表

Week 5-6 (按需)
└── Phase 5: 语音 + ASR 入口

Month 2-3 (按触发条件)
└── Phase 6: 规模化（R2 存储 / Dashboard / 迁移 DB / 微调评估）
```

### 里程碑总结

| 里程碑 | 时间 | 你能做什么 |
|--------|------|-----------|
| **M1: 能跑** | Day 3 | 一条命令从 RSS 拉文章 → 抽取融资数据 → 写入 Airtable |
| **M2: 能用** | Day 6 | 无人值守运行，每天 10 分钟复核，Telegram 收通知 |
| **M3: 能扩** | Week 2 | Webhook/手动/会议纪要都能往里灌数据 |
| **M4: 能治** | Week 4 | 多来源冲突自动检测，训练数据自动沉淀 |
| **M5: 能听** | Week 6 | 语音录音直接扔进去 |
| **M6: 能长大** | Month 3 | 数据库可迁移，Pipeline 可并发，微调可评估 |

---

## 八、关键风险 & 应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 公众号正文抓不到（反爬/摘要） | 抽取源数据就是错的 | 保证 Miniflux 用全文 RSS；抓不到的标 `skipped` 不走抽取 |
| LLM 幻觉（编造投资方/金额） | 数据库污染 | evidence 必须是原文引用，复核时对照 |
| Airtable API 限速（5 req/s） | Pipeline 跑不动 | 批量写入，加 sleep；每次只处理增量 |
| 实体归一化不准（同公司多条记录） | 数据碎片化 | 别名表 + 定期人工合并 + 后期加向量相似度 |
| 金额表述模糊（"数亿元"） | 无法做精确统计 | 保留 raw_text，value 允许 null，做分析时只统计有确切数值的 |

---

## 九、项目文件结构（建议）

```
ai-startup-tracker/
├── README.md
├── requirements.txt
├── .env                        # AIRTABLE_API_KEY, ANTHROPIC_API_KEY, MINIFLUX_*
├── config.py                   # 常量、表名、枚举映射
├── pipeline/
│   ├── __init__.py
│   ├── fetch_articles.py       # Miniflux → Sources
│   ├── preprocess.py           # 清洗 + 关键词过滤
│   ├── extract_funding.py      # LLM 抽取
│   ├── normalize.py            # 实体归一化
│   ├── write_airtable.py       # 写 Airtable
│   └── notify.py               # 通知（Telegram/微信）
├── prompts/
│   ├── system_prompt.txt
│   └── extraction_schema.json
├── data/
│   ├── org_aliases.json        # 投资机构别名表
│   └── training_data/          # 复核修正数据
│       └── corrections.jsonl
├── run_pipeline.py             # 主入口
├── tests/
│   ├── test_preprocess.py
│   ├── test_extraction.py
│   └── sample_articles/        # 测试用文章
└── .github/
    └── workflows/
        └── extract.yml         # 定时 GitHub Action
```

---

## 十、技术选型补充

### 10.1 不用 LangChain

本项目是线性管道（文章 → LLM → JSON → DB），不需要 Agent/Chain 编排。LangChain 的代价（依赖膨胀、调试困难、版本不稳定）远大于收益。

**推荐**：`litellm`（轻量 LLM 代理，换模型改一行）+ `pydantic`（JSON 校验）+ `tenacity`（重试）。

### 10.2 多输入渠道扩展（Adapter 模式）

所有输入渠道统一走 `POST /ingest` API，写入 Sources 表（status=new）。不同输入类型用 Adapter 模式处理预处理差异：

- `RSSArticleAdapter`：清洗 HTML + 去公众号噪声，reliability=medium
- `WebhookArticleAdapter`：清洗 HTML，reliability=medium
- `MeetingNoteAdapter`：纯文本 + 加参会人信息，reliability=low
- `VoiceTranscriptAdapter`：去 ASR 噪声 + 补标点，reliability=low

新增渠道 = 写一个 Adapter（~20 行）+ 加一个路由（~5 行）。Pipeline 主流程完全不关心输入来自哪里。

### 10.3 存储层可迁移（Repository 模式）

Pipeline 通过 `StorageBackend` 抽象接口操作数据库，不直接调 Airtable API。迁移到 Supabase/PostgreSQL = 写一个新的 Backend 实现 + 改一行配置，Pipeline 代码零改动。

### 10.4 队列演进路径

| 阶段 | 队列方案 | 适用场景 |
|------|----------|----------|
| MVP | Sources 表 status=new 就是队列，cron 轮询 | 日均 <200 篇 |
| 中期 | FastAPI Ingest API + Sources 表队列 | 加 webhook/手动/语音入口 |
| 规模化 | Redis Queue / Cloudflare Queue + Worker | 日均 >1000 篇，需并发 |

---

## 十一、下一步行动

你现在只需做 **一个决定**：

> **先在 Airtable 建表，还是先写代码？**

- **选 A：先建表** → 我帮你生成 Airtable 的字段清单（含类型、枚举值、Link 关系），你按清单建好，然后我们写代码对接。
- **选 B：先写代码** → 我直接在 `ai-startup-tracker/` 目录开始写 Python Pipeline，代码里会创建表结构。

哪个？
