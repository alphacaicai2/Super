# Airtable 建表清单（Step-by-Step Checklist）

**推荐**：若你有 Personal Access Token（需勾选 scope `schema.bases:write`），可直接用脚本通过 API 建表：

```bash
cd ai-startup-tracker
# .env 中设置 AIRTABLE_API_KEY=（PAT）、AIRTABLE_BASE_ID=（Base ID，如 appXXX）
python scripts/create_airtable_tables.py
```

脚本会创建 5 张表及全部字段；若表已存在则跳过。以下为手动建表时的参考清单。

---

按顺序在 Airtable Base 中创建以下 5 张表，字段类型与选项需与下表一致。完成后可在每项前的 `[ ]` 打勾。

---

## 表 1：Sources（来源，统一入口）

| 步骤 | 字段名 | Airtable 字段类型 | 选项 / 说明 |
|------|--------|-------------------|-------------|
| [ ] | (保留默认) | — | 如需主键可添加 **Auto Number** 字段，命名为 `source_id` |
| [ ] | type | Single Select | 选项：`rss_article` \| `manual_article` \| `meeting_note` \| `memo` |
| [ ] | title | Single Line Text | — |
| [ ] | url | URL | — |
| [ ] | author | Single Line Text | — |
| [ ] | published_at | Date | 含时间可选 |
| [ ] | created_at | Created Time | 系统自动 |
| [ ] | source_channel | Single Select | 选项：`miniflux` \| `manual` \| `meeting` \| `wechat` |
| [ ] | content_hash | Single Line Text | MD5 去重用 |
| [ ] | has_funding_signal | Checkbox | — |
| [ ] | processing_status | Single Select | 选项：`new` \| `extracted` \| `needs_review` \| `done` \| `skipped` |
| [ ] | raw_text | Long Text | **MVP 必加**：正文内容，供 Pipeline 读取（超长可后续改存 raw_text_url） |
| [ ] | raw_text_url | URL | 正文存外部时的链接 |
| [ ] | tags | Multiple Select | 自由标签，可不预设选项 |

---

## 表 2：Companies（公司）

| 步骤 | 字段名 | Airtable 字段类型 | 选项 / 说明 |
|------|--------|-------------------|-------------|
| [ ] | (保留默认或添加) | — | 如需主键可添加 **Auto Number**，命名为 `company_id` |
| [ ] | name_cn | Single Line Text | 中文名 |
| [ ] | name_en | Single Line Text | 英文名 |
| [ ] | aliases | Long Text | 其他名称，逗号分隔 |
| [ ] | sector | Multiple Select | 选项：`LLM` \| `机器人` \| `自动驾驶` \| `AI医疗` \| `AI芯片`（可后续补充） |
| [ ] | description | Long Text | 一句话描述 |
| [ ] | website | URL | — |
| [ ] | status | Single Select | 选项：`active` \| `acquired` \| `closed` |
| [ ] | founded_year | Number | 整数，无小数 |
| [ ] | funding_rounds | Link to another record | 链接到表 **FundingRounds**（反向关联，在 FundingRounds 侧配置 Link to Companies） |
| [ ] | first_seen_at | Date | — |
| [ ] | last_seen_at | Date | — |
| [ ] | notes | Long Text | — |

---

## 表 3：Orgs（投资机构）

| 步骤 | 字段名 | Airtable 字段类型 | 选项 / 说明 |
|------|--------|-------------------|-------------|
| [ ] | (保留默认或添加) | — | 如需主键可添加 **Auto Number**，命名为 `org_id` |
| [ ] | name | Single Line Text | 机构名 |
| [ ] | aliases | Long Text | 别名，逗号分隔 |
| [ ] | type | Single Select | 选项：`VC` \| `PE` \| `CVC` \| `Government` \| `Angel` \| `Accelerator` |
| [ ] | website | URL | — |
| [ ] | funding_rounds_lead | Link to another record | 链接到表 **FundingRounds**（领投） |
| [ ] | funding_rounds_participated | Link to another record | 链接到表 **FundingRounds**（参投） |
| [ ] | notes | Long Text | — |

---

## 表 4：FundingRounds（融资轮次）⭐ 核心表

| 步骤 | 字段名 | Airtable 字段类型 | 选项 / 说明 |
|------|--------|-------------------|-------------|
| [ ] | (保留默认或添加) | — | 如需主键可添加 **Auto Number**，命名为 `round_id` |
| [ ] | company | Link to another record | 链接到表 **Companies** |
| [ ] | stage | Single Select | 选项：`Angel` \| `Pre-Seed` \| `Seed` \| `Pre-A` \| `A` \| `A+` \| `B` \| `C` \| `D` \| `E+` \| `Pre-IPO` \| `IPO` \| `Strategic` \| `Acquisition` \| `Undisclosed` |
| [ ] | date | Date | — |
| [ ] | amount_value | Number | 金额数值 |
| [ ] | amount_currency | Single Select | 选项：`CNY` \| `USD` \| `EUR` \| `HKD` |
| [ ] | amount_raw | Single Line Text | 原文表述（如「数亿元」） |
| [ ] | valuation_value | Number | 估值数值（若有） |
| [ ] | valuation_currency | Single Select | 选项：`CNY` \| `USD` \| `EUR` \| `HKD` |
| [ ] | valuation_raw | Single Line Text | 原文表述 |
| [ ] | lead_investors | Link to another record | 链接到表 **Orgs**（允许链接多条） |
| [ ] | co_investors | Link to another record | 链接到表 **Orgs**（允许链接多条） |
| [ ] | source_primary | Link to another record | 链接到表 **Sources** |
| [ ] | evidence_text | Long Text | 原文证据片段 |
| [ ] | confidence | Rating | 1–5 星 |
| [ ] | verification_status | Single Select | 选项：`unverified` \| `verified` \| `disputed` |
| [ ] | needs_review | Checkbox | — |
| [ ] | review_notes | Long Text | — |
| [ ] | extracted_at | Date | 抽取时间 |
| [ ] | model_version | Single Line Text | 模型名+版本 |

---

## 表 5：ExtractionLog（抽取日志，辅助表）

| 步骤 | 字段名 | Airtable 字段类型 | 选项 / 说明 |
|------|--------|-------------------|-------------|
| [ ] | (保留默认或添加) | — | 如需主键可添加 **Auto Number**，命名为 `log_id` |
| [ ] | source | Link to another record | 链接到表 **Sources** |
| [ ] | run_at | Created Time | 运行时间（可用 Created Time） |
| [ ] | model | Single Line Text | 模型名+版本 |
| [ ] | input_tokens | Number | 整数 |
| [ ] | output_tokens | Number | 整数 |
| [ ] | status | Single Select | 选项：`success` \| `failed` \| `partial` \| `no_funding` |
| [ ] | error_message | Long Text | 失败原因 |
| [ ] | raw_output | Long Text | 模型原始输出（JSON） |
| [ ] | rounds_extracted | Number | 抽出的融资条数 |

---

## Link 关系（链接关系）

| 从表 | 字段 | 指向表 |
|------|------|--------|
| **Companies** | funding_rounds | FundingRounds（反向：由 FundingRounds 的 company 字段创建双向链接） |
| **Orgs** | funding_rounds_lead | FundingRounds |
| **Orgs** | funding_rounds_participated | FundingRounds |
| **FundingRounds** | company | Companies |
| **FundingRounds** | lead_investors | Orgs |
| **FundingRounds** | co_investors | Orgs |
| **FundingRounds** | source_primary | Sources |
| **ExtractionLog** | source | Sources |

**建议建表顺序**：先建 **Sources**、**Companies**、**Orgs**，再建 **FundingRounds**（并在此表添加指向 Companies、Orgs、Sources 的 Link 字段），最后建 **ExtractionLog**（Link to Sources）。这样创建 Link 时目标表已存在。

---

*依据：`docs/plans/2026-02-21-ai-startup-extraction-plan.md` 第三节「数据模型（Airtable 表结构）」3.1 MVP 表结构。*
