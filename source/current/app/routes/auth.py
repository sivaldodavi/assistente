from uuid import uuid4

from flask import Blueprint, abort, current_app, redirect, request, session, url_for

from ..auth import csrf_token, require_csrf
from ..store.db import get_db


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/dev-login")
def dev_login():
    if not current_app.config["ALLOW_DEV_AUTH"]:
        abort(404)
    email = (request.form.get("email") or "dev@example.test").strip().lower()[:240]
    name = (request.form.get("name") or "Conta de teste").strip()[:160]
    account_id = get_db().execute("SELECT id FROM accounts WHERE email = ?", (email,)).fetchone()
    if account_id is None:
        account_id = str(uuid4())
        if current_app.testing:
            get_db().execute(
                "INSERT INTO accounts (id, email, name, project_limit, ai_limit, created_at) VALUES (?, ?, ?, 100, 100, strftime('%s','now'))",
                (account_id, email, name),
            )
        else:
            get_db().execute(
                "INSERT INTO accounts (id, email, name, created_at) VALUES (?, ?, ?, strftime('%s','now'))",
                (account_id, email, name),
            )
        get_db().commit()
    resolved_account_id = account_id if isinstance(account_id, str) else account_id["id"]
    from ..store.accounts import get_account
    if get_account(resolved_account_id).get("is_blocked"):
        session.clear()
        abort(403, description="Esta conta está impedida de acessar o sistema.")
    session.clear()
    session["account_id"] = resolved_account_id
    csrf_token()
    return redirect(url_for("projects.account"))


@auth_bp.post("/logout")
@require_csrf
def logout():
    session.clear()
    return redirect(url_for("public.home"))
