"""Exportação completa de dados da conta (LGPD/GDPR)."""

from __future__ import annotations

import json
import time
from typing import Any

from .db import get_db
from .projects import list_projects, get_project
from .sources import list_sources
from .sharing import list_comments
from .revisions import list_revisions


def export_account_data(account_id: str) -> dict[str, Any]:
    """Exporta todos os dados da conta para LGPD/GDPR."""
    from .accounts import get_account

    account = get_account(account_id)
    if not account:
        raise ValueError("Conta não encontrada")

    # Projetos completos
    projects_data = []
    for project in list_projects(account_id):
        full_project = get_project(account_id, project["id"])
        if full_project:
            projects_data.append(full_project)

    # Revisões
    revisions = []
    for project in list_projects(account_id):
        rev_list = list_revisions(project["id"], account_id)
        for rev in rev_list:
            revisions.append({
                "project_id": project["id"],
                "snapshot_id": rev["snapshot_id"],
                "revision": rev["revision"],
                "title": rev["title"],
                "project_type": rev["project_type"],
                "payload": rev["payload"],
                "created_at": rev["created_at"],
            })

    # Comentários recebidos (como proprietário dos projetos)
    comments = []
    for project in list_projects(account_id):
        proj_comments = list_comments(project["id"])
        for c in proj_comments:
            c = dict(c)
            c["project_id"] = project["id"]
            comments.append(c)

    # Fontes da biblioteca
    sources_data = list_sources(account_id)

    # Uso de IA - reservas
    ai_usage = get_db().execute(
        """SELECT request_id, action, units, status, created_at, updated_at
           FROM ai_usage_reservations WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()

    # Uso de IA - provedores
    provider_usage = get_db().execute(
        """SELECT request_id, provider, operation, model, input_tokens, output_tokens, status, created_at
           FROM provider_usage WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()

    # Grants
    grants = get_db().execute(
        """SELECT grant_id, plan_code, project_credits, project_consumed,
                  ai_analysis_credits, ai_analysis_consumed,
                  deepseek_explanation_credits, deepseek_explanation_consumed,
                  created_at, expires_at
           FROM account_grants WHERE account_id = ? ORDER BY created_at DESC""",
        (account_id,),
    ).fetchall()

    # Sessões
    sessions = get_db().execute(
        "SELECT id, created_at, expires_at FROM sessions WHERE account_id = ? ORDER BY created_at DESC",
        (account_id,),
    ).fetchall()

    # Pedido de exclusão
    deletion_request = get_db().execute(
        "SELECT status, created_at, resolved_at FROM deletion_requests WHERE account_id = ?",
        (account_id,),
    ).fetchone()

    # Preferências de compartilhamento
    sharing_prefs = get_db().execute(
        """SELECT sharing_preferences_version, sharing_allow_admin_view,
                  sharing_allow_admin_comments, sharing_inherit_default
           FROM accounts WHERE id = ?""",
        (account_id,),
    ).fetchone()

    return {
        "account": {
            **account,
            "sharing_preferences": dict(sharing_prefs) if sharing_prefs else {},
            "deletion_request": dict(deletion_request) if deletion_request else None,
        },
        "projects": projects_data,
        "revisions": revisions,
        "comments": comments,
        "sources": sources_data,
        "ai_usage_reservations": [dict(r) for r in ai_usage],
        "provider_usage": [dict(r) for r in provider_usage],
        "grants": [dict(r) for r in grants],
        "sessions": [dict(r) for r in sessions],
        "exported_at": int(time.time()),
    }