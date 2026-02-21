"""Base types and abstract adapter for source content preprocessing."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProcessedContent:
    """Normalized content ready for downstream extraction."""

    text: str
    language: str = ""


class SourceAdapter(ABC):
    """Abstract adapter: raw content + metadata -> ProcessedContent."""

    @abstractmethod
    def preprocess(self, raw_content: str, metadata: dict[str, Any]) -> ProcessedContent:
        """Convert raw content and metadata into normalized ProcessedContent."""
        ...

    @abstractmethod
    def default_reliability(self) -> str:
        """Default reliability tier for this source. One of: high, medium, low."""
        ...
