"""
Telegram 通知：运行摘要与发送逻辑。
需在加载 config 前加载 .env，故本模块顶部先 load_dotenv 再 import config。
"""
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()
import config  # noqa: E402


def send_telegram(text: str) -> bool:
    """发送一条文本到配置的 Telegram 群/用户。未配置 token/chat_id 时不发送并返回 False。"""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[notify] Telegram skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(
            url,
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
            timeout=10.0,
        )
        if not r.is_success:
            print(f"[notify] Telegram send failed: HTTP {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[notify] Telegram send error: {e}")
        return False


def send_run_summary(
    stats: dict,
    success: bool = True,
    airtable_url: str = "",
) -> None:
    """
    发送一次运行摘要到 Telegram（中文）。
    stats 可含: sources_created, sources_processed, rounds_extracted,
    needs_review_count, input_tokens, output_tokens；缺失则按 0 处理。
    若未配置 TELEGRAM_* 则不发送。
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[notify] Run summary skipped: Telegram not configured")
        return
    created = stats.get("sources_created", 0)
    processed = stats.get("sources_processed", 0)
    rounds = stats.get("rounds_extracted", 0)
    needs_review = stats.get("needs_review_count", 0)
    inp = stats.get("input_tokens", 0)
    out = stats.get("output_tokens", 0)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if success:
        lines = [f"✅ 融资抽取完成 ({ts})"]
    else:
        lines = [f"❌ 融资抽取失败 ({ts})"]
    lines.append(f"📥 新采集: {created} 篇")
    lines.append(f"🔍 处理: {processed} 篇")
    lines.append(f"📊 新增轮次: {rounds} 条")
    lines.append(f"⚠️ 待复核: {needs_review} 条")
    if inp or out:
        lines.append(f"💰 Tokens: input {inp} output {out}")
    if airtable_url:
        lines.append(f"前往复核 → {airtable_url}")
    send_telegram("\n".join(lines))
