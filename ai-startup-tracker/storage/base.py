"""
Abstract storage backend interface for ai-startup-tracker.
Pipeline and adapters depend only on this interface; concrete backends (e.g. Airtable) implement it.
"""
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract interface for source, company, org, funding round, and extraction log storage."""

    # --- Sources ---
    @abstractmethod
    def create_source(self, data: dict) -> str:
        """Create a source record. Returns the new record id."""
        ...

    @abstractmethod
    def get_pending_sources(self, limit: int = 50) -> list[dict]:
        """Return source records where processing_status == \"new\", up to limit."""
        ...

    @abstractmethod
    def update_source_status(self, source_id: str, status: str) -> None:
        """Set processing_status for the given source record."""
        ...

    # --- Lookups ---
    @abstractmethod
    def find_company(self, name: str) -> dict | None:
        """Find a company by name_cn or aliases. Returns record dict or None."""
        ...

    @abstractmethod
    def find_org(self, name: str) -> dict | None:
        """Find an org by name or aliases. Returns record dict or None."""
        ...

    # --- Creates ---
    @abstractmethod
    def create_company(self, data: dict) -> str:
        """Create a company record. Returns the new record id."""
        ...

    @abstractmethod
    def create_org(self, data: dict) -> str:
        """Create an org record. Returns the new record id."""
        ...

    @abstractmethod
    def create_funding_round(self, data: dict) -> str:
        """Create a funding round record. Returns the new record id."""
        ...

    @abstractmethod
    def create_extraction_log(self, data: dict) -> str:
        """Create an extraction log record. Returns the new record id."""
        ...

    # --- Pipeline state (last fetch time for incremental Miniflux pull) ---
    def get_last_fetch_at(self) -> str | None:
        """Return last fetch timestamp as ISO date string (YYYY-MM-DD), or None if never run."""
        return None

    def set_last_fetch_at(self, iso_date: str) -> None:
        """Persist last fetch date (YYYY-MM-DD or full ISO)."""
        pass
