"""
Fetch unread entries from Miniflux and create source records.

重要：本模块仅对 Miniflux 做只读请求（GET），不标记已读、不修改或删除任何数据，
以便同一 Miniflux 实例供其他程序使用。
"""
import hashlib
from datetime import datetime, timedelta, timezone
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


def _is_after_cutoff(published_at_iso: str | None) -> bool:
    """True if published_at is within PUBLISHED_AFTER_DAYS (or no cutoff set)."""
    if not published_at_iso or config.PUBLISHED_AFTER_DAYS <= 0:
        return True
    try:
        pub_date = datetime.strptime(published_at_iso[:10], "%Y-%m-%d").date()
        cutoff = (datetime.now() - timedelta(days=config.PUBLISHED_AFTER_DAYS)).date()
        return pub_date >= cutoff
    except (ValueError, TypeError):
        return True


def _iso_date_to_unix_timestamp(iso_date: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp (start of day UTC)."""
    try:
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return 0


def fetch_and_create_sources(
    storage: StorageBackend,
    last_fetch_at: str | None = None,
) -> int:
    """
    Fetch unread Miniflux entries (GET only; no writes to Miniflux) published after last_fetch_at,
    in chronological order (published_at asc), and create source records.
    If last_fetch_at is None (first run), only fetches entries from the last FIRST_RUN_PUBLISHED_AFTER_DAYS
    to avoid pulling years of old unread (e.g. 2018). If PUBLISHED_AFTER_DAYS > 0, still skips older entries.
    Returns the number of sources created.
    """
    base_url = (config.MINIFLUX_URL or "").rstrip("/")
    api_key = config.MINIFLUX_API_KEY or ""
    if not base_url or not api_key:
        return 0

    headers = {"X-Auth-Token": api_key}
    created = 0
    params: dict = {
        "status": "unread",
        "order": "published_at",
        "direction": "asc",
    }
    if last_fetch_at and last_fetch_at.strip():
        ts = _iso_date_to_unix_timestamp(last_fetch_at.strip())
        if ts > 0:
            params["published_after"] = ts
    else:
        # 首次 run：只拉最近 N 天，避免拉 2018 等陈年未读
        if config.FIRST_RUN_PUBLISHED_AFTER_DAYS > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=config.FIRST_RUN_PUBLISHED_AFTER_DAYS)
            params["published_after"] = int(cutoff.timestamp())

    with httpx.Client(timeout=30.0) as client:
        # Get unread entry ids (read-only; we do not mark as read), 按发布时间正序
        r = client.get(
            f"{base_url}/v1/entries",
            params=params,
            headers=headers,
        )
        r.raise_for_status()
        payload = r.json()
        entry_ids = [e["id"] for e in payload.get("entries", []) if isinstance(e.get("id"), int)]

        for entry_id in entry_ids:
            # Get full entry details (read-only)
            r2 = client.get(f"{base_url}/v1/entries/{entry_id}", headers=headers)
            r2.raise_for_status()
            entry = r2.json()

            title = (entry.get("title") or "").strip()
            content = entry.get("content") or ""
            url = (entry.get("url") or "").strip()
            published_at = _published_at_to_iso(entry.get("published_at"))
            if not _is_after_cutoff(published_at):
                continue  # 跳过超过 PUBLISHED_AFTER_DAYS 的旧文章，不写入 Airtable
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
