"""Operações administrativas manuais.

O módulo depende de uma extensão aditiva da tabela ``accounts`` que é aplicada
pelo schema/migração da aplicação. Nenhuma operação aqui concede plano por
pagamento nem devolve o payload de projetos privados.
"""
from __future__ import annotations

import time
import shutil
from dataclasses import dataclass
from typing import Any

from flask import current_app

from .db import get_db


PLAN_CODES = ("livre", "avulso_ai", "sem_ia", "com_ia")
PLAN_LABELS = {
    "livre": "Sem plano",
    "avulso_ai": "Avulso com IA",
    "sem_ia": "Plano sem IA",
    "com_ia": "Plano com IA",
}
MAX_ACCOUNT_LIMIT = 1000

# These are deliberately explicit: the parent migration must add exactly these
# administrative fields (with compatible integer/text types and safe defaults).
REQUIRED_ACCOUNT_COLUMNS = (
    "plan_code",
    "project_limit",
    "project_used",
    "ai_limit",
    "ai_used",
    "is_blocked",
    "ai_analysis_limit",
    "deepseek_explanation_limit",
)


class AdminSchemaUnavailable(RuntimeError):
    """Raised when the parent application has not applied the admin migration."""

    def __init__(self, missing: set[str]):
        self.missing = tuple(sorted(missing))
        super().__init__(
            "A migração administrativa ainda não foi aplicada; faltam: "
            + ", ".join(self.missing)
        )


@dataclass(frozen=True)
class AdminValidationError(ValueError):
    """An input that an administrator must correct before retrying."""

    message: str

    def __str__(self) -> str:
        return self.message


def _account_columns() -> set[str]:
    return {row["name"] for row in get_db().execute("PRAGMA table_info(accounts)").fetchall()}


def _require_admin_schema() -> None:
    missing = set(REQUIRED_ACCOUNT_COLUMNS) - _account_columns()
    if missing:
        raise AdminSchemaUnavailable(missing)


def _is_admin_email(email: str) -> bool:
    return str(email or "").strip().lower() in current_app.config.get("ADMIN_EMAILS", set())


def _account_dict(row: Any) -> dict[str, Any]:
    project_used = max(0, int(row["project_used"] or 0))
    project_limit = max(0, int(row["project_limit"] or 0))
    ai_used = max(0, int(row["ai_used"] or 0))
    ai_limit = max(0, int(row["ai_limit"] or 0))
    plan_code = row["plan_code"] if row["plan_code"] in PLAN_CODES else "livre"
    is_admin = _is_admin_email(row["email"])
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "plan_code": plan_code,
        "plan_label": PLAN_LABELS[plan_code],
        "project_limit": project_limit,
        "project_used": project_used,
        "project_remaining": None if is_admin else max(0, project_limit - project_used),
        "ai_limit": ai_limit,
        "ai_used": ai_used,
        "ai_remaining": None if is_admin else max(0, ai_limit - ai_used),
        "is_blocked": bool(row["is_blocked"]),
        "is_admin": is_admin,
        "unlimited": is_admin,
        "project_count": int(row["project_count"] or 0),
        "created_at": row["created_at"],
        "last_login": row["last_login"],
        # Novos campos v12
        "ai_analysis_limit": int(row["ai_analysis_limit"] or 0),
        "deepseek_explanation_limit": int(row["deepseek_explanation_limit"] or 0),
    }


def list_admin_accounts() -> list[dict[str, Any]]:
    """Return account balances and identity metadata, never project payloads."""
    _require_admin_schema()
    rows = get_db().execute(
        """SELECT a.id, a.email, a.name, a.plan_code,
                  a.project_limit, a.project_used, a.ai_limit, a.ai_used,
                  a.is_blocked, a.created_at, a.last_login,
                  a.ai_analysis_limit, a.deepseek_explanation_limit,
                  COUNT(p.id) AS project_count
           FROM accounts AS a
           LEFT JOIN projects AS p ON p.account_id = a.id
           GROUP BY a.id, a.email, a.name, a.plan_code,
                    a.project_limit, a.project_used, a.ai_limit, a.ai_used,
                    a.is_blocked, a.created_at, a.last_login,
                    a.ai_analysis_limit, a.deepseek_explanation_limit
           ORDER BY a.created_at ASC, a.email ASC"""
    ).fetchall()
    return [_account_dict(row) for row in rows]


def get_admin_account(account_id: str) -> dict[str, Any] | None:
    _require_admin_schema()
    row = get_db().execute(
        """SELECT a.id, a.email, a.name, a.plan_code,
                  a.project_limit, a.project_used, a.ai_limit, a.ai_used,
                  a.is_blocked, a.created_at, a.last_login,
                  a.ai_analysis_limit, a.deepseek_explanation_limit,
                  (SELECT COUNT(*) FROM projects p WHERE p.account_id = a.id) AS project_count
           FROM accounts a WHERE a.id = ?""",
        (account_id,),
    ).fetchone()
    return _account_dict(row) if row else None


def set_account_plan(account_id: str, plan_code: str) -> dict[str, Any]:
    """Change only the manually displayed plan badge; do not change balances."""
    _require_admin_schema()
    if not isinstance(plan_code, str) or plan_code not in PLAN_CODES:
        raise AdminValidationError("Plano inválido.")
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    row = database.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        database.rollback()
        return None
    database.execute("UPDATE accounts SET plan_code = ? WHERE id = ?", (plan_code, account_id))
    database.commit()
    return get_admin_account(account_id)


def set_project_credits(account_id: str, project_remaining: int) -> dict[str, Any]:
    """Set available project credits independently of the plan badge."""
    _require_admin_schema()
    if (
        isinstance(project_remaining, bool)
        or not isinstance(project_remaining, int)
        or not 0 <= project_remaining <= MAX_ACCOUNT_LIMIT
    ):
        raise AdminValidationError(
            f"Os créditos de projeto devem ser um inteiro entre 0 e {MAX_ACCOUNT_LIMIT}."
        )
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    row = database.execute(
        "SELECT project_used FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if row is None:
        database.rollback()
        return None
    project_used = max(0, int(row["project_used"] or 0))
    if project_used + project_remaining > MAX_ACCOUNT_LIMIT:
        database.rollback()
        raise AdminValidationError(
            f"O total concedido não pode ultrapassar {MAX_ACCOUNT_LIMIT} projetos."
        )
    database.execute(
        "UPDATE accounts SET project_limit = ? WHERE id = ?",
        (project_used + project_remaining, account_id),
    )
    database.commit()
    return get_admin_account(account_id)


def set_account_blocked(account_id: str, blocked: bool, actor_id: str | None = None) -> dict[str, Any]:
    """Set a manual block flag, protecting the current administrator from lockout."""
    _require_admin_schema()
    if type(blocked) is not bool:
        raise AdminValidationError("O estado de bloqueio é inválido.")
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    row = database.execute(
        """SELECT id, email, is_blocked
           FROM accounts WHERE id = ?""",
        (account_id,),
    ).fetchone()
    if row is None:
        database.rollback()
        return None
    if actor_id and actor_id == account_id:
        database.rollback()
        raise AdminValidationError("A conta administrativa atual não pode bloquear a própria sessão.")
    if blocked and _is_admin_email(row["email"]):
        admin_count = database.execute(
            "SELECT COUNT(*) FROM accounts WHERE lower(email) IN ({})".format(
                ",".join("?" for _ in current_app.config.get("ADMIN_EMAILS", set()))
            ),
            tuple(sorted(current_app.config.get("ADMIN_EMAILS", set()))),
        ).fetchone()[0] if current_app.config.get("ADMIN_EMAILS", set()) else 0
        if admin_count <= 1:
            database.rollback()
            raise AdminValidationError("Não bloqueie a única conta administradora configurada.")
    database.execute(
        "UPDATE accounts SET is_blocked = ? WHERE id = ?", (int(blocked), account_id)
    )
    database.commit()
    return get_admin_account(account_id)


def list_account_projects(account_id: str) -> list[dict[str, Any]] | None:
    """List safe project metadata; private payloads never leave the database."""
    _require_admin_schema()
    if get_db().execute("SELECT 1 FROM accounts WHERE id = ?", (account_id,)).fetchone() is None:
        return None
    rows = get_db().execute(
        """SELECT p.id, p.title, p.project_type, p.created_at, p.updated_at,
                  COALESCE(s.allow_admin_view, 0) AS allow_admin_view,
                  COALESCE(s.allow_admin_comments, 0) AS allow_admin_comments
           FROM projects p
           LEFT JOIN project_sharing s ON s.project_id = p.id AND s.account_id = p.account_id
           WHERE p.account_id = ?
           ORDER BY p.updated_at DESC, p.created_at DESC""",
        (account_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "project_type": row["project_type"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "allow_admin_view": bool(row["allow_admin_view"]),
            "allow_admin_comments": bool(row["allow_admin_view"] and row["allow_admin_comments"]),
        }
        for row in rows
    ]


# ──────────────────────────────────────────────
# Admin: Health, Usage Global, Limits
# ──────────────────────────────────────────────

def global_usage() -> dict[str, Any]:
    """Retorna estatísticas globais de uso de IA (DeepSeek + JEV/Typesafe)."""
    db = get_db()
    # Usage reservations
    usage_stats = db.execute(
        """SELECT
            COUNT(*) as total_reservations,
            SUM(CASE WHEN status = 'complete' THEN units ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'refunded' THEN units ELSE 0 END) as refunded,
            SUM(CASE WHEN status = 'reserved' THEN units ELSE 0 END) as reserved
           FROM ai_usage_reservations"""
    ).fetchone()

    # Provider usage
    provider_stats = db.execute(
        """SELECT provider, operation, COUNT(*) as calls,
                  SUM(input_tokens) as total_input_tokens,
                  SUM(output_tokens) as total_output_tokens
           FROM provider_usage
           GROUP BY provider, operation"""
    ).fetchall()

    # DeepSeek usage
    deepseek_stats = db.execute(
        """SELECT COUNT(*) as calls,
                  SUM(input_tokens) as total_input_tokens,
                  SUM(output_tokens) as total_output_tokens,
                  SUM(estimated_cost_usd) as total_cost
           FROM deepseek_usage"""
    ).fetchone()

    return {
        "reservations": dict(usage_stats) if usage_stats else {},
        "by_provider": [dict(row) for row in provider_stats],
        "deepseek": dict(deepseek_stats) if deepseek_stats else {},
    }


def operational_health() -> dict[str, Any]:
    """Retorna health check operacional do sistema."""
    db = get_db()

    # DB integrity
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]

    # Notification queue stats
    notif_stats = db.execute(
        """SELECT status, COUNT(*) as count
           FROM notification_outbox
           GROUP BY status"""
    ).fetchall()

    # Active sessions (last 24h)
    now = int(time.time())
    day_ago = now - 86400
    active_sessions = db.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE expires_at > ?", (day_ago,)
    ).fetchone()

    # Disk usage
    usage = shutil.disk_usage("/")
    disk = {
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "used_percent": round((usage.total - usage.free) / usage.total * 100, 1) if usage.total else 0,
    }

    # Database size
    db_path = current_app.config.get("DATABASE", "")
    db_size = 0
    if db_path:
        from pathlib import Path
        for path in (Path(db_path), Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")):
            if path.exists():
                db_size += path.stat().st_size

    return {
        "database": {
            "integrity": integrity,
            "notifications": {row["status"]: row["count"] for row in notif_stats},
            "size_bytes": db_size,
        },
        "active_sessions_24h": active_sessions["count"] if active_sessions else 0,
        "disk": disk,
    }


def set_account_limits(account_id: str, payload: dict) -> dict[str, Any] | None:
    """Admin define limites customizados da conta."""
    _require_admin_schema()
    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    row = db.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        db.rollback()
        return None

    # Validação dos limites
    ai_analysis_limit = payload.get("ai_analysis_limit")
    deepseek_explanation_limit = payload.get("deepseek_explanation_limit")
    is_admin = payload.get("is_admin")

    if ai_analysis_limit is not None:
        if not isinstance(ai_analysis_limit, int) or not (0 <= ai_analysis_limit <= MAX_ACCOUNT_LIMIT):
            db.rollback()
            raise AdminValidationError(f"Limite de análise IA deve ser inteiro entre 0 e {MAX_ACCOUNT_LIMIT}.")
        db.execute("UPDATE accounts SET ai_analysis_limit = ? WHERE id = ?", (ai_analysis_limit, account_id))

    if deepseek_explanation_limit is not None:
        if not isinstance(deepseek_explanation_limit, int) or not (0 <= deepseek_explanation_limit <= MAX_ACCOUNT_LIMIT):
            db.rollback()
            raise AdminValidationError(f"Limite de explicação DeepSeek deve ser inteiro entre 0 e {MAX_ACCOUNT_LIMIT}.")
        db.execute("UPDATE accounts SET deepseek_explanation_limit = ? WHERE id = ?", (deepseek_explanation_limit, account_id))

    if is_admin is not None:
        if not isinstance(is_admin, bool):
            db.rollback()
            raise AdminValidationError("O campo is_admin deve ser booleano.")
        # Atualiza ai_limit baseado nos novos limites
        new_ai_limit = int(ai_analysis_limit or 0) + int(deepseek_explanation_limit or 0)
        db.execute("UPDATE accounts SET is_admin = ?, ai_limit = ? WHERE id = ?",
                   (int(is_admin), new_ai_limit, account_id))

    db.commit()
    return get_admin_account(account_id)
