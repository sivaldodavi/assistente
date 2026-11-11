from __future__ import annotations

from .workflow import workflow_sections

PAPER_PROJECT_SECTIONS = workflow_sections("paper_project")
PAPER_FINAL_SECTIONS = workflow_sections("paper_final")


def paper_sections(project_type: str) -> list[dict]:
    return PAPER_FINAL_SECTIONS if project_type == "paper_final" else PAPER_PROJECT_SECTIONS


def _rules(project_type: str) -> dict:
    return {field["id"]: field for section in paper_sections(project_type) for field in section["fields"]}


def normalize_paper_fields(raw: object, project_type: str) -> dict:
    source = raw if isinstance(raw, dict) else {}
    normalized = {}
    all_rules = _rules("paper_project") | _rules("paper_final") | {"development": {"limit": 30000}} | {key: {"limit": 160} for key in ("institution", "course", "city")}
    for field_id, rule in all_rules.items():
        value = source.get(field_id, "")
        if not isinstance(value, str):
            value = str(value or "")
        normalized[field_id] = value.strip()[: rule["limit"]]
    return normalized


def paper_progress(fields: object, project_type: str) -> dict:
    normalized = normalize_paper_fields(fields, project_type)
    required = [field_id for field_id, rule in _rules(project_type).items() if rule.get("required")]
    done = sum(bool(normalized.get(field_id)) for field_id in required)
    return {"done": done, "total": len(required), "percent": round(done / len(required) * 100) if required else 100}
