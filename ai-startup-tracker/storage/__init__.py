"""
Storage layer for ai-startup-tracker.
Export the abstract backend and the Airtable implementation.
"""
from storage.base import StorageBackend
from storage.airtable_backend import AirtableBackend

__all__ = ["StorageBackend", "AirtableBackend"]
