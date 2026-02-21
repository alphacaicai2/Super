# Airtable 复核视图与统计 Dashboard 设置说明

在 Airtable 网页中按以下步骤搭建「待复核」视图和简单统计，便于每日 10 分钟复核。

---

## 〇、待复核视图（表格视图，约 30 秒）

**在 FundingRounds 表里建一个「待复核」视图，只显示需要人工复核的记录。**

1. 打开你的 Base：浏览器访问 `https://airtable.com/<你的 BASE_ID>`（BASE_ID 即 `.env` 里的 `AIRTABLE_BASE_ID`）。
2. 左侧点击表 **FundingRounds**。
3. 左上角当前视图名称旁点 **+** 或 **Add view**，新建视图。
4. 视图名称填：**待复核**（或 🔍 待复核）。
5. 在视图设置里点 **Filter**（筛选）→ **Add condition**：
   - 字段选 **needs_review**
   - 条件选 **Is checked**（已勾选）。
6. 可选：再加一条筛选 **verification_status** → **is** → **unverified**。
7. 可选：在 **Fields** 里勾选要显示的列（建议保留：round_label、company、stage、amount_value、amount_currency、evidence_text、source_primary、confidence、verification_status、review_notes）。
8. 保存。之后有抽到融资且标为 needs_review 时，在这个视图里逐条改完并把 **verification_status** 改为 **verified**。

---

## 一、待复核 Interface（可选，需 Interface 设计器）

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

---

## 四、ExtractionLog 为空

**ExtractionLog** 只有在「某篇来源过了预处理、调用了 LLM 抽取」时才会写入一条记录（成功/无融资/失败）。若当前为空白，说明本 run 里处理的 50 篇都在**预处理阶段**因未命中融资关键词被标为 skipped，没有进入 LLM 抽取，因此没有写 ExtractionLog。等有文章命中关键词并走完抽取后，这里就会出现对应日志。
