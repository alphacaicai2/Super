"""
Preprocess sources: run type-specific adapter and filter by funding signal.
"""
import config
from adapters.base import ProcessedContent
from adapters.rss_article import RSSArticleAdapter
from storage.base import StorageBackend


def has_funding_signal(title: str, text: str) -> bool:
    """Return True if (title + first 500 chars of text) contains any config.FUNDING_KEYWORDS."""
    combined = (title or "") + " " + (text or "")[:500]
    return any(kw in combined for kw in config.FUNDING_KEYWORDS)


def preprocess_source(
    source_record: dict,
    storage: StorageBackend,
) -> ProcessedContent | None:
    """
    Run the appropriate adapter for source type; if no funding signal, mark skipped and return None.
    """
    source_type = source_record.get("type")
    if source_type == config.SOURCE_TYPE_RSS_ARTICLE:
        adapter = RSSArticleAdapter()
    else:
        return None

    metadata = {k: v for k, v in source_record.items() if k != "raw_text"}
    processed = adapter.preprocess(source_record.get("raw_text", ""), metadata)

    if not has_funding_signal(source_record.get("title", ""), processed.text):
        storage.update_source_status(source_record["id"], config.PROCESSING_STATUS_SKIPPED)
        return None
    return processed
