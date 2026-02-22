# 规划 vs 当前实现对照

> 规划文件：`docs/plans/2026-02-21-ai-startup-extraction-plan.md`

---

## 结论一句话

**Phase 0、Phase 1、Phase 2 已按规划落地，并在「过滤→抽取」之间多做了「正文精判」一层（召回尽量别漏、抽取尽量准），与后续确定的策略一致。Phase 3–6 尚未做。**

---

## 分阶段对照

| 阶段 | 规划内容 | 当前状态 | 说明 |
|------|----------|----------|------|
| **Phase 0** | 脚手架、5 张 Airtable 表、storage/adapters/config、prompts | ✅ 完成 | 多了一张 **PipelineState**（存 last_fetch_at 做增量拉取） |
| **Phase 1** | Miniflux 拉取 → 预处理(清洗+关键词过滤) → LLM 抽取 → 归一化 → 写入、ExtractionLog | ✅ 完成并增强 | 见下「Phase 1 增强」 |
| **Phase 2** | 复核 Interface、GitHub Actions 每 6h、Telegram 通知、org_aliases | ✅ 完成 | 摘要里多了「召回跳过 / 正文精判跳过」统计；7 天未拉取会 Telegram 提醒 |
| **Phase 3** | Ingest API、Webhook/手动/会议纪要适配器、Adapter 注册表 | ❌ 未做 | 仍只有 RSS(Miniflux) 单入口 |
| **Phase 4** | Claims 表、冲突检测、训练数据沉淀、People 表 | ❌ 未做 | — |
| **Phase 5** | 语音转写、ASR 入口 | ❌ 未做 | — |
| **Phase 6** | 规模化（R2 存正文、Dashboard、迁移 DB、微调评估） | ❌ 未做 | — |

---

## Phase 1 与规划的差异（均为增强）

| 规划 | 当前实现 | 是否一致 |
|------|----------|----------|
| ③ 过滤：标题+正文**前 500 字**关键词 | 召回：标题+正文**前 2000 字**，且支持 **keyword / minimal / none** 三种模式 | 一致（范围更大、选项更多） |
| ④ 直接 LLM 抽取 | 中间增加 **正文精判**（LLM 二分类 YES/NO），再抽取 | **增强**：规划里是「过滤→抽取」两步，现在是「召回→精判→抽取」三层，与后来定的「标题粗筛+正文精判+结构化抽取+人工复核」一致 |
| 采集：每次拉 unread 全部 | 采集：**增量**（published_after + last_fetch_at），首次 run 只拉最近 365 天；单次处理 200 条 | 增强（防陈年未读、可控量） |
| 无「距上次拉取过久」告警 | 距上次拉取 **≥7 天** 发 Telegram 提醒 | 增强 |

---

## 与规划文档完全一致的部分

- **技术栈**：Python、litellm、Airtable、Miniflux、GitHub Actions、Telegram
- **5 张主表**：Sources、Companies、Orgs、FundingRounds、ExtractionLog（字段与规划一致，Airtable 用 PAT 建表）
- **Pipeline 主流程**：采集 → 预处理(清洗) → 过滤(召回) → 抽取 → 归一化 → 写入
- **evidence + confidence**：FundingRounds 有 evidence_text、confidence；低置信度/缺金额/无领投/Undisclosed → needs_review
- **人工复核**：待复核视图（筛选 needs_review）、Airtable 内改 verification_status
- **实体归一化**：精确匹配 + 别名表（org_aliases.json），未匹配则新建
- **错误与重试**：extract 重试、ExtractionLog 记失败
- **不微调、先跑通**：未做微调，通用模型 + 分层流水线

---

## 尚未实现的规划内容（Phase 3–6）

- **Phase 3**：Ingest API（POST /ingest）、webhook_article / meeting_note / manual 适配器、按 source.type 选 Adapter
- **Phase 4**：Claims 表、同公司同轮次冲突检测、复核修正自动写 corrections.jsonl、People 表、merge_entities 脚本
- **Phase 5**：语音转写适配器、ASR、POST /ingest/audio
- **Phase 6**：正文存 R2、corrections 达量后评估微调、Dashboard、Airtable 超 50K 行迁 Supabase、队列与并行

---

## 总结

| 问题 | 答案 |
|------|------|
| 和最早规划还一致吗？ | **一致**。Phase 0–2 按规划做完，且召回/精判/抽取/复核分层比规划更细（多了一层正文精判），其余未做的仍在规划里（Phase 3–6）。 |
| 主要「多出来」的？ | ① 正文精判层（LLM YES/NO）；② 增量拉取 + 首次 365 天 + 7 天告警；③ PipelineState 表；④ FUNDING_PREFILTER 三种模式、正文前 2000 字、产品类关键词。 |
| 规划里写了但还没做的？ | Phase 3（多入口/Ingest API）、Phase 4（冲突与训练数据）、Phase 5（语音）、Phase 6（规模化）。 |
