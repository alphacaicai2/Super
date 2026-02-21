"""
Fetch unread entries from Miniflux and create source records.
Uses config.MINIFLUX_URL and config.MINIFLUX_API_KEY.
"""
import hashlib
import httpx

import config
from storage.base import StorageBackend

# Truncate raw_text to avoid huge records
RAW_TEXT_MAX_LENGTH = 100_000


def fetch_and_create_sources(storage: StorageBackend) -> int:
    """
    Fetch unread Miniflux entries, create source records for each (no duplicate check in MVP).
    Returns the number of sources created.
    """
    base_url = (config.MINIFLUX_URL or "").rstrip("/")
    api_key = config.MINIFLUX_API_KEY or ""
    if not base_url or not api_key:
        return 0

    headers = {"X-Auth-Token": api_key}
    created = 0

    with httpx.Client(timeout=30.0) as client:
        # Get unread entry ids
        r = client.get(
            f"{base_url}/v1/entries",
            params={"status": "unread"},
            headers=headers,
        )
        r.raise_for_status()
        payload = r.json()
        entry_ids = [e["id"] for e in payload.get("entries", []) if isinstance(e.get("id"), int)]

        for entry_id in entry_ids:
            # Get full entry details
            r2 = client.get(f"{base_url}/v1/entries/{entry_id}", headers=headers)
            r2.raise_for_status()
            entry = r2.json()

            title = (entry.get("title") or "").strip()
            content = entry.get("content") or ""
            url = (entry.get("url") or "").strip()
            published_at = entry.get("published_at") or ""
            feed = entry.get("feed") or {}
            author = (feed.get("title") or "").strip()

            content_hash = hashlib.md5((title + content).encode()).hexdigest()
            raw_text = content[:RAW_TEXT_MAX_LENGTH] if len(content) > RAW_TEXT_MAX_LENGTH else content

            data = {
                "type": config.SOURCE_TYPE_RSS_ARTICLE,
                "title": title,
                "url": url,
                "author": author,
                "published_at": published_at,
                "source_channel": config.SOURCE_CHANNEL_MINIFLUX,
                "content_hash": content_hash,
                "has_funding_signal": False,
                "processing_status": config.PROCESSING_STATUS_NEW,
                "raw_text": raw_text,
            }
            storage.create_source(data)
            created += 1

    return created
