"""
Fetch unread entries from Miniflux and create source records.
Uses config.MINIFLUX_URL and config.MINIFLUX_API_KEY.
"""
import hashlib
from datetime import datetime
import httpx

import config
from storage.base import StorageBackend

# Truncate raw_text to avoid huge records
RAW_TEXT_MAX_LENGTH = 100_000


def _published_at_to_iso(value) -> str | None:
    """Normalize Miniflux published_at to ISO date string for Airtable (YYYY-MM-DD)."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        try:
            dt = datetime.utcfromtimestamp(int(value))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return None
    if isinstance(value, str) and value.strip():
        # Already ISO-like (e.g. 2025-02-21 or 2025-02-21T12:00:00Z)
        return value.strip()[:10]
    return None


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
            published_at = _published_at_to_iso(entry.get("published_at"))
            feed = entry.get("feed") or {}
            author = (feed.get("title") or "").strip()

            content_hash = hashlib.md5((title + content).encode()).hexdigest()
            raw_text = content[:RAW_TEXT_MAX_LENGTH] if len(content) > RAW_TEXT_MAX_LENGTH else content

            data = {
                "type": config.SOURCE_TYPE_RSS_ARTICLE,
                "title": title,
                "url": url,
                "author": author,
                "source_channel": config.SOURCE_CHANNEL_MINIFLUX,
                "content_hash": content_hash,
                "has_funding_signal": False,
                "processing_status": config.PROCESSING_STATUS_NEW,
                "raw_text": raw_text,
            }
            if published_at is not None:
                data["published_at"] = published_at
            storage.create_source(data)
            created += 1

    return created
