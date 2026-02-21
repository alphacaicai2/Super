"""
Pydantic models for extraction output.
Match prompts/extraction_schema.json; used to validate LLM JSON response.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Enums from extraction_schema.json ---
CompanySector = Literal[
    "LLM",
    "机器人",
    "自动驾驶",
    "AI医疗",
    "AI芯片",
    "AI安全",
    "AI基础设施",
    "AI应用",
    "具身智能",
    "计算机视觉",
    "NLP",
    "AI for Science",
    "其他",
]

Stage = Literal[
    "Angel",
    "Pre-Seed",
    "Seed",
    "Pre-A",
    "A",
    "A+",
    "B",
    "B+",
    "C",
    "C+",
    "D",
    "E+",
    "Pre-IPO",
    "IPO",
    "Strategic",
    "Acquisition",
    "Undisclosed",
]

AmountCurrency = Literal["CNY", "USD", "EUR", "HKD"]


class Amount(BaseModel):
    """Amount sub-object for funding round."""

    model_config = ConfigDict(extra="allow")

    value: float | None = None
    currency: str | None = None
    raw_text: str | None = None


class Valuation(BaseModel):
    """Valuation sub-object for funding round (same shape as Amount)."""

    model_config = ConfigDict(extra="allow")

    value: float | None = None
    currency: str | None = None
    raw_text: str | None = None


class FundingRound(BaseModel):
    """Single funding event extracted from an article."""

    model_config = ConfigDict(extra="allow")

    company_name_cn: str
    company_name_en: str | None = None
    company_sector: CompanySector = "其他"
    stage: Stage
    date: str | None = None
    amount: Amount | None = None
    valuation: Valuation | None = None
    lead_investors: list[str] = Field(default_factory=list)
    co_investors: list[str] = Field(default_factory=list)
    evidence: str
    confidence: int = Field(..., ge=1, le=5)
    confidence_notes: str | None = None


class ExtractionResult(BaseModel):
    """Top-level extraction result: whether funding info exists and list of rounds."""

    model_config = ConfigDict(extra="allow")

    has_funding_info: bool = False
    funding_rounds: list[FundingRound] = Field(default_factory=list)
