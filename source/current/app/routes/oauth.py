import secrets

from flask import Blueprint, current_app, redirect, request, session, url_for

from ..auth import csrf_token
from ..services.google_oauth import (
    GoogleOAuthClient,
    GoogleOAuthConfig,
    GoogleOAuthError,
    new_code_verifier,
    new_nonce,
    new_state,
)
from ..store.accounts import upsert_google_account


oauth_bp = Blueprint("oauth", __name__)


def _client():
    return GoogleOAuthClient(GoogleOAuthConfig.from_mapping(current_app.config))


@oauth_bp.get("/oauth/google/start")
def google_start():
    client = _client()
    if not client.config.configured:
        return redirect(url_for("public.home", google_login="unconfigured"))
    state = new_state()
    nonce = new_nonce()
    code_verifier = new_code_verifier()
    session["google_oauth"] = {"state": state, "nonce": nonce, "code_verifier": code_verifier}
    try:
        location = client.authorization_url(state, nonce, code_verifier)
    except GoogleOAuthError as error:
        current_app.logger.warning("google_oauth_start_failed code=%s", str(error))
        session.pop("google_oauth", None)
        return redirect(url_for("public.home", google_login="failed"))
    return redirect(location)


@oauth_bp.get("/oauth/google/callback")
def google_callback():
    flow = session.pop("google_oauth", None)
    state = request.args.get("state", "")
    code = request.args.get("code", "")
    if (
        not isinstance(flow, dict)
        or not isinstance(state, str)
        or not state
        or not secrets.compare_digest(state, str(flow.get("state", "")))
        or request.args.get("error")
        or not isinstance(code, str)
        or not code
        or len(code) > 2048
    ):
        return redirect(url_for("public.home", google_login="failed"))
    try:
        claims = _client().exchange_code(code, str(flow["code_verifier"]), str(flow["nonce"]))
        account_id = upsert_google_account(claims)
        from ..store.accounts import get_account
        if get_account(account_id).get("is_blocked"):
            raise GoogleOAuthError("account_blocked")
    except (GoogleOAuthError, KeyError, TypeError, ValueError) as error:
        code = str(error) if isinstance(error, GoogleOAuthError) else type(error).__name__
        current_app.logger.warning("google_oauth_callback_failed code=%s", code)
        return redirect(url_for("public.home", google_login="failed"))
    session.clear()
    session["account_id"] = account_id
    csrf_token()
    return redirect(url_for("projects.account"))
