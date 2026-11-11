"""Roteiros acadêmicos, conferências e tópicos: dados puros, sem HTTP ou banco."""
import json
from pathlib import Path
from uuid import uuid4

WORKFLOWS = json.loads(Path(__file__).with_name("academic-workflows.json").read_text(encoding="utf-8"))
PHASE_LABELS = {"report": "Relatório", "debate": "Debate", "dissertation": "Dissertação", "paper_project": "Projeto de Paper", "paper_final": "Paper Final"}


def workflow_sections(project_type):
    return WORKFLOWS.get(project_type, WORKFLOWS["case"])


def normalize_checks(raw, project_type):
    allowed = {key for section in workflow_sections(project_type) for key, _ in section.get("checks", [])}
    source = raw if isinstance(raw, dict) else {}
    return {key: value is True for key, value in source.items() if key in allowed}


def review_groups(sections, checks, phase):
    """Agrupa as conferências da fase atual para a revisão final do roteiro."""
    source = checks if isinstance(checks, dict) else {}
    groups = []
    for section in sections:
        if section.get("phase") != phase or not section.get("checks"):
            continue
        items = [{"label": label, "done": bool(source.get(key))} for key, label in section["checks"]]
        groups.append({
            "title": section["title"],
            "items": items,
            "done": sum(item["done"] for item in items),
            "total": len(items),
        })
    done = sum(group["done"] for group in groups)
    total = sum(group["total"] for group in groups)
    return {"groups": groups, "done": done, "total": total, "percent": round(done / total * 100) if total else 100}


def normalize_deliveries(raw):
    source = raw if isinstance(raw, dict) else {}
    result = {}
    for key in ("report", "dissertation", "paper_project", "paper_final"):
        value = source.get(key)
        if isinstance(value, dict) and value.get("delivered") is True:
            result[key] = {"delivered": True, "at": int(value.get("at") or 0)}
        elif value is True:
            result[key] = {"delivered": True, "at": 0}
    return result


def normalize_development(raw):
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw[:20]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:240]
        body = str(item.get("body") or "").strip()[:30000]
        if title or body:
            rows.append({"id": str(item.get("id") or uuid4())[:80], "title": title, "body": body})
    return rows
