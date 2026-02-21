"""
Airtable implementation of StorageBackend using pyairtable.
Uses config for API key, base id, and table names.
"""
from pyairtable import Api
from pyairtable.formulas import match

import config
from storage.base import StorageBackend


# Airtable field names used by this backend (align with base schema)
FIELD_PROCESSING_STATUS = "processing_status"
FIELD_NAME_CN = "name_cn"
FIELD_NAME = "name"
FIELD_ALIASES = "aliases"


class AirtableBackend(StorageBackend):
    """Storage backend that reads/writes to Airtable tables."""

    def __init__(
        self,
        api_key: str | None = None,
        base_id: str | None = None,
    ):
        self._api_key = (api_key or config.AIRTABLE_API_KEY).strip()
        self._base_id = (base_id or config.AIRTABLE_BASE_ID).strip()
        if not self._api_key or not self._base_id:
            raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")
        self._api = Api(self._api_key)
        self._sources = self._api.table(self._base_id, config.TABLE_SOURCES)
        self._companies = self._api.table(self._base_id, config.TABLE_COMPANIES)
        self._orgs = self._api.table(self._base_id, config.TABLE_ORGS)
        self._funding_rounds = self._api.table(self._base_id, config.TABLE_FUNDING_ROUNDS)
        self._extraction_log = self._api.table(self._base_id, config.TABLE_EXTRACTION_LOG)
        self._pipeline_state = self._api.table(self._base_id, config.TABLE_PIPELINE_STATE)

    def _record_to_dict(self, record: dict) -> dict:
        """Normalize Airtable record to a plain dict with id and fields merged."""
        out = dict(record.get("fields", {}))
        out["id"] = record.get("id", "")
        return out

    # --- Sources ---
    def create_source(self, data: dict) -> str:
        rec = self._sources.create(data)
        return rec["id"]

    def get_pending_sources(self, limit: int = 50) -> list[dict]:
        formula = match({FIELD_PROCESSING_STATUS: config.PROCESSING_STATUS_NEW})
        records = self._sources.all(formula=formula, max_records=limit)
        return [self._record_to_dict(r) for r in records]

    def update_source_status(self, source_id: str, status: str) -> None:
        self._sources.update(source_id, {FIELD_PROCESSING_STATUS: status})

    # --- Lookups (by primary name; alias search can be extended) ---
    def find_company(self, name: str) -> dict | None:
        rec = self._companies.first(formula=match({FIELD_NAME_CN: name}))
        if rec is None:
            return None
        # Optional: search in aliases by fetching and filtering if needed
        return self._record_to_dict(rec)

    def find_org(self, name: str) -> dict | None:
        rec = self._orgs.first(formula=match({FIELD_NAME: name}))
        if rec is None:
            return None
        return self._record_to_dict(rec)

    # --- Creates ---
    def create_company(self, data: dict) -> str:
        rec = self._companies.create(data)
        return rec["id"]

    def create_org(self, data: dict) -> str:
        rec = self._orgs.create(data)
        return rec["id"]

    def create_funding_round(self, data: dict) -> str:
        rec = self._funding_rounds.create(data)
        return rec["id"]

    def create_extraction_log(self, data: dict) -> str:
        rec = self._extraction_log.create(data)
        return rec["id"]

    # --- Pipeline state (表 PipelineState 不存在时 get 返回 None，set 忽略) ---
    _STATE_FIELD = "last_fetch_at"

    def get_last_fetch_at(self) -> str | None:
        try:
            recs = self._pipeline_state.all(max_records=1)
            if not recs:
                return None
            val = recs[0].get("fields", {}).get(self._STATE_FIELD)
            if val is None:
                return None
            return str(val)[:10]  # YYYY-MM-DD
        except Exception:
            return None

    def set_last_fetch_at(self, iso_date: str) -> None:
        try:
            recs = self._pipeline_state.all(max_records=1)
            date_only = iso_date[:10]
            if recs:
                self._pipeline_state.update(recs[0]["id"], {self._STATE_FIELD: date_only})
            else:
                self._pipeline_state.create({self._STATE_FIELD: date_only})
        except Exception:
            pass
