from ..services.assistant import ALLOWED_FIELDS
import json
from copy import deepcopy

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from ..auth import current_account_id, login_required, require_csrf
from ..domain.case import case_progress, case_sections, normalize_case_fields, normalize_criteria
from ..domain.paper import normalize_paper_fields, paper_progress, paper_sections
from ..domain.workflow import PHASE_LABELS, normalize_checks, normalize_deliveries, normalize_development, review_groups
from ..domain.schedule import account_calendar, normalize_schedule, schedule_summary, schedule_templates
import json
import time
from uuid import uuid4

from ..store.accounts import get_account
from ..store.projects import ProjectConflict, ProjectQuotaError, create_project, delete_project, get_project, list_edit_activity, list_projects, save_project
from ..store.sharing import get_sharing, list_comments, save_sharing
from ..store.sources import SOURCE_KINDS, create_source as create_library_source, list_sources, owned_source_ids
from ..store.revisions import create_revision, list_revisions, get_revision, diff_revisions, restore_revision
from ..services.quarto_documents import render_document_pdf, QuartoUnavailableError, QuartoBusyError, QuartoRenderError, QuartoDocumentError


projects_bp = Blueprint("projects", __name__)


@projects_bp.get("/account")
@login_required
def account():
    projects = list_projects(current_account_id())
    from datetime import date
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1).isoformat()
    return render_template(
        "account/home.html",
        account=get_account(current_account_id()),
        projects=projects,
        account_calendar=account_calendar(projects, list_edit_activity(current_account_id(), start, end)),
    )


@projects_bp.post("/projects")
@login_required
@require_csrf
def create():
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["terms_accepted"]:
        return redirect(url_for("account.settings", required="terms"))
    project_type = request.form.get("project_type", "case")
    if project_type not in {"case", "paper_project", "paper_final"}:
        abort(400, description="Tipo de projeto inválido.")
    try:
        project_id = create_project(current_account_id(), project_type)
    except ProjectQuotaError:
        return redirect(url_for("projects.account", error="project_quota"))
    return redirect(url_for("projects.editor", project_id=project_id))


@projects_bp.post("/projects/<project_id>/delete")
@login_required
@require_csrf
def delete(project_id):
    if not delete_project(current_account_id(), project_id):
        abort(404)
    return redirect(url_for("projects.account", deleted="1"))


@projects_bp.get("/projects/<project_id>")
@login_required
def editor(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)
    project["schedule"] = normalize_schedule(
        project.get("schedule"),
        project.get("fields", {}).get("deliveryDate", ""),
        project["project_type"],
    )
    project["source_ids"] = project.get("source_ids", [])
    project["criteria"] = normalize_criteria(project.get("criteria", []))
    project["checks"] = normalize_checks(project.get("checks"), project["project_type"])
    project["deliveries"] = normalize_deliveries(project.get("deliveries"))
    project["development_sections"] = normalize_development(project.get("development_sections"))
    if not project["development_sections"]:
        previous = project.get("fields", {}).get("dissertation_foundation") or project.get("fields", {}).get("development")
        if previous:
            project["development_sections"] = [{"id": "existing", "title": "Fundamentação", "body": previous}]
    is_case = project["project_type"] == "case"
    is_paper = project["project_type"] in {"paper_project", "paper_final"}
    sections = deepcopy(case_sections() if is_case else paper_sections(project["project_type"]))
    review_phase = "report" if is_case else project["project_type"]
    review_summaries = {
        phase: review_groups(sections, project["checks"], phase)
        for phase in {item.get("phase") for item in sections}
    }
    profile = (get_account(current_account_id()) or {}).get("profile", {})
    for section in sections:
        for field in section["fields"]:
            if field.get("source"):
                values = list(profile.get(field["source"], []))
                current = project.get("fields", {}).get(field["id"], "")
                if current and current not in values:
                    values.append(current)
                field["type"] = "select"
                field["options"] = [["", "Selecione…"]] + [[value, value] for value in values]
                field["hint"] = "Cadastre suas opções em Meu perfil. Alterar o perfil não muda este trabalho."
    return render_template(
        "projects/editor.html",
        project=project,
        sources=list_sources(current_account_id()),
        case_sections=sections if is_case else [],
        case_progress=case_progress(project.get("fields", {})) if is_case else None,
        paper_sections=sections if is_paper else [],
        paper_progress=paper_progress(project.get("fields", {}), project["project_type"]) if is_paper else None,
        review_summary=review_summaries.get(review_phase, {"groups": [], "done": 0, "total": 0, "percent": 100}),
        review_summaries=review_summaries,
        schedule_summary=schedule_summary(project["schedule"], project["project_type"]),
        schedule_templates=schedule_templates(project["project_type"]),
        sharing=get_sharing(current_account_id(), project_id),
        comments=list_comments(project_id),
        ai_allowed_fields=ALLOWED_FIELDS,
        phase_labels=PHASE_LABELS,
    )


@projects_bp.post("/projects/<project_id>/save")
@login_required
@require_csrf
def save(project_id):
    body = request.get_json(silent=True) or {}
    current_project = get_project(current_account_id(), project_id)
    if current_project is None:
        abort(404)
    try:
        revision = int(body.get("revision"))
    except (TypeError, ValueError):
        abort(400, description="Revisão inválida.")
    payload = body.get("payload")
    if not isinstance(payload, dict):
        abort(400, description="Projeto inválido.")
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    fields = current_project.get("fields", {}) | fields
    if current_project["project_type"] == "case":
        normalized_fields = normalize_case_fields(fields)
    elif current_project["project_type"] in {"paper_project", "paper_final"}:
        normalized_fields = normalize_paper_fields(fields, current_project["project_type"])
    else:
        normalized_fields = {"title": str(fields.get("title") or "")[:240]}
    requested_project_source_ids = payload.get("source_ids") if isinstance(payload.get("source_ids"), list) else []
    valid_project_source_ids = owned_source_ids(current_account_id(), requested_project_source_ids)
    project_source_ids = [source_id for source_id in requested_project_source_ids if source_id in valid_project_source_ids]
    criteria = normalize_criteria(payload.get("criteria")) if current_project["project_type"] == "case" else []
    schedule = normalize_schedule(
        payload.get("schedule"),
        normalized_fields.get("deliveryDate", ""),
        current_project["project_type"],
    )
    payload = {
        "version": 1,
        "fields": normalized_fields,
        "checks": normalize_checks(payload.get("checks"), current_project["project_type"]),
        "deliveries": normalize_deliveries(payload.get("deliveries")),
        "development_sections": normalize_development(payload.get("development_sections")),
        "source_ids": project_source_ids,
        "criteria": criteria,
        "schedule": schedule,
    }
    try:
        next_revision = save_project(current_account_id(), project_id, revision, payload)
    except ProjectConflict as error:
        return jsonify({"error": "project_conflict", "revision": error.current_revision}), 409
    if next_revision is None:
        abort(404)
    return jsonify({"ok": True, "revision": next_revision})


@projects_bp.post("/projects/<project_id>/sources")
@login_required
@require_csrf
def create_source(project_id):
    if get_project(current_account_id(), project_id) is None:
        abort(404)
    body = request.get_json(silent=True) or {}
    title = str(body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "invalid_source", "message": "Informe o título da fonte."}), 400
    kind = str(body.get("kind") or "other")
    source_id = create_library_source(
        current_account_id(),
        title,
        body.get("author", ""),
        kind if kind in SOURCE_KINDS else "other",
        body.get("reference", ""),
        body.get("notes", ""),
    )
    source = next(item for item in list_sources(current_account_id()) if item["id"] == source_id)
    return jsonify({"ok": True, "source": source})


@projects_bp.post("/projects/<project_id>/sharing")
@login_required
@require_csrf
def update_sharing(project_id):
    sharing = save_sharing(current_account_id(), project_id, request.form.get("allow_admin_view") == "on", request.form.get("allow_admin_comments") == "on")
    if sharing is None:
        abort(404)
    return redirect(url_for("projects.editor", project_id=project_id, saved="sharing"))


@projects_bp.post("/projects/<project_id>/paper-mode")
@login_required
@require_csrf
def paper_mode(project_id):
    from ..store.projects import switch_paper_mode
    body = request.get_json(silent=True) or {}
    try:
        revision = int(body.get("revision"))
        updated = switch_paper_mode(current_account_id(), project_id, body.get("project_type"), revision)
    except ProjectConflict as error:
        return jsonify({"error": "project_conflict", "revision": error.current_revision}), 409
    except (ValueError, TypeError):
        abort(400, description="Roteiro ou revisão inválidos.")
    if updated is None:
        abort(404)
    return jsonify({"ok": True, "revision": updated})


# ──────────────────────────────────────────────
# Duplicate Project
# ──────────────────────────────────────────────

@projects_bp.post("/projects/<project_id>/duplicate")
@login_required
@require_csrf
def duplicate(project_id):
    body = request.get_json(silent=True) or {}
    try:
        revision = int(body.get("revision"))
    except (TypeError, ValueError):
        abort(400, description="Revisão inválida.")

    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)

    if int(revision) != int(project["revision"]):
        return jsonify({"error": "project_conflict", "revision": project["revision"]}), 409

    # Verifica se a conta tem crédito de projeto
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    if not account["unlimited"] and int(account["project_remaining"] or 0) <= 0:
        return jsonify({"error": "project_quota", "message": "Sem créditos de projeto disponíveis."}), 402

    try:
        new_project_id = create_project(current_account_id(), project["project_type"])
    except ProjectQuotaError:
        return jsonify({"error": "project_quota", "message": "Sem créditos de projeto disponíveis."}), 402

    # Copia o payload completo
    payload = {k: v for k, v in project.items() if k not in {"id", "revision", "created_at", "updated_at", "title"}}
    payload["version"] = 1
    payload["fields"] = {**project.get("fields", {}), "title": f"Cópia de {project.get('title', 'Projeto')}"}
    new_title = payload["fields"]["title"][:240]

    from ..store.projects import get_db
    import time
    now = int(time.time())
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        # Atualiza o novo projeto com o payload copiado
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        db.execute(
            """UPDATE projects SET title = ?, payload = ?, updated_at = ?
               WHERE id = ? AND account_id = ?""",
            (new_title, encoded, now, new_project_id, current_account_id()),
        )
        # Cria revisão inicial do projeto duplicado
        create_revision(current_account_id(), new_project_id, 1, new_title, project["project_type"], payload)
        db.commit()
    except Exception:
        db.rollback()
        # Tenta limpar o projeto criado se falhar
        try:
            db.execute("DELETE FROM projects WHERE id = ?", (new_project_id,))
            db.execute("UPDATE accounts SET project_used = CASE WHEN project_used > 0 THEN project_used - 1 ELSE 0 END WHERE id = ?", (current_account_id(),))
            db.commit()
        except Exception:
            pass
        return jsonify({"error": "duplicate_failed", "message": "Falha ao duplicar projeto."}), 500

    return jsonify({"ok": True, "project_id": new_project_id, "revision": 1})


# ──────────────────────────────────────────────
# Quarto PDF Export
# ──────────────────────────────────────────────

_DOCUMENT_KINDS = {
    "case_report": "case",
    "paper_project": "paper",
    "paper_final": "paper",
}

@projects_bp.post("/projects/<project_id>/export/pdf")
@login_required
@require_csrf
def export_pdf(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)

    body = request.get_json(silent=True) or {}
    document_kind = body.get("document_kind")

    if document_kind not in _DOCUMENT_KINDS:
        return jsonify({"error": "invalid_document_kind", "message": "Tipo de documento inválido."}), 400

    expected_type = _DOCUMENT_KINDS[document_kind]
    if project.get("project_type") != expected_type:
        return jsonify({"error": "project_type_mismatch", "message": "Tipo de documento não corresponde ao projeto."}), 400

    try:
        pdf_bytes = render_document_pdf(project, document_kind)
    except QuartoUnavailableError:
        return jsonify({"error": "quarto_unavailable", "message": "O renderizador Quarto não está disponível."}), 503
    except QuartoBusyError:
        return jsonify({"error": "quarto_busy", "message": "Há muitas renderizações em andamento. Tente novamente."}), 503
    except QuartoRenderError as error:
        return jsonify({"error": "quarto_render_error", "message": str(error)}), 500
    except QuartoDocumentError as error:
        return jsonify({"error": "invalid_document", "message": str(error)}), 400

    from flask import Response
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{project["title"] or "documento"}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ──────────────────────────────────────────────
# Revisions (History, Diff, Restore)
# ──────────────────────────────────────────────

@projects_bp.get("/projects/<project_id>/revisions")
@login_required
def revisions_list(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)

    revs = list_revisions(project_id, current_account_id())
    return jsonify({"ok": True, "revisions": revs})


@projects_bp.get("/projects/<project_id>/revisions/diff")
@login_required
def revisions_diff(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)

    snapshot_a = request.args.get("a")
    snapshot_b = request.args.get("b")
    if not snapshot_a or not snapshot_b:
        return jsonify({"error": "missing_snapshots", "message": "Informe os snapshots 'a' e 'b'."}), 400

    diff = diff_revisions(current_account_id(), project_id, snapshot_a, snapshot_b)
    if diff is None:
        return jsonify({"error": "revision_not_found", "message": "Uma das revisões não foi encontrada."}), 404

    return jsonify({"ok": True, "diff": diff})


@projects_bp.post("/projects/<project_id>/revisions/restore")
@login_required
@require_csrf
def revisions_restore(project_id):
    project = get_project(current_account_id(), project_id)
    if project is None:
        abort(404)

    body = request.get_json(silent=True) or {}
    snapshot_id = body.get("snapshot_id")
    try:
        expected_revision = int(body.get("revision"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_revision", "message": "Revisão inválida."}), 400

    if not snapshot_id:
        return jsonify({"error": "missing_snapshot", "message": "Informe o snapshot_id."}), 400

    try:
        next_revision = restore_revision(current_account_id(), project_id, snapshot_id, expected_revision)
    except ProjectConflict as error:
        return jsonify({"error": "project_conflict", "revision": error.current_revision}), 409
    except Exception:
        return jsonify({"error": "restore_failed", "message": "Falha ao restaurar revisão."}), 500

    if next_revision is None:
        return jsonify({"error": "restore_failed", "message": "Revisão não encontrada ou projeto inexistente."}), 404

    return jsonify({"ok": True, "revision": next_revision})
