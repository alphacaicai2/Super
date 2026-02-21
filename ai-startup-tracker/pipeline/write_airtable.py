"""
Write extraction results to storage (Airtable): funding rounds, source status, extraction log.
Uses pipeline.normalize for company/org resolution and config for all constants.
"""
from datetime import datetime

import config
from models.schemas import ExtractionResult, FundingRound
from storage.base import StorageBackend

from . import normalize


def should_review(round: FundingRound) -> bool:
    """
    Return True if this round should be flagged for review: low confidence,
    missing amount (and not Undisclosed), no lead investors, or Undisclosed stage.
    """
    if round.confidence <= 3:
        return True
    if round.amount is None and round.stage != "Undisclosed":
        return True
    if len(round.lead_investors) == 0:
        return True
    if round.stage == "Undisclosed":
        return True
    return False


def write_extraction_result(
    storage: StorageBackend,
    source_id: str,
    source_record: dict,
    result: ExtractionResult,
    token_usage: dict,
) -> None:
    """
    Persist extraction result: create funding round records (with resolved company/org ids),
    update source processing_status, and create an extraction log entry.
    """
    now = datetime.now()
    now_iso = now.isoformat()
    date_only = now_iso[:10]
    any_needs_review = False

    for round in result.funding_rounds:
        company_id = normalize.resolve_company(storage, round.company_name_cn)
        lead_ids = [normalize.resolve_org(storage, n) for n in round.lead_investors]
        co_ids = [normalize.resolve_org(storage, n) for n in round.co_investors]

        record = {
            "company": [company_id],
            "stage": round.stage,
            "date": round.date if round.date else None,
            "amount_value": round.amount.value if round.amount else None,
            "amount_currency": round.amount.currency if round.amount else None,
            "amount_raw": round.amount.raw_text if round.amount else None,
            "valuation_value": round.valuation.value if round.valuation else None,
            "valuation_currency": round.valuation.currency if round.valuation else None,
            "valuation_raw": round.valuation.raw_text if round.valuation else None,
            "lead_investors": lead_ids,
            "co_investors": co_ids,
            "source_primary": [source_id],
            "evidence_text": round.evidence,
            "confidence": round.confidence,
            "verification_status": config.VERIFICATION_STATUS_UNVERIFIED,
            "needs_review": should_review(round),
            "extracted_at": date_only,
            "model_version": config.LLM_MODEL,
        }
        storage.create_funding_round(record)
        if should_review(round):
            any_needs_review = True

    source_status = (
        config.PROCESSING_STATUS_NEEDS_REVIEW
        if any_needs_review
        else config.PROCESSING_STATUS_EXTRACTED
    )
    storage.update_source_status(source_id, source_status)

    storage.create_extraction_log({
        "source": [source_id],
        "run_at": now_iso,
        "model": config.LLM_MODEL,
        "input_tokens": token_usage.get("input_tokens", 0),
        "output_tokens": token_usage.get("output_tokens", 0),
        "status": config.LOG_STATUS_SUCCESS,
        "rounds_extracted": len(result.funding_rounds),
    })
