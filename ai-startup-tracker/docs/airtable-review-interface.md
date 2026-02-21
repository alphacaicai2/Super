# Airtable 复核视图与统计 Dashboard 设置说明

在 Airtable 网页中按以下步骤搭建「待复核」视图和简单统计，便于每日 10 分钟复核。

---

## 一、待复核 Interface（推荐）

1. 打开你的 Base（如 VibeX）→ 点击左上 **Extensions** 或 **Interface**（若已启用 Interface 设计器）。
2. 新建 Interface：名称 `🔍 待复核`。
3. 添加 **Record picker** 或 **Table** 数据源：选择表 **FundingRounds**。
4. 设置筛选条件：
   - `needs_review` = 勾选（true）
   - 可选：`verification_status` = `unverified`
5. 布局建议：
   - **左侧**：显示 `evidence_text`（原文证据）、`source_primary` 展开显示来源标题与 URL、`confidence`、`model_version`。
   - **右侧**：可编辑字段 `company`、`stage`、`amount_value`、`amount_currency`、`lead_investors`、`co_investors`、`verification_status`（改为 verified）、`review_notes`。
6. 保存。之后每天打开此 Interface，逐条修正并标记 `verification_status` 为 verified。

---

## 二、统计 Dashboard（可选）

在同一 Base 中可新建一个 **Dashboard** 或使用 **Interface**：

- 使用 **Chart** 或 **Summary** 组件：
  - 数据源：FundingRounds。
  - 按 `stage` 分组统计数量（各轮次分布）。
  - 筛选「本周创建」的 `extracted_at` 或 `Created time`。
- 使用 **Record count**：表 FundingRounds 中 `needs_review` = true 的记录数，即「待复核数」。

若 Base 未开通 Interface 设计器，可直接在 **FundingRounds** 表中新建视图「待复核」，筛选 `needs_review` = 勾选，按需排序列出 evidence、company、stage 等列，在表格中直接编辑复核。

---

## 三、Airtable 链接（用于 Telegram 通知）

在 Pipeline 或 notify 中使用的「前往复核」链接格式：

```
https://airtable.com/appXXXXXXXXXXXXXX/xxxxxxxxxxxxx
```

其中 `appXXX` 为 Base ID，后面一段为 Interface 或表视图的 ID（可在浏览器地址栏复制）。若只做表视图，链接到 FundingRounds 表并带筛选参数即可。
