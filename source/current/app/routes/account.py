from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from ..auth import current_account_id, login_required, require_csrf
from ..store.accounts import (
    accept_terms,
    get_account,
    update_profile,
    get_account_sharing_preferences,
    set_account_sharing_preferences,
    get_effective_project_sharing,
    request_self_deletion,
    cancel_self_deletion,
    confirm_self_deletion,
    get_account_grants_summary,
    export_account_data,
)
from ..store.projects import list_projects, get_project
from ..store.sharing import get_sharing


account_bp = Blueprint("account", __name__)


@account_bp.get("/account/settings")
@login_required
def settings():
    account = get_account(current_account_id())
    if account is None:
        abort(401)
    return render_template("account/settings.html", account=account)


@account_bp.post("/account/settings/profile")
@login_required
@require_csrf
def save_profile():
    account_id = current_account_id()
    update_profile(
        account_id,
        {
            "city": request.form.get("city"),
            "disciplines": request.form.get("disciplines", "").splitlines(),
            "teachers": request.form.get("teachers", "").splitlines(),
            "institution": request.form.get("institution"),
            "course": request.form.get("course"),
            "discipline": request.form.get("discipline"),
            "professor": request.form.get("professor"),
        },
        request.form.get("name", ""),
    )
    return redirect(url_for("account.settings", saved="profile"))


@account_bp.post("/account/settings/terms")
@login_required
@require_csrf
def save_terms():
    if request.form.get("accept") != "on":
        abort(400, description="É necessário aceitar os termos para continuar.")
    try:
        accept_terms(
            current_account_id(),
            request.form.get("accept") == "on",
            request.form.get("ai_consent") == "on",
        )
    except ValueError as error:
        abort(400, description=str(error))
    return redirect(url_for("account.settings", saved="terms"))


# ──────────────────────────────────────────────
# Sharing Preferences (Account Level + Inheritance)
# ──────────────────────────────────────────────

@account_bp.get("/account/sharing")
@login_required
def sharing_preferences():
    account_id = current_account_id()
    prefs = get_account_sharing_preferences(account_id)
    return jsonify({"ok": True, "preferences": prefs})


@account_bp.post("/account/sharing")
@login_required
@require_csrf
def save_sharing_preferences():
    account_id = current_account_id()
    body = request.get_json(silent=True) or {}
    try:
        prefs = set_account_sharing_preferences(account_id, body)
    except ValueError as error:
        return jsonify({"error": "invalid_sharing_preferences", "message": str(error)}), 400
    return jsonify({"ok": True, "preferences": prefs})


@account_bp.get("/account/projects/<project_id>/sharing/effective")
@login_required
def effective_project_sharing(project_id):
    account_id = current_account_id()
    project = get_project(account_id, project_id)
    if project is None:
        abort(404)
    effective = get_effective_project_sharing(account_id, project_id)
    project_sharing = get_sharing(account_id, project_id)
    return jsonify({
        "ok": True,
        "effective": effective,
        "project_override": project_sharing,
    })


# ──────────────────────────────────────────────
# Self Deletion (Auto-exclusão pelo próprio usuário)
# ──────────────────────────────────────────────

@account_bp.post("/account/deletion/request")
@login_required
@require_csrf
def request_deletion():
    account_id = current_account_id()
    try:
        result = request_self_deletion(account_id)
    except ValueError as error:
        return jsonify({"error": "deletion_request_failed", "message": str(error)}), 400
    return jsonify({"ok": True, **result})


@account_bp.post("/account/deletion/cancel")
@login_required
@require_csrf
def cancel_deletion():
    account_id = current_account_id()
    result = cancel_self_deletion(account_id)
    return jsonify({"ok": True, **result})


@account_bp.post("/account/deletion/confirm")
@login_required
@require_csrf
def confirm_deletion():
    account_id = current_account_id()
    try:
        result = confirm_self_deletion(account_id)
    except ValueError as error:
        return jsonify({"error": "deletion_failed", "message": str(error)}), 400
    # A conta foi deletada - a sessão será invalidada
    return jsonify({"ok": True, **result})


# ──────────────────────────────────────────────
# Account Grants Summary
# ──────────────────────────────────────────────

@account_bp.get("/account/grants")
@login_required
def account_grants():
    account_id = current_account_id()
    summary = get_account_grants_summary(account_id)
    return jsonify({"ok": True, **summary})


# ──────────────────────────────────────────────
# Account Data Export (LGPD/GDPR)
# ──────────────────────────────────────────────

@account_bp.get("/account/export")
@login_required
def export_data():
    account_id = current_account_id()
    try:
        data = export_account_data(account_id)
    except ValueError as error:
        return jsonify({"error": "export_failed", "message": str(error)}), 400
    from flask import Response
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="assistente-academico-export-{account_id}.json"',
        },
    )
