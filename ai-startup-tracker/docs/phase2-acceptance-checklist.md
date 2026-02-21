# Phase 2 验收清单

按顺序完成以下项并打勾，即完成 Phase 2 验收。

---

## 一、GitHub Secrets 配置

1. 打开仓库 **Settings → Secrets and variables → Actions**。
2. 新增以下 **Repository secrets**（若用默认 Claude，必填前 7 个）：

| Secret 名称 | 说明 | 必填 |
|-------------|------|------|
| `AIRTABLE_API_KEY` | Airtable Personal Access Token（或 PAT） | ✅ |
| `AIRTABLE_BASE_ID` | Base ID（如 `app9gKooHtEXRmLDo`，仅 app 这一段） | ✅ |
| `MINIFLUX_URL` | Miniflux 地址，如 `https://miniflux.xxx.com` | ✅ |
| `MINIFLUX_API_KEY` | Miniflux API Key | ✅ |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（@BotFather 创建） | ✅ |
| `TELEGRAM_CHAT_ID` | 接收通知的 Chat ID（群或私聊） | ✅ |
| `ANTHROPIC_API_KEY` | 使用 Claude 时必填 | 用 Claude 时 ✅ |
| `OPENAI_API_KEY` | 使用 OpenAI 时必填（并在 workflow 中传 `LLM_MODEL`） | 用 OpenAI 时 ✅ |

**若使用 OpenAI 而非 Claude**：在 `.github/workflows/extract.yml` 的 `Run pipeline` 步骤的 `env` 中增加一行：

```yaml
LLM_MODEL: openai/gpt-4o
```

并确保已配置 `OPENAI_API_KEY` secret，可不配 `ANTHROPIC_API_KEY`。

- [ ] 已配置上述 Secrets

---

## 二、手动触发一次 GitHub Actions

1. 打开仓库 **Actions** 页，左侧选择 **Extract pipeline**。
2. 点击 **Run workflow** → **Run workflow**（分支选 `main`）。
3. 等待约 1～3 分钟，查看 run 是否 **绿色成功**；若有报错，点进 run 看 **Run pipeline** 步骤的日志。

- [ ] 手动触发成功，日志无报错

---

## 三、Telegram 通知

1. 若未配置 Bot：在 Telegram 找 @BotFather，发送 `/newbot`，按提示创建 Bot，获得 **Bot Token**。
2. 获得 **Chat ID**：给 Bot 发一条消息后，访问  
   `https://api.telegram.org/bot<你的Token>/getUpdates`  
   在返回 JSON 里找到 `"chat":{"id": 123456789}`，即为 Chat ID。
3. 将 `TELEGRAM_BOT_TOKEN` 与 `TELEGRAM_CHAT_ID` 填入 GitHub Secrets（见上一节）。
4. 再次手动跑一次 **Extract pipeline**，检查是否收到一条中文运行摘要（✅ 融资抽取完成 / ❌ 融资抽取失败，及新采集/处理/轮次/待复核等）。

- [ ] 运行成功后收到 Telegram 摘要
- [ ] （可选）故意制造失败（如暂时删掉 AIRTABLE_API_KEY）再跑一次，确认能收到「❌ 融资抽取失败」通知

---

## 四、Airtable 复核视图

1. 打开你的 Airtable Base（如 VibeX）。
2. 按 **docs/airtable-review-interface.md** 操作：
   - 若有 **Interface 设计器**：新建 Interface「🔍 待复核」，数据源选 **FundingRounds**，筛选 `needs_review` = 勾选，左侧展示 evidence/来源，右侧可编辑 company/stage/金额/投资方/verification_status/review_notes。
   - 若无 Interface：在 **FundingRounds** 表新建视图「待复核」，筛选 `needs_review` = 勾选，列中包含 `evidence_text`、`company`、`stage`、`lead_investors`、`verification_status`、`review_notes` 等。
3. 若有已标为 needs_review 的记录，打开该视图/Interface，能看见原文证据并修改字段、将 `verification_status` 改为 verified。

- [ ] 复核视图/Interface 已搭建，能查看 evidence 并修改字段

---

## 五、机构别名表（红杉/Sequoia 等不重复）

1. **data/org_aliases.json** 已包含约 59 家机构及中英文别名。
2. 验收方式：跑 Pipeline 后，在 Airtable **Orgs** 表中查看——同一机构不同写法（如「红杉中国」「Sequoia China」）应只对应一条记录，不应出现多条同名或重复机构。

- [ ] （有数据后）Orgs 中无因别名未归一而重复的机构

---

## 六、定时与连续运行（可选）

1. 定时：Workflow 已设 `cron: '0 */6 * * *'`，即每 6 小时跑一次；可在 **Actions** 的 **Extract pipeline** 的 **Runs** 中观察是否按计划执行。
2. 若希望「连续 3 天无人干预运行正常」：保持 Miniflux 有订阅源、Airtable 与 Secrets 不变，3 天后查看 Actions 历史与 Telegram 记录是否无异常。

- [ ] （可选）确认定时 run 按 6 小时执行
- [ ] （可选）连续 3 天无报错、Telegram 摘要正常

---

## 验收结论

以上 **一、二、三、四** 全部打勾即视为 **Phase 2 验收通过**。第五、六项为可选或后续观察。

通过后即可进入 **Phase 3（多入口扩展：Ingest API + Webhook + 手动/会议纪要）**。
