"""
Org alias resolution and company/org lookup-or-create for the extraction pipeline.
Uses data/org_aliases.json and storage backend (find_company uses name_cn, find_org uses name).
"""
import json
from pathlib import Path

import config
from storage.base import StorageBackend

# Path to org aliases: {"canonical": ["alias1", "alias2"], ...} or {"红杉中国": ["红杉资本", "Sequoia China"], ...}
_ALIASES_PATH = config.PROJECT_ROOT / "data" / "org_aliases.json"

# Map: alias or canonical name -> canonical name (built once at import)
_alias_to_canonical: dict[str, str] = {}


def _load_org_aliases() -> dict[str, str]:
    """Load org_aliases.json and build alias/canonical -> canonical map."""
    global _alias_to_canonical
    if _alias_to_canonical:
        return _alias_to_canonical
    path = _ALIASES_PATH
    if not path.exists():
        _alias_to_canonical = {}
        return _alias_to_canonical
    raw = json.load(path.open(encoding="utf-8"))
    out: dict[str, str] = {}
    for canonical, aliases in raw.items():
        if isinstance(aliases, list):
            out[canonical] = canonical
            for a in aliases:
                if isinstance(a, str) and a.strip():
                    out[a.strip()] = canonical
        else:
            out[canonical] = canonical
    _alias_to_canonical = out
    return _alias_to_canonical


def find_org_canonical(name: str) -> str | None:
    """
    Return the canonical org name if the given name is in the aliases map (as canonical or alias).
    Otherwise return None.
    """
    aliases = _load_org_aliases()
    return aliases.get(name) if name else None


def resolve_company(storage: StorageBackend, name: str) -> str:
    """
    Resolve company by name (matched against name_cn). If found return record id;
    otherwise create company with name_cn=name and notes='自动创建，待复核' and return new id.
    """
    rec = storage.find_company(name)
    if rec is not None:
        return rec["id"]
    new_id = storage.create_company({
        "name_cn": name,
        "notes": "自动创建，待复核",
    })
    return new_id


def resolve_org(storage: StorageBackend, name: str) -> str:
    """
    Resolve org by name. First try canonical name from aliases and find_org(canonical);
    if not found, try find_org(name). If still not found, create org with name and
    notes='自动创建，待复核' and return new id.
    """
    canonical = find_org_canonical(name)
    if canonical is not None:
        rec = storage.find_org(canonical)
        if rec is not None:
            return rec["id"]
    rec = storage.find_org(name)
    if rec is not None:
        return rec["id"]
    new_id = storage.create_org({
        "name": name,
        "notes": "自动创建，待复核",
    })
    return new_id
