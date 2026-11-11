import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_from_directory

from ..auth import require_csrf
from ..domain.workflow import workflow_sections
from ..services.research import ResearchUnavailable, search_catalog, entries_by_ids


public_bp = Blueprint("public", __name__)


def _camel_case(value):
    return re.sub(r"_([a-z])", lambda match: match.group(1).upper(), value)


def _demo_workflow_key(model_id, workflow):
    if model_id == "civil-personality":
        return "case", "report"
    if model_id == "projeto-paper-modelo":
        return "paper_project", "paper_project"
    if model_id == "paper-final-modelo":
        return "paper_final", "paper_final"
    if workflow.get("fields", {}).get("paperKind") == "project":
        return "paper_project", "paper_project"
    return "paper_final", "paper_final"


def _normalise_demo_title(value):
    value = unicodedata.normalize("NFD", str(value or "").casefold())
    value = "".join(character for character in value if unicodedata.category(character) != "Mn")
    return " ".join(value.replace("·", " ").replace(".", " ").split())


def _demo_stage_sections(model_id, stage_title, sections):
    """Relaciona o conteúdo preenchido ao mesmo estágio usado no editor.

    Os modelos legados têm subtítulos vazios (por exemplo, cabeçalhos de
    agrupamento). Por isso, a associação não deve depender da posição bruta
    da lista de parágrafos: o título do estágio e o título textual da seção
    são as identidades estáveis.
    """
    maps = {
        "civil-personality": {
            "1 · Descrição do caso": ("1 descricao do caso",),
            "2.1 · Decisões possíveis": ("2 1 descricao das decisoes possiveis",),
            "2.2.1 · Argumentação da tese A": ("2 2 1",),
            "2.2.2 · Argumentação da tese B": ("2 2 2",),
            "2.3 · Critérios e valores": ("2 3 descricao dos criterios e valores",),
        },
        "projeto-paper-modelo": {
            "Identificação e delimitação": ("1 tema", "2 titulo e delimitacao do tema"),
            "Problema de pesquisa": ("3 problema",),
            "Hipótese": ("4 hipoteses",),
            "Justificativa": ("5 justificativa",),
            "Objetivos": ("6 objetivos gerais e especificos",),
            "Referencial teórico": ("7 referencial teorico",),
            "Metodologia": ("8 metodologia",),
            "Referências do projeto": ("9 referencias",),
        },
        "paper-final-modelo": {
            "Introdução": ("1 introducao",),
            "Desenvolvimento": ("2 o inquerito policial", "3 a lei", "4 valor probatorio"),
            "Conclusão": ("5 conclusao",),
            "Referências finais": ("referencias",),
        },
    }
    patterns = maps.get(model_id, {}).get(stage_title, ())
    if not patterns:
        return ()
    normalized_sections = [_normalise_demo_title(section.get("title")) for section in sections]
    return tuple(
        index
        for index, title in enumerate(normalized_sections)
        if any(title.startswith(pattern) for pattern in patterns)
    )


def _build_demo_stages(model_id, workflow, sections):
    workflow_key, phase = _demo_workflow_key(model_id, workflow)
    values = workflow.get("fields", {}) if isinstance(workflow, dict) else {}
    stages = []
    for index, original in enumerate(workflow_sections(workflow_key)):
        if original.get("phase", "report") != phase:
            continue
        stage = deepcopy(original)
        fields = []
        for field in stage.get("fields", []):
            field = deepcopy(field)
            field_id = str(field.get("id") or "")
            candidates = [field_id, _camel_case(field_id)]
            if field_id == "authors":
                candidates.insert(0, "author")
            field["value"] = next((values[key] for key in candidates if key in values), "")
            fields.append(field)
        stage["fields"] = fields
        if stage.get("custom") == "criteria":
            stage["criteria_text"] = values.get("criteriaText", "")
        if stage.get("custom") == "development":
            stage["development_sections"] = values.get("developmentSections", [])
        stage["demo_sections"] = [
            deepcopy(sections[item])
            for item in _demo_stage_sections(model_id, stage.get("title", ""), sections)
            if item < len(sections)
        ]
        stages.append(stage)
    return stages


# A demonstração pública usa somente conteúdo estático, anonimizado e versionado.
# A fonte de verdade foi extraída dos modelos preenchidos do projeto de referência;
# não há conta, projeto ou dado de produção neste arquivo.
def _load_demo_models():
    source = Path(__file__).resolve().parents[1] / "domain" / "public-models.json"
    raw_models = json.loads(source.read_text(encoding="utf-8"))
    models = []
    for raw in raw_models:
        raw_sections = []
        for section in raw.get("sections", []):
            paragraphs = []
            for item in section.get("paragraphs", []):
                if isinstance(item, dict) and item.get("quote"):
                    value = f'“{item["quote"]}”'
                else:
                    value = str(item)
                if value.strip():
                    paragraphs.append(value)
            paragraphs = tuple(paragraphs)
            raw_sections.append({"title": section.get("title", "Seção"), "paragraphs": paragraphs})
        sections = [section for section in raw_sections if section["paragraphs"]]
        model_id = raw.get("id", "")
        if model_id == "civil-personality":
            question_label = "Questão do caso"
            question = next((paragraph for section in sections for paragraph in section["paragraphs"] if "quais são os limites" in paragraph.lower()), "")
        elif model_id == "projeto-paper-modelo":
            question_label = "Problema de pesquisa"
            question = next((section["paragraphs"][-1] for section in sections if "problema" in section["title"].lower() and section["paragraphs"]), "")
        else:
            question_label = "Resumo"
            question = raw.get("abstract", "")
        workflow = deepcopy(raw.get("workflow", {}))
        field_values = dict(workflow.get("fields", {}))
        field_values.setdefault("title", raw.get("title", ""))
        field_values.setdefault("author", raw.get("authors", ""))
        field_values.setdefault("discipline", raw.get("discipline", ""))
        field_values.setdefault("teacher", raw.get("teacher", ""))
        field_values.setdefault("city", raw.get("city", ""))
        field_values.setdefault("year", raw.get("year", ""))
        class_info = raw.get("classInfo", "")
        if class_info:
            field_values.setdefault("classInfo", class_info)
            field_values.setdefault("shift", class_info.split(",", 1)[0].strip())
            if "," in class_info:
                field_values.setdefault("period", class_info.split(",", 1)[1].strip())
        workflow["fields"] = field_values
        models.append({
            "id": model_id,
            "type_label": raw.get("typeLabel", "Modelo preenchido"),
            "title": raw.get("title", ""),
            "authors": raw.get("authors", ""),
            "discipline": raw.get("discipline", ""),
            "teacher": raw.get("teacher", ""),
            "class_info": raw.get("classInfo", ""),
            "delivery_date": raw.get("deliveryDate", ""),
            "city": raw.get("city", ""),
            "year": raw.get("year", ""),
            "question_label": question_label,
            "question": question,
            "summary": raw.get("summary", "Modelo preenchido em modo somente leitura."),
            "abstract": raw.get("abstract", ""),
            "keywords": raw.get("keywords", []),
            "sections": sections,
            "citations": raw.get("citations", []),
            "sources": raw.get("sources", []),
            "workflow": workflow,
            "stages": _build_demo_stages(model_id, workflow, raw_sections),
        })
    return tuple(models)


PUBLIC_DEMO_MODELS = _load_demo_models()
_PUBLIC_PIX_NAMES = frozenset({"avulso-ai.svg", "sem-ia.svg", "com-ia.svg"})


@public_bp.get("/")
def home():
    return render_template(
        "public/home.html",
        demo_models=PUBLIC_DEMO_MODELS,
        google_login=request.args.get("google_login", ""),
        pricing_only=False,
    )


@public_bp.get("/planos", strict_slashes=False)
def pricing():
    return render_template(
        "public/home.html",
        demo_models=PUBLIC_DEMO_MODELS,
        google_login="",
        pricing_only=True,
    )


@public_bp.get("/termos", strict_slashes=False)
def terms():
    return render_template("public/terms.html")


@public_bp.get("/privacidade", strict_slashes=False)
def privacy():
    return render_template("public/privacy.html")


@public_bp.get("/ajuda-ia", strict_slashes=False)
def ai_help():
    return render_template("public/ai-help.html")


@public_bp.get("/jornada", strict_slashes=False)
def journey():
    return render_template("public/journey.html")


@public_bp.get("/pix/<path:filename>")
def pix_asset(filename):
    if filename not in _PUBLIC_PIX_NAMES:
        abort(404)
    # Use safe_join to prevent path traversal
    static_folder = Path(current_app.static_folder)
    pix_dir = static_folder / "pix"
    # Ensure the resolved path is within pix_dir
    file_path = pix_dir / filename
    try:
        file_path.resolve().relative_to(pix_dir.resolve())
    except ValueError:
        abort(404)
    return send_from_directory(pix_dir, filename, mimetype="image/svg+xml", max_age=3600)


# ──────────────────────────────────────────────
# Research Catalog (Public API)
# ──────────────────────────────────────────────

@public_bp.get("/api/research/catalog")
def research_catalog():
    """Catálogo jurídico público com metadata para auxiliar IA/JEV."""
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind")
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit, 100))

    try:
        result = search_catalog(q, kind=kind, limit=limit)
    except ResearchUnavailable:
        return jsonify({"error": "catalog_unavailable", "message": "O catálogo jurídico não está disponível no momento."}), 503

    return jsonify({"ok": True, **result})


@public_bp.post("/api/research/catalog/entries")
@require_csrf
def research_catalog_entries():
    """Obtém entradas completas do catálogo por IDs."""
    body = request.get_json(silent=True) or {}
    ids = body.get("ids")
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "invalid_ids", "message": "Informe uma lista de IDs."}), 400
    ids = [str(id_) for id_ in ids if isinstance(id_, str)][:50]

    try:
        entries = entries_by_ids(ids)
    except ResearchUnavailable:
        return jsonify({"error": "catalog_unavailable", "message": "O catálogo jurídico não está disponível no momento."}), 503

    return jsonify({"ok": True, "entries": entries})
