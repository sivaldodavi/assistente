import json

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from ..auth import admin_required, current_account_id, require_csrf
from ..store.accounts import get_account
from ..store.admin import (
    AdminSchemaUnavailable,
    AdminValidationError,
    get_admin_account,
    list_account_projects,
    list_admin_accounts,
    set_account_blocked,
    set_account_plan,
    set_project_credits,
    global_usage,
    operational_health,
    set_account_limits,
)
from ..store.sharing import add_admin_comment, get_shared_project, list_comments, list_shared_projects


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _current_admin():
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    return account


def _schema_error(error):
    abort(503, description=str(error))


@admin_bp.get("/")
@admin_required
def index():
    return redirect(url_for("admin.accounts"))


@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        account=_current_admin(),
    )


@admin_bp.get("/accounts")
@admin_required
def accounts():
    try:
        managed_accounts = list_admin_accounts()
    except AdminSchemaUnavailable as error:
        _schema_error(error)
    return render_template(
        "admin/accounts.html",
        account=_current_admin(),
        managed_accounts=managed_accounts,
    )


@admin_bp.post("/accounts/<account_id>/plan")
@admin_required
@require_csrf
def update_plan(account_id):
    try:
        updated = set_account_plan(account_id, request.form.get("plan_code", ""))
    except AdminSchemaUnavailable as error:
        _schema_error(error)
    except AdminValidationError as error:
        abort(400, description=str(error))
    if updated is None:
        abort(404)
    return redirect(url_for("admin.accounts", saved="plan"))


@admin_bp.post("/accounts/<account_id>/credits")
@admin_bp.post("/accounts/<account_id>/project-credits")
@admin_required
@require_csrf
def update_credits(account_id):
    raw_remaining = request.form.get("project_remaining", "")
    try:
        remaining = int(raw_remaining)
    except (TypeError, ValueError):
        abort(400, description="Os créditos de projeto devem ser um número inteiro.")
    try:
        updated = set_project_credits(account_id, remaining)
    except AdminSchemaUnavailable as error:
        _schema_error(error)
    except AdminValidationError as error:
        abort(400, description=str(error))
    if updated is None:
        abort(404)
    return redirect(url_for("admin.accounts", saved="credits"))


@admin_bp.post("/accounts/<account_id>/block")
@admin_required
@require_csrf
def update_block(account_id):
    raw_blocked = request.form.get("blocked")
    if raw_blocked not in {"0", "1"}:
        abort(400, description="O estado de bloqueio é inválido.")
    try:
        updated = set_account_blocked(
            account_id,
            raw_blocked == "1",
            actor_id=current_account_id(),
        )
    except AdminSchemaUnavailable as error:
        _schema_error(error)
    except AdminValidationError as error:
        abort(400, description=str(error))
    if updated is None:
        abort(404)
    return redirect(url_for("admin.accounts", saved="block"))


@admin_bp.get("/accounts/<account_id>/projects")
@admin_required
def account_projects(account_id):
    try:
        managed_account = get_admin_account(account_id)
        projects = list_account_projects(account_id)
    except AdminSchemaUnavailable as error:
        _schema_error(error)
    if managed_account is None or projects is None:
        abort(404)
    return render_template(
        "admin/account_projects.html",
        account=_current_admin(),
        managed_account=managed_account,
        projects=projects,
    )


@admin_bp.get("/projects")
@admin_required
def projects():
    return render_template(
        "admin/projects.html",
        account=_current_admin(),
        projects=list_shared_projects(),
    )


def _mask_email(email: str) -> str:
    """Mascarar email para LGPD - mostra apenas primeiro e último caractere do local-part."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


@admin_bp.get("/projects/<project_id>")
@admin_required
def project(project_id):
    row = get_shared_project(project_id)
    if row is None:
        abort(404)
    payload = json.loads(row["payload"] or "{}")
    payload.update({"id": row["id"], "project_type": row["project_type"], "title": row["title"], "revision": row["revision"]})
    return render_template(
        "admin/project.html",
        account=_current_admin(),
        project=payload,
        owner_email=_mask_email(row["email"]),
        allow_comments=bool(row["allow_admin_comments"]),
        comments=list_comments(project_id) if bool(row["allow_admin_comments"]) else [],
    )


@admin_bp.post("/projects/<project_id>/comments")
@admin_required
@require_csrf
def comment(project_id):
    if not add_admin_comment(project_id, current_account_id(), request.form.get("body", "")):
        abort(403)
    return redirect(url_for("admin.project", project_id=project_id))


# ──────────────────────────────────────────────
# Admin: Health, Usage Global, Limits
# ──────────────────────────────────────────────

@admin_bp.get("/health")
@admin_required
def health():
    try:
        health_data = operational_health()
    except AdminSchemaUnavailable as error:
        abort(503, description=str(error))
    return jsonify({"ok": True, "health": health_data})


@admin_bp.get("/usage")
@admin_required
def usage():
    try:
        usage_data = global_usage()
    except AdminSchemaUnavailable as error:
        abort(503, description=str(error))
    return jsonify({"ok": True, "usage": usage_data})


@admin_bp.post("/accounts/<account_id>/limits")
@admin_required
@require_csrf
def update_limits(account_id):
    body = request.get_json(silent=True) or {}
    try:
        updated = set_account_limits(account_id, body)
    except AdminSchemaUnavailable as error:
        abort(503, description=str(error))
    except AdminValidationError as error:
        return jsonify({"error": "validation_error", "message": str(error)}), 400
    if updated is None:
        abort(404)
    return jsonify({"ok": True, "account": updated})
