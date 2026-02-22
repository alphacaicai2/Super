"""
分层流水线：召回（标题粗筛）→ 正文精判 → 结构化抽取 → 人工复核。

- 召回：preprocess 用关键词/minimal/none 粗筛，尽量别漏。
- 正文精判：LLM 二分类「正文是否含可抽取的投融资/产品发布事实」，过滤标题党与无关文。
- 结构化抽取：仅对精判为 YES 的做 LLM 抽取并写 Airtable。
- 人工复核：needs_review 的条目在 Airtable 待复核视图处理。
"""
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import config
from pipeline import fetch_and_create_sources, preprocess_source
from pipeline.classify import body_worth_extracting
from pipeline.extract import extract_funding
from pipeline.notify import send_run_summary, send_telegram
from pipeline.write_airtable import write_extraction_result, should_review
from storage import AirtableBackend, StorageBackend

FETCH_GAP_ALERT_DAYS = 7  # 距上次拉取超过该天数时 Telegram 提醒


def get_storage() -> StorageBackend:
    if config.STORAGE_BACKEND == "airtable":
        return AirtableBackend()
    raise ValueError(f"Unknown STORAGE_BACKEND: {config.STORAGE_BACKEND}")


def main() -> None:
    storage = get_storage()
    stats = {
        "sources_created": 0,
        "sources_processed": 0,
        "skipped_no_signal": 0,
        "skipped_body_no": 0,
        "rounds_extracted": 0,
        "needs_review_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    # 1) 上次拉取时间；若距今回超过 7 天则 Telegram 提醒
    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%d")
    last_fetch_at = storage.get_last_fetch_at()
    if last_fetch_at:
        try:
            last_dt = datetime.strptime(last_fetch_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            gap_days = (now - last_dt).days
            if gap_days >= FETCH_GAP_ALERT_DAYS:
                send_telegram(
                    f"⚠️ 融资抽取 Pipeline：距上次拉取已超过 {gap_days} 天（上次 {last_fetch_at}），"
                    "请检查 GitHub Actions 或 Miniflux。"
                )
        except (ValueError, TypeError):
            pass

    # 2) 从 Miniflux 拉取「上次拉取之后」的新未读（按发布时间正序），写入 Sources
    try:
        n_created = fetch_and_create_sources(storage, last_fetch_at=last_fetch_at)
        stats["sources_created"] = n_created
        print(f"[OK] Miniflux: {n_created} new source(s) created.")
        storage.set_last_fetch_at(today_iso)
    except Exception as e:
        print(f"[WARN] Miniflux fetch failed: {e}")

    # 3) 取待处理来源
    pending = storage.get_pending_sources(limit=200)
    if not pending:
        print("[OK] No pending sources. Done.")
        send_run_summary(stats, success=True)
        return

    print(f"[OK] Processing {len(pending)} pending source(s).")

    for source in pending:
        source_id = source.get("id")
        if not source_id:
            continue
        title = source.get("title", "")
        published_at = source.get("published_at") or ""
        if hasattr(published_at, "isoformat"):
            published_at = published_at.isoformat()[:10]
        source_channel = source.get("source_channel", config.SOURCE_CHANNEL_MINIFLUX)

        # 4) 召回：预处理 + 标题粗筛（关键词/minimal/none）
        processed = preprocess_source(source, storage)
        if processed is None:
            stats["sources_processed"] = stats.get("sources_processed", 0) + 1
            stats["skipped_no_signal"] = stats.get("skipped_no_signal", 0) + 1
            continue
        stats["sources_processed"] = stats.get("sources_processed", 0) + 1

        # 5) 正文精判：LLM 判正文是否含可抽取事实，不含则跳过抽取
        if config.BODY_CLASSIFY:
            try:
                worth, classify_usage = body_worth_extracting(title, processed.text)
                stats["input_tokens"] = stats.get("input_tokens", 0) + classify_usage.get("input_tokens", 0)
                stats["output_tokens"] = stats.get("output_tokens", 0) + classify_usage.get("output_tokens", 0)
                if not worth:
                    storage.update_source_status(source_id, config.PROCESSING_STATUS_SKIPPED)
                    stats["skipped_body_no"] = stats.get("skipped_body_no", 0) + 1
                    continue
            except Exception as e:
                print(f"[WARN] Body classify failed for {source_id}: {e}, proceeding to extract.")

        # 6) 结构化抽取
        try:
            result, token_usage = extract_funding(
                processed.text,
                title=title,
                published_at=str(published_at),
                source_channel=source_channel,
            )
        except Exception as e:
            print(f"[ERR] Extract failed for source {source_id}: {e}")
            storage.update_source_status(source_id, config.PROCESSING_STATUS_NEEDS_REVIEW)
            storage.create_extraction_log({
                "source": [source_id],
                "model": config.LLM_MODEL,
                "input_tokens": 0,
                "output_tokens": 0,
                "status": config.LOG_STATUS_FAILED,
                "error_message": str(e)[:1000],
                "rounds_extracted": 0,
            })
            continue

        if not result.has_funding_info or not result.funding_rounds:
            storage.update_source_status(source_id, config.PROCESSING_STATUS_EXTRACTED)
            storage.create_extraction_log({
                "source": [source_id],
                "model": config.LLM_MODEL,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "status": config.LOG_STATUS_NO_FUNDING,
                "rounds_extracted": 0,
            })
            stats["input_tokens"] = stats.get("input_tokens", 0) + token_usage.get("input_tokens", 0)
            stats["output_tokens"] = stats.get("output_tokens", 0) + token_usage.get("output_tokens", 0)
            continue

        # 7) 写入 FundingRounds + 更新 Source 状态 + ExtractionLog
        try:
            write_extraction_result(
                storage,
                source_id=source_id,
                source_record=source,
                result=result,
                token_usage=token_usage,
            )
            stats["rounds_extracted"] = stats.get("rounds_extracted", 0) + len(result.funding_rounds)
            stats["input_tokens"] = stats.get("input_tokens", 0) + token_usage.get("input_tokens", 0)
            stats["output_tokens"] = stats.get("output_tokens", 0) + token_usage.get("output_tokens", 0)
            for r in result.funding_rounds:
                if should_review(r):
                    stats["needs_review_count"] = stats.get("needs_review_count", 0) + 1
            print(f"[OK] Source {source_id}: {len(result.funding_rounds)} round(s) written.")
        except Exception as e:
            print(f"[ERR] Write failed for source {source_id}: {e}")
            storage.update_source_status(source_id, config.PROCESSING_STATUS_NEEDS_REVIEW)
            storage.create_extraction_log({
                "source": [source_id],
                "model": config.LLM_MODEL,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "status": config.LOG_STATUS_FAILED,
                "error_message": str(e)[:1000],
                "rounds_extracted": len(result.funding_rounds),
            })

    print("[OK] Pipeline run finished.")
    send_run_summary(stats, success=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        send_telegram(f"❌ 融资抽取失败 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n{str(e)[:500]}")
        raise
