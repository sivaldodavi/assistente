from __future__ import annotations

import calendar
import unicodedata
from datetime import date
from uuid import uuid4


SCHEDULE_KEYS = ("report_date", "debate_date", "dissertation_date", "final_date")

SCHEDULE_TEMPLATES = {
    "case": (
        ("case-theme", "Escolher e delimitar o tema"),
        ("case-narrative", "Construir a narrativa: personagens, contexto e conflito"),
        ("case-question", "Formular a questão jurídica central"),
        ("case-decisions", "Cadastrar as decisões possíveis"),
        ("case-research", "Pesquisar legislação, jurisprudência e doutrina"),
        ("case-arguments", "Montar argumentos para cada decisão"),
        ("case-criteria", "Registrar critérios e valores da decisão"),
        ("case-debate", "Preparar e participar do debate"),
        ("case-debate-notes", "Registrar objeções e aprendizados do debate"),
        ("case-dissertation", "Redigir a dissertação argumentativa"),
        ("case-review", "Conferir referências e checklist"),
        ("case-delivery", "Preparar a entrega"),
    ),
    "paper": (
        ("paper-theme", "Delimitar o tema e o problema"),
        ("paper-hypothesis", "Definir hipóteses e objetivos"),
        ("paper-method", "Definir a metodologia"),
        ("paper-research", "Pesquisar e organizar as fontes"),
        ("paper-project", "Escrever o Projeto de Paper"),
        ("paper-project-review", "Revisar o Projeto de Paper"),
        ("paper-development", "Estruturar o desenvolvimento em tópicos"),
        ("paper-writing", "Escrever o Paper Final"),
        ("paper-conclusion", "Retomar problema, hipótese e conclusão"),
        ("paper-review", "Conferir referências e extensão"),
        ("paper-delivery", "Preparar a entrega"),
    ),
}

_MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) == 10 and text[2] == "/" and text[5] == "/":
        text = f"{text[6:]}-{text[3:5]}-{text[:2]}"
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def _text(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _normalise_title(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(character for character in text if unicodedata.category(character) != "Mn")


def _template_key(project_type: str, title: str) -> str:
    normalized = _normalise_title(title)
    aliases = (
        (
            ("metodologia", "paper-method"),
            ("hipotese", "paper-hypothesis"),
            ("hipoteses", "paper-hypothesis"),
            ("fontes", "paper-research"),
            ("projeto de paper", "paper-project"),
            ("paper final", "paper-writing"),
            ("conclusao", "paper-conclusion"),
        )
        if project_type in {"paper", "paper_project", "paper_final"}
        else (
            ("decisoes possiveis", "case-decisions"),
            ("debate", "case-debate"),
            ("dissertacao", "case-dissertation"),
            ("entrega", "case-delivery"),
            ("questao juridica", "case-question"),
        )
    )
    return next((key for fragment, key in aliases if fragment in normalized), "")


def normalize_schedule(raw: object, fallback_date: object = "", project_type: str = "case") -> dict:
    source = raw if isinstance(raw, dict) else {}
    report_date = source.get("report_date") or source.get("deliveryDate") or source.get("paper_project_date")
    final_date = source.get("final_date") or source.get("finalDate") or source.get("paperFinalDate")
    tasks = []
    raw_tasks = source.get("tasks") if isinstance(source.get("tasks"), list) else []
    for item in raw_tasks[:100]:
        if not isinstance(item, dict):
            continue
        raw_date = item.get("date")
        due = _date(raw_date)
        if raw_date and not due:
            continue
        title = _text(item.get("title"), 180)
        identifier = _text(item.get("id"), 80) or str(uuid4())
        if not title and not due and not item.get("id"):
            continue
        raw_stage = item.get("stage")
        stage = raw_stage if isinstance(raw_stage, int) and raw_stage >= 0 else None
        template_key = _text(item.get("template_key") or item.get("templateKey"), 80)
        tasks.append({
            "id": identifier,
            "title": title,
            "date": due,
            "done": bool(item.get("done")),
            "stage": stage,
            "template_key": template_key or _template_key(project_type, title),
        })
    return {
        "report_date": _date(report_date) or _date(fallback_date),
        "debate_date": _date(source.get("debate_date") or source.get("debateDate")),
        "dissertation_date": _date(source.get("dissertation_date") or source.get("dissertationDate")),
        "final_date": _date(final_date),
        "tasks": tasks,
    }


def schedule_templates(project_type: str):
    return SCHEDULE_TEMPLATES["paper" if project_type in {"paper", "paper_project", "paper_final"} else "case"]


def schedule_deadlines(schedule: dict, project_type: str, project_id: str, title: str) -> list[dict]:
    normalized = normalize_schedule(schedule, project_type=project_type)
    keys = (
        (("report_date", "Entrega do relatório"), ("debate_date", "Debate"), ("dissertation_date", "Dissertação"))
        if project_type == "case"
        else (("report_date", "Projeto de Paper"), ("final_date", "Paper Final"))
    )
    return [
        {
            "project_id": project_id,
            "title": title or ("Paper sem título" if project_type != "case" else "Relatório sem título"),
            "kind": key,
            "label": label,
            "date": normalized[key],
            "date_label": f"{normalized[key][8:10]}/{normalized[key][5:7]}/{normalized[key][:4]}",
        }
        for key, label in keys
        if normalized[key]
    ]


def schedule_summary(schedule: dict, project_type: str) -> dict:
    normalized = normalize_schedule(schedule, project_type=project_type)
    tasks = normalized["tasks"]
    dates = sorted(schedule_deadlines(normalized, project_type, "", ""), key=lambda item: item["date"])
    return {
        "task_total": len(tasks),
        "task_done": sum(1 for task in tasks if task["done"]),
        "deadline": dates[0] if dates else None,
        "has_dates": bool(dates),
    }


def _edit_level(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def account_calendar(projects: list[dict], edit_activity: list[dict] | None = None, today: date | None = None) -> dict:
    if isinstance(edit_activity, date) and today is None:
        today, edit_activity = edit_activity, None
    today = today or date.today()
    entries = sorted(
        [entry for project in projects for entry in project.get("deadlines", [])],
        key=lambda item: (item["date"], item["title"], item["label"]),
    )
    activity = {
        str(item.get("date")): int(item.get("count") or 0)
        for item in (edit_activity or [])
        if isinstance(item, dict) and item.get("date")
    }
    first = date(today.year, today.month, 1)
    leading = [None] * ((first.weekday() + 1) % 7)
    cells = leading + [{"number": day} for day in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
    by_date = {}
    for entry in entries:
        by_date.setdefault(entry["date"], []).append(entry)
    for cell in cells:
        if cell is None:
            continue
        key = f"{today.year:04d}-{today.month:02d}-{cell['number']:02d}"
        cell["entries"] = by_date.get(key, [])[:2]
        cell["more"] = max(0, len(by_date.get(key, [])) - 2)
        cell["edit_count"] = activity.get(key, 0)
        cell["edit_level"] = _edit_level(cell["edit_count"])
        cell["edit_label"] = f"{cell['edit_count']} edição(ões) neste dia"
    upcoming = [entry for entry in entries if entry["date"] >= today.isoformat()]
    if not upcoming:
        upcoming = list(reversed(entries))
    return {
        "has_dates": bool(entries),
        "has_activity": bool(activity),
        "month_has_dates": any(cell.get("entries") for cell in cells if cell),
        "month_has_activity": any(cell.get("edit_count") for cell in cells if cell),
        "month_label": f"{_MONTHS[today.month - 1]} de {today.year}",
        "weekdays": ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"),
        "cells": cells,
        "upcoming": upcoming[:5],
        "upcoming_label": "Próximas datas" if any(entry["date"] >= today.isoformat() for entry in entries) else "Datas cadastradas",
    }
