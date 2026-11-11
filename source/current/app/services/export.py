"""Prévia HTML e PDF ABNT com Typst/Quarto, sem interpretar texto do usuário como código."""
import html
from pathlib import Path

from ..domain.case import case_sections
from ..domain.paper import paper_sections
from .quarto_documents import (
    QuartoBusyError,
    QuartoDocumentError,
    QuartoRenderError,
    QuartoUnavailableError,
    build_quarto_source,
    render_document_pdf,
)


class ExportUnavailable(RuntimeError):
    pass


def _paragraphs(value):
    text = str(value or "").strip()
    if not text:
        return '<p class="empty">Não preenchido.</p>'
    return "".join(f"<p>{html.escape(part.strip())}</p>" for part in text.split("\n\n") if part.strip())


def _sections(project):
    if project.get("project_type") == "case":
        phase = project.get("export_phase", "report")
        return [section for section in case_sections() if section["phase"] == phase]
    return paper_sections(project.get("project_type", "paper_project"))


def _document_sections(project, sources):
    """Produz as mesmas seções acadêmicas para HTML e PDF, na ordem do roteiro."""
    fields = project.get("fields", {})
    result = []
    for section in _sections(project):
        custom = section.get("custom")
        if custom == "review":
            continue
        content = [(field["label"], fields.get(field["id"], "")) for field in section["fields"] if field["id"] not in {"title", "authors"}]
        if custom == "criteria":
            content = [(item.get("title", "Critério"), (item.get("definition", "") + "\n\nBase: " + item.get("basis", ""))) for item in project.get("criteria", [])]
        elif custom == "dissertation":
            development = [(item.get("title", "Tópico"), item.get("body", "")) for item in project.get("development_sections", [])]
            if not development:
                old = fields.get("dissertation_foundation") or fields.get("development")
                if old:
                    development = [("Fundamentação", old)]
            content = [
                ("Introdução", fields.get("dissertation_intro", "")),
                *development,
                ("Conclusão", fields.get("dissertation_conclusion", "")),
            ]
        elif custom == "development":
            content = [(item.get("title", "Tópico"), item.get("body", "")) for item in project.get("development_sections", [])]
            if not content:
                old = fields.get("dissertation_foundation") or fields.get("development")
                if old:
                    content = [("Fundamentação", old)]
        elif custom == "sources":
            content = [("", source.get("reference") or " — ".join(value for value in (source.get("author"), source.get("title")) if value)) for source in sorted(sources, key=lambda item: (item.get("author") or item.get("title") or "").casefold())]
        result.append((section["title"], content))
    return result


def build_project_html(project, sources):
    fields = project.get("fields", {})
    title = fields.get("title") or project.get("title") or "Trabalho sem título"
    authors = fields.get("dissertation_author") if project.get("export_phase") == "dissertation" else fields.get("authors")
    authors = authors or "Autor não informado"
    parts = []
    for heading, content in _document_sections(project, sources):
        body = "".join((f"<h3>{html.escape(label)}</h3>" if label else "") + _paragraphs(value) for label, value in content)
        parts.append(f"<section><h2>{html.escape(heading)}</h2>{body or '<p class=empty>Não preenchido.</p>'}</section>")
    workflow = "".join(parts)
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font:16px/1.6 Georgia,serif;max-width:850px;margin:3rem auto;padding:0 1.5rem;color:#171717}}h1,h2,h3{{font-family:system-ui,sans-serif}}h1{{font-size:2.3rem}}h2{{margin-top:2.5rem;border-bottom:1px solid #bbb;padding-bottom:.35rem}}.meta{{color:#555}}.empty{{color:#666;font-style:italic}}</style></head>
<body><header><h1>{html.escape(title)}</h1><p class="meta">{html.escape(authors).replace(chr(10), '<br>')}</p></header>{workflow}</body></html>'''


def _legacy_project(project, sources):
    """Mapeia o payload snake_case atual para o contrato Typst do compositor original."""
    fields = project.get("fields", {}) if isinstance(project.get("fields"), dict) else {}
    project_type = project.get("project_type")
    schedule = project.get("schedule") if isinstance(project.get("schedule"), dict) else {}
    authors = fields.get("authors") or fields.get("author") or ""
    mapped = {
        "title": fields.get("title", ""),
        "author": authors,
        "institution": fields.get("institution", ""),
        "course": fields.get("course", ""),
        "city": fields.get("city", ""),
        "year": fields.get("year", ""),
        "profile": fields.get("profile", ""),
        "discipline": fields.get("discipline", ""),
        "teacher": fields.get("teacher", ""),
        "classInfo": " · ".join(value for value in (fields.get("period", ""), fields.get("shift", "")) if value),
        "subtitle": fields.get("subtitle", fields.get("sub_title", "")),
        "abstract": fields.get("abstract", ""),
        "keywords": fields.get("keywords", ""),
        "paperKind": "final" if project_type == "paper_final" else "project",
    }
    field_map = {
        "assignment_prompt": "assignmentPrompt",
        "facts": "facts",
        "problem": "problem",
        "decision_basis": "decisionBasis",
        "decision_a": "decisionA",
        "decision_b": "decisionB",
        "thesis_a_title": "thesisATitle",
        "thesis_a": "thesisA",
        "thesis_b_title": "thesisBTitle",
        "thesis_b": "thesisB",
        "area": "area",
        "delimitation": "delimitation",
        "research_context": "researchContext",
        "research_object": "researchObject",
        "problem_context": "problemContext",
        "hypothesis": "hypothesis",
        "justification": "justification",
        "objective_general": "objectiveGeneral",
        "objective1": "objective1",
        "objective2": "objective2",
        "objective3": "objective3",
        "theory": "theory",
        "method_author": "methodAuthor",
        "nature": "nature",
        "approach": "approach",
        "ends": "ends",
        "procedure": "procedure",
        "instruments": "instruments",
        "introduction": "introduction",
        "conclusion": "conclusion",
        "ai_note": "aiNote",
    }
    for source, target in field_map.items():
        mapped[target] = fields.get(source, "")
    mapped["developmentSections"] = [
        {"title": item.get("title", ""), "content": item.get("body", "")}
        for item in project.get("development_sections", [])
        if isinstance(item, dict)
    ]
    mapped["deliveryDate"] = schedule.get("final_date" if project_type == "paper_final" else "report_date", "")
    criteria = []
    for item in project.get("criteria", []):
        if isinstance(item, dict):
            criteria.append({"term": item.get("title", item.get("term", "")), "definition": item.get("definition", ""), "basis": item.get("basis", "")})
    mapped_project_type = "case" if project_type == "case" else "paper"
    return {"projectType": mapped_project_type, "fields": mapped, "criteria": criteria, "sources": sources, "schedule": schedule}


def build_typst_source(project, sources):
    document_kind = "case_report" if project.get("project_type") == "case" else ("paper_final" if project.get("project_type") == "paper_final" else "paper_project")
    try:
        return build_quarto_source(_legacy_project(project, sources), document_kind)
    except QuartoDocumentError as error:
        raise ExportUnavailable(str(error)) from error


def build_project_markdown(project, sources):
    """Mantém um nome de compatibilidade interno, agora gerando QMD com Typst/ABNT."""
    return build_typst_source(project, sources)


def render_pdf(project, sources):
    if project.get("project_type") == "case" and project.get("export_phase", "report") != "report":
        raise ExportUnavailable("O PDF do Case é gerado na fase Relatório; as demais fases podem ser consultadas na prévia.")
    document_kind = "case_report" if project.get("project_type") == "case" else ("paper_final" if project.get("project_type") == "paper_final" else "paper_project")
    try:
        return render_document_pdf(_legacy_project(project, sources), document_kind)
    except (QuartoDocumentError, QuartoUnavailableError, QuartoBusyError, QuartoRenderError) as error:
        raise ExportUnavailable(str(error)) from error
