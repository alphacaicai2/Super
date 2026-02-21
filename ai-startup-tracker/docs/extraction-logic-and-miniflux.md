# 抽取逻辑与 Miniflux 使用说明

## 〇、部署与触发

| 项目 | 说明 |
|------|------|
| **部署位置** | **GitHub Actions**（仓库 `alphacaicai2/Super` → Actions → workflow「Extract pipeline」）。跑在 GitHub 提供的 `ubuntu-latest` runner 上，无单独服务器。 |
| **自动触发** | **是**。按 cron 每 **6 小时** 跑一次：UTC 0:00、6:00、12:00、18:00（对应北京时间 8:00、14:00、20:00、次日 2:00）。 |
| **手动触发** | 在 Actions 页点「Extract pipeline」→「Run workflow」即可。 |
| **拉取范围** | 每次 run 只拉取**上次拉取之后**的新未读（Miniflux API `published_after` + 存于 Airtable 表 PipelineState 的 `last_fetch_at`）。首次 run 无记录时拉取全部未读。 |
| **拉取顺序** | **按发布时间正序**（`order=published_at`, `direction=asc`），即从旧到新。 |
| **是否顺序处理** | **是**。从 Airtable 取 `processing_status=new` 的 50 条，按返回顺序逐条预处理 → LLM 抽取 → 写入 FundingRounds。 |
| **超过 7 天未拉取** | 若本次 run 距上次拉取日期 ≥ 7 天，会发一条 Telegram 提醒：「距上次拉取已超过 N 天，请检查 GitHub Actions 或 Miniflux」。 |

---

## 一、Pipeline 抽取逻辑（为何会看到 2015 年等旧新闻）

1. **拉取**：每次 run 向 Miniflux 请求 **当前所有未读条目**（`GET /v1/entries?status=unread`），不按时间筛选。
2. **写入 Airtable**：为每条未读条目在 **Sources** 表创建一条记录（`published_at` 为文章原始发布日期，可能很早）。
3. **待处理**：从 Airtable 取 `processing_status=new` 的 Sources，每次最多 50 条，**不按 published_at 排序**，顺序由 Airtable 返回决定。
4. **预处理**：用 `FUNDING_KEYWORDS` 在标题+正文前 500 字里做关键词匹配；无命中则标为 `skipped`，不进入 LLM。
5. **LLM 抽取**：有命中则调用 LLM 从正文抽取融资轮次；结果写入 **FundingRounds**，并写 **ExtractionLog**。
6. **待复核**：若某条轮次满足「低置信度 / 缺金额 / 无领投 / Undisclosed」等条件，会勾选 `needs_review`，在「待复核」视图中显示。

因此，若 Miniflux 里积压了大量**很早以前未读**的文章（例如 2015 年），它们会被拉进 Airtable 并被处理，所以你会在 Airtable / 抽取结果里看到很多旧新闻。

**处理方式**：在 `.env` 中设置 **PUBLISHED_AFTER_DAYS**（例如 `365`），则只拉取「发表日期在最近 N 天内」的未读文章并写入 Sources，更早的未读文章不会进入本 pipeline，**Miniflux 内数据不被修改**。

---

## 二、Miniflux：只读，不修改

**PipelineState 表**：Airtable 中需有表 **PipelineState**（单行即可），字段 `last_fetch_at`（日期），用于存上次拉取日期。若尚未建表，在 `ai-startup-tracker` 目录执行一次 `python scripts/create_airtable_tables.py` 会自动创建。

本 pipeline 对 Miniflux **仅做只读请求**，方便同一 Miniflux 实例给其他程序使用：

- **会做**：`GET /v1/entries?status=unread`、`GET /v1/entries/{id}`，读取标题、正文、发表日期等。
- **不会做**：不标记已读、不删除、不修改任何 feed 或条目。

所有「状态变更」只发生在 **Airtable**（Sources 的 `processing_status`、FundingRounds、ExtractionLog 等），Miniflux 后端数据保持不变。
