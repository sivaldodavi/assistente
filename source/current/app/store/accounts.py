import json
import time
from uuid import uuid4

from flask import current_app

from .db import get_db
from ..config import PLAN_CODES, PLAN_LABELS, MAX_ACCOUNT_LIMIT


def upsert_google_account(claims: dict) -> str:
    subject = str(claims.get("sub") or "").strip()[:255]
    email = str(claims.get("email") or "").strip().lower()[:240]
    name = str(claims.get("name") or "").strip()[:160]
    if not subject or not email:
        raise ValueError("claims Google incompletos")
    database = get_db()
    row = database.execute("SELECT id FROM accounts WHERE google_sub = ? OR email = ?", (subject, email)).fetchone()
    now = int(time.time())
    if row is None:
        account_id = str(uuid4())
        database.execute(
            "INSERT INTO accounts (id, google_sub, email, name, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, subject, email, name, now, now),
        )
    else:
        account_id = row["id"]
        database.execute(
            "UPDATE accounts SET google_sub = ?, email = ?, name = ?, last_login = ? WHERE id = ?",
            (subject, email, name, now, account_id),
        )
    database.commit()
    return account_id


def get_account(account_id: str) -> dict | None:
    row = get_db().execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        return None
    try:
        profile = json.loads(row["profile_json"] or "{}")
    except json.JSONDecodeError:
        profile = {}
    is_admin = row["email"].lower() in current_app.config.get("ADMIN_EMAILS", set())
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "profile": profile if isinstance(profile, dict) else {},
        "terms_accepted": bool(row["terms_accepted"]),
        "terms_version": row["terms_version"],
        "ai_consent": bool(row["ai_consent"]),
        "is_blocked": bool(row["is_blocked"]),
        "is_admin": is_admin,
        "plan_code": row["plan_code"] or "livre",
        "project_limit": int(row["project_limit"] or 0),
        "project_used": int(row["project_used"] or 0),
        "ai_limit": int(row["ai_limit"] or 0),
        "ai_used": int(row["ai_used"] or 0),
        "project_remaining": None if is_admin else max(0, int(row["project_limit"] or 0) - int(row["project_used"] or 0)),
        "ai_remaining": None if is_admin else max(0, int(row["ai_limit"] or 0) - int(row["ai_used"] or 0)),
        "unlimited": is_admin,
        # Novos campos v12
        "sharing_preferences_version": int(row["sharing_preferences_version"] or 1),
        "sharing_allow_admin_view": bool(row["sharing_allow_admin_view"]),
        "sharing_allow_admin_comments": bool(row["sharing_allow_admin_comments"]),
        "sharing_inherit_default": bool(row["sharing_inherit_default"]),
        "deletion_request_pending": bool(row["deletion_request_pending"]),
        "ai_analysis_limit": int(row["ai_analysis_limit"] or 0),
        "deepseek_explanation_limit": int(row["deepseek_explanation_limit"] or 0),
    }


def update_profile(account_id: str, profile: dict, name: str) -> dict:
    clean = {
        "city": str(profile.get("city") or "").strip()[:160],
        "disciplines": list(dict.fromkeys(str(value).strip()[:160] for value in profile.get("disciplines", []) if str(value).strip()))[:40],
        "teachers": list(dict.fromkeys(str(value).strip()[:160] for value in profile.get("teachers", []) if str(value).strip()))[:40],
        "institution": str(profile.get("institution") or "").strip()[:160],
        "course": str(profile.get("course") or "").strip()[:160],
        "discipline": str(profile.get("discipline") or "").strip()[:160],
        "professor": str(profile.get("professor") or "").strip()[:160],
    }
    get_db().execute(
        "UPDATE accounts SET name = ?, profile_json = ? WHERE id = ?",
        (str(name or "").strip()[:160], json.dumps(clean, ensure_ascii=False), account_id),
    )
    get_db().commit()
    return get_account(account_id)


def accept_terms(account_id: str, accept: bool, ai_consent: bool) -> dict:
    if not accept:
        raise ValueError("os termos precisam ser aceitos")
    now = int(time.time())
    get_db().execute(
        """UPDATE accounts SET terms_accepted = 1, terms_version = ?, terms_accepted_at = ?, ai_consent = ?
           WHERE id = ?""",
        ("2026-10", now, int(bool(ai_consent)), account_id),
    )
    get_db().commit()
    return get_account(account_id)


# ──────────────────────────────────────────────
# Sharing Preferences v2 (com herança)
# ──────────────────────────────────────────────
def get_account_sharing_preferences(account_id: str) -> dict:
    """Retorna preferências de compartilhamento no nível da conta."""
    row = get_db().execute(
        "SELECT sharing_preferences_version, sharing_allow_admin_view, sharing_allow_admin_comments, sharing_inherit_default "
        "FROM accounts WHERE id = ?",
        (account_id,),
    ).fetchone()
    if row is None:
        return {
            "version": 1,
            "allow_admin_view": False,
            "allow_admin_comments": False,
            "inherit_default": True,
        }
    return {
        "version": int(row["sharing_preferences_version"] or 1),
        "allow_admin_view": bool(row["sharing_allow_admin_view"]),
        "allow_admin_comments": bool(row["sharing_allow_admin_comments"]),
        "inherit_default": bool(row["sharing_inherit_default"]),
    }


def set_account_sharing_preferences(account_id: str, payload: dict) -> dict:
    """Atualiza preferências de compartilhamento no nível da conta.

    Regras de validação:
    - allow_admin_comments requer allow_admin_view
    - version é incrementado a cada mudança
    """
    allow_view = bool(payload.get("allow_admin_view", False))
    allow_comments = bool(payload.get("allow_admin_comments", False))
    inherit_default = bool(payload.get("inherit_account_default", True))

    if allow_comments and not allow_view:
        raise ValueError("Comentários administrativos requerem visualização administrativa.")

    now = int(time.time())
    get_db().execute(
        """UPDATE accounts
           SET sharing_allow_admin_view = ?, sharing_allow_admin_comments = ?,
               sharing_inherit_default = ?, sharing_preferences_version = sharing_preferences_version + 1
           WHERE id = ?""",
        (int(allow_view), int(allow_comments), int(inherit_default), account_id),
    )
    get_db().commit()
    return get_account_sharing_preferences(account_id)


def get_effective_project_sharing(account_id: str, project_id: str) -> dict:
    """Calcula permissões efetivas do projeto (override vs herança da conta)."""
    from .sharing import get_sharing
    project_sharing = get_sharing(account_id, project_id)
    account_prefs = get_account_sharing_preferences(account_id)

    if project_sharing.get("inherit_account_default", True):
        # Herda da conta
        return {
            "allow_admin_view": account_prefs["allow_admin_view"],
            "allow_admin_comments": account_prefs["allow_admin_comments"],
            "inherited": True,
        }
    else:
        # Override no projeto
        return {
            "allow_admin_view": project_sharing["allow_admin_view"],
            "allow_admin_comments": project_sharing["allow_admin_comments"],
            "inherited": False,
        }


# ──────────────────────────────────────────────
# Deletion Request (auto-exclusão pelo próprio usuário)
# ──────────────────────────────────────────────
def request_self_deletion(account_id: str) -> dict:
    """Usuário solicita exclusão da própria conta."""
    now = int(time.time())
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    # Verifica se já existe pedido pendente
    existing = db.execute(
        "SELECT status FROM deletion_requests WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    if existing and existing["status"] == "pending":
        db.rollback()
        raise ValueError("Já existe uma solicitação de exclusão pendente.")

    # Cria pedido de exclusão
    db.execute(
        """INSERT INTO deletion_requests (account_id, requested_by, status, created_at)
           VALUES (?, ?, 'pending', ?)""",
        (account_id, account_id, now),
    )
    # Marca conta como com pedido pendente
    db.execute(
        "UPDATE accounts SET deletion_request_pending = 1 WHERE id = ?",
        (account_id,),
    )
    db.commit()
    return {"status": "pending", "created_at": now}


def cancel_self_deletion(account_id: str) -> dict:
    """Usuário cancela sua própria solicitação de exclusão."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    db.execute(
        "DELETE FROM deletion_requests WHERE account_id = ? AND status = 'pending'",
        (account_id,),
    )
    db.execute(
        "UPDATE accounts SET deletion_request_pending = 0 WHERE id = ?",
        (account_id,),
    )
    db.commit()
    return {"status": "cancelled"}


def confirm_self_deletion(account_id: str) -> dict:
    """Usuário confirma exclusão - deleta tudo em cascata."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    # Atualiza status do pedido
    db.execute(
        "UPDATE deletion_requests SET status = 'accepted', resolved_at = ? WHERE account_id = ? AND status = 'pending'",
        (int(time.time()), account_id),
    )
    # Deleta a conta (cascata via FK)
    db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    db.commit()
    return {"status": "accepted", "executed": True}


# ──────────────────────────────────────────────
# Account Grants (Ledger de créditos)
# ──────────────────────────────────────────────
def create_account_grant(
    account_id: str,
    plan_code: str,
    project_credits: int = 0,
    ai_analysis_credits: int = 0,
    deepseek_explanation_credits: int = 0,
    expires_at: int | None = None,
) -> str:
    """Cria grant de créditos para a conta."""
    grant_id = str(uuid4())
    now = int(time.time())
    get_db().execute(
        """INSERT INTO account_grants
           (grant_id, account_id, plan_code, project_credits, project_consumed,
            ai_analysis_credits, ai_analysis_consumed,
            deepseek_explanation_credits, deepseek_explanation_consumed,
            created_at, expires_at)
           VALUES (?, ?, ?, ?, 0, ?, 0, ?, 0, ?, ?)""",
        (grant_id, account_id, plan_code, project_credits, ai_analysis_credits,
         deepseek_explanation_credits, now, expires_at),
    )
    get_db().commit()
    return grant_id


def consume_project_credit(account_id: str) -> bool:
    """Consome 1 crédito de projeto do grant mais antigo com saldo."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        """SELECT grant_id, project_credits, project_consumed
           FROM account_grants
           WHERE account_id = ? AND project_consumed < project_credits
           ORDER BY created_at ASC
           LIMIT 1""",
        (account_id,),
    ).fetchone()
    if row is None:
        db.rollback()
        return False
    db.execute(
        "UPDATE account_grants SET project_consumed = project_consumed + 1 WHERE grant_id = ?",
        (row["grant_id"],),
    )
    db.commit()
    return True


def refund_project_credit(account_id: str) -> bool:
    """Devolve 1 crédito de projeto (usado ao deletar projeto)."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        """SELECT grant_id, project_consumed
           FROM account_grants
           WHERE account_id = ? AND project_consumed > 0
           ORDER BY created_at DESC
           LIMIT 1""",
        (account_id,),
    ).fetchone()
    if row is None:
        db.rollback()
        return False
    db.execute(
        "UPDATE account_grants SET project_consumed = project_consumed - 1 WHERE grant_id = ?",
        (row["grant_id"],),
    )
    db.commit()
    return True


def get_account_grants_summary(account_id: str) -> dict:
    """Retorna resumo de grants da conta."""
    rows = get_db().execute(
        """SELECT grant_id, plan_code, project_credits, project_consumed,
                  ai_analysis_credits, ai_analysis_consumed,
                  deepseek_explanation_credits, deepseek_explanation_consumed,
                  created_at, expires_at
           FROM account_grants WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()
    grants = []
    for row in rows:
        grants.append({
            "grant_id": row["grant_id"],
            "plan_code": row["plan_code"],
            "project_credits": row["project_credits"],
            "project_consumed": row["project_consumed"],
            "project_remaining": row["project_credits"] - row["project_consumed"],
            "ai_analysis_credits": row["ai_analysis_credits"],
            "ai_analysis_consumed": row["ai_analysis_consumed"],
            "ai_analysis_remaining": row["ai_analysis_credits"] - row["ai_analysis_consumed"],
            "deepseek_explanation_credits": row["deepseek_explanation_credits"],
            "deepseek_explanation_consumed": row["deepseek_explanation_consumed"],
            "deepseek_explanation_remaining": row["deepseek_explanation_credits"] - row["deepseek_explanation_consumed"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        })
    return {"grants": grants}


# ──────────────────────────────────────────────
# Account Export (LGPD)
# ──────────────────────────────────────────────
def export_account_data(account_id: str) -> dict:
    """Exporta todos os dados da conta para LGPD/GDPR."""
    from .projects import list_projects, get_project
    from .sharing import list_comments
    from .sources import list_sources
    from .ai_usage import get_db as get_ai_db

    account = get_account(account_id)
    if not account:
        raise ValueError("Conta não encontrada")

    projects_data = []
    for project in list_projects(account_id):
        full_project = get_project(account_id, project["id"])
        if full_project:
            projects_data.append(full_project)

    # Revisions
    revisions = []
    for project in list_projects(account_id):
        rev_rows = get_db().execute(
            """SELECT snapshot_id, revision, title, project_type, payload, created_at
               FROM project_revisions WHERE project_id = ? ORDER BY revision DESC""",
            (project["id"],),
        ).fetchall()
        for rev in rev_rows:
            try:
                payload = json.loads(rev["payload"])
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            revisions.append({
                "project_id": project["id"],
                "snapshot_id": rev["snapshot_id"],
                "revision": rev["revision"],
                "title": rev["title"],
                "project_type": rev["project_type"],
                "payload": payload,
                "created_at": rev["created_at"],
            })

    # Comments received (as owner)
    comments = []
    for project in list_projects(account_id):
        proj_comments = list_comments(project["id"])
        for c in proj_comments:
            c["project_id"] = project["id"]
            comments.append(c)

    # Sources
    sources_data = list_sources(account_id)

    # AI Usage
    ai_usage = get_ai_db().execute(
        """SELECT request_id, action, units, status, created_at, updated_at
           FROM ai_usage_reservations WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()

    provider_usage = get_ai_db().execute(
        """SELECT request_id, provider, operation, model, input_tokens, output_tokens, status, created_at
           FROM provider_usage WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()

    return {
        "account": account,
        "projects": projects_data,
        "revisions": revisions,
        "comments": comments,
        "sources": sources_data,
        "ai_usage_reservations": [dict(r) for r in ai_usage],
        "provider_usage": [dict(r) for r in provider_usage],
        "exported_at": int(time.time()),
    }
