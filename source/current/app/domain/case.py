from __future__ import annotations

from uuid import uuid4

from .workflow import workflow_sections

ALL_CASE_SECTIONS = workflow_sections("case")
CASE_SECTIONS = [section for section in ALL_CASE_SECTIONS if section["phase"] == "report"]
CASE_LATER_SECTIONS = [section for section in ALL_CASE_SECTIONS if section["phase"] != "report"]

_FIELD_RULES = {field["id"]: field for section in ALL_CASE_SECTIONS for field in section["fields"]}
_FIELD_RULES.update({key: {"limit": 160} for key in ("institution", "course", "city")})
_FIELD_RULES["dissertation_foundation"] = {"limit": 30000}
_BASE_FIELD_RULES = {field["id"]: field for section in CASE_SECTIONS for field in section["fields"]}
REQUIRED_CASE_FIELDS = tuple(field_id for field_id, field in _BASE_FIELD_RULES.items() if field.get("required"))


def case_sections() -> list[dict]:
    return ALL_CASE_SECTIONS


def normalize_case_fields(raw: object) -> dict:
    source = raw if isinstance(raw, dict) else {}
    normalized = {}
    for field_id, rule in _FIELD_RULES.items():
        value = source.get(field_id, "")
        if not isinstance(value, str):
            value = str(value or "")
        normalized[field_id] = value.strip()[: rule["limit"]]
    return normalized


def case_progress(fields: object) -> dict:
    normalized = normalize_case_fields(fields)
    done = sum(bool(normalized.get(field_id, "")) for field_id in REQUIRED_CASE_FIELDS)
    total = len(REQUIRED_CASE_FIELDS)
    return {"done": done, "total": total, "percent": round(done / total * 100) if total else 100}


def missing_case_fields(fields: object) -> list[str]:
    normalized = normalize_case_fields(fields)
    return [field_id for field_id in REQUIRED_CASE_FIELDS if not normalized.get(field_id)]


def normalize_criteria(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    criteria = []
    for item in raw[:40]:
        if not isinstance(item, dict):
            continue
        criterion = {
            "id": str(item.get("id") or uuid4())[:80],
            "title": str(item.get("title") or "").strip()[:180],
            "definition": str(item.get("definition") or "").strip()[:3000],
            "basis": str(item.get("basis") or "").strip()[:1000],
        }
        if any(criterion[key] for key in ("title", "definition", "basis")):
            criteria.append(criterion)
    return criteria
