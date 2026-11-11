from functools import wraps
from hmac import compare_digest
from secrets import token_urlsafe

from flask import abort, current_app, redirect, request, session, url_for


def current_account_id():
    return session.get("account_id")


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = token_urlsafe(32)
        session["csrf_token"] = token
    return token


def require_csrf(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or not supplied or not compare_digest(expected, supplied):
            abort(400, description="A sessão expirou. Atualize a página e tente novamente.")
        return view(*args, **kwargs)
    return wrapped


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_account_id():
            return redirect(url_for("public.home", login="required"))
        from .store.accounts import get_account
        account = get_account(current_account_id())
        if account is None or account.get("is_blocked"):
            session.clear()
            abort(403, description="Esta conta está impedida de acessar o sistema.")
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_account_id():
            return redirect(url_for("public.home", login="required"))
        from .store.accounts import get_account
        account = get_account(current_account_id())
        if not account or account.get("is_blocked") or not account.get("is_admin"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped
