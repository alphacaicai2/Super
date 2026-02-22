"""
Preprocess sources: run type-specific adapter and optionally filter by funding signal.
筛选方式由 config.FUNDING_PREFILTER 决定：keyword / minimal / none（不预筛则全部送 LLM）。
"""
import config
from adapters.base import ProcessedContent
from adapters.rss_article import RSSArticleAdapter
from storage.base import StorageBackend

# 正文参与匹配的长度
PREFILTER_TEXT_LEN = 2000


def has_funding_signal(title: str, text: str, keywords: list[str]) -> bool:
    """Return True if (title + first N chars of text) contains any of keywords."""
    combined = (title or "") + " " + (text or "")[:PREFILTER_TEXT_LEN]
    return any(kw in combined for kw in keywords)


def preprocess_source(
    source_record: dict,
    storage: StorageBackend,
) -> ProcessedContent | None:
    """
    Run the appropriate adapter; if prefilter enabled and no funding signal, mark skipped and return None.
    """
    source_type = source_record.get("type")
    if source_type == config.SOURCE_TYPE_RSS_ARTICLE:
        adapter = RSSArticleAdapter()
    else:
        return None

    metadata = {k: v for k, v in source_record.items() if k != "raw_text"}
    processed = adapter.preprocess(source_record.get("raw_text", ""), metadata)

    if config.FUNDING_PREFILTER == "none":
        return processed

    keywords = (
        config.FUNDING_KEYWORDS_MINIMAL
        if config.FUNDING_PREFILTER == "minimal"
        else config.FUNDING_KEYWORDS
    )
    if not has_funding_signal(source_record.get("title", ""), processed.text, keywords):
        storage.update_source_status(source_record["id"], config.PROCESSING_STATUS_SKIPPED)
        return None
    return processed
