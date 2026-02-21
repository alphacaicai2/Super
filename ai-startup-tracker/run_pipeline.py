"""
Phase 1 主入口：Miniflux 拉取 → 预处理 → LLM 抽取 → 归一化 → 写入 Airtable。
运行前请：cp .env.example .env 并填写 AIRTABLE_* / MINIFLUX_* / ANTHROPIC_API_KEY。
"""
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import config
from pipeline import fetch_and_create_sources, preprocess_source
from pipeline.extract import extract_funding
from pipeline.write_airtable import write_extraction_result
from storage import AirtableBackend, StorageBackend


def get_storage() -> StorageBackend:
    if config.STORAGE_BACKEND == "airtable":
        return AirtableBackend()
    raise ValueError(f"Unknown STORAGE_BACKEND: {config.STORAGE_BACKEND}")


def main() -> None:
    storage = get_storage()

    # 1) 从 Miniflux 拉取新文章并写入 Sources（status=new）
    try:
        n_created = fetch_and_create_sources(storage)
        print(f"[OK] Miniflux: {n_created} new source(s) created.")
    except Exception as e:
        print(f"[WARN] Miniflux fetch failed: {e}")

    # 2) 取待处理来源
    pending = storage.get_pending_sources(limit=50)
    if not pending:
        print("[OK] No pending sources. Done.")
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

        # 3) 预处理：清洗 + 融资关键词过滤；无信号则标 skipped
        processed = preprocess_source(source, storage)
        if processed is None:
            continue

        # 4) LLM 抽取
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
                "run_at": datetime.now().isoformat(),
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
                "run_at": datetime.now().isoformat(),
                "model": config.LLM_MODEL,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "status": config.LOG_STATUS_NO_FUNDING,
                "rounds_extracted": 0,
            })
            continue

        # 5) 写入 FundingRounds + 更新 Source 状态 + ExtractionLog
        try:
            write_extraction_result(
                storage,
                source_id=source_id,
                source_record=source,
                result=result,
                token_usage=token_usage,
            )
            print(f"[OK] Source {source_id}: {len(result.funding_rounds)} round(s) written.")
        except Exception as e:
            print(f"[ERR] Write failed for source {source_id}: {e}")
            storage.update_source_status(source_id, config.PROCESSING_STATUS_NEEDS_REVIEW)
            storage.create_extraction_log({
                "source": [source_id],
                "run_at": datetime.now().isoformat(),
                "model": config.LLM_MODEL,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "status": config.LOG_STATUS_FAILED,
                "error_message": str(e)[:1000],
                "rounds_extracted": len(result.funding_rounds),
            })

    print("[OK] Pipeline run finished.")


if __name__ == "__main__":
    main()
