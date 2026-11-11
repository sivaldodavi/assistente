from __future__ import annotations

import time
from flask import current_app
from .db import get_db


class UsageError(RuntimeError):
    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.status = status
        super().__init__(message)


def reserve_usage(account_id: str, project_id: str, request_id: str, action: str) -> None:
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    existing = database.execute(
        "SELECT status FROM ai_usage_reservations WHERE request_id = ?", (request_id,)
    ).fetchone()
    if existing is not None:
        database.rollback()
        raise UsageError("duplicate_usage_request", "Esta solicitação já foi processada.", 409)
    project = database.execute(
        "SELECT 1 FROM projects WHERE id = ? AND account_id = ?", (project_id, account_id)
    ).fetchone()
    if project is None:
        database.rollback()
        raise UsageError("project_not_found", "Projeto não encontrado.", 404)
    account = database.execute(
        "SELECT email, ai_limit, ai_used FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if account is None:
        database.rollback()
        raise UsageError("account_not_found", "Conta não encontrada.", 401)
    admin_emails = current_app.config.get("ADMIN_EMAILS", set())
    is_admin = str(account["email"] or "").lower() in admin_emails
    if not is_admin and int(account["ai_used"] or 0) >= int(account["ai_limit"] or 0):
        database.rollback()
        raise UsageError("ai_quota_exhausted", "O limite de assistência desta conta foi atingido.", 429)
    now = int(time.time())
    database.execute(
        "INSERT INTO ai_usage_reservations (request_id, account_id, project_id, action, units, status, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 'reserved', ?, ?)",
        (request_id, account_id, project_id, action, now, now),
    )
    database.execute("UPDATE accounts SET ai_used = ai_used + 1 WHERE id = ?", (account_id,))
    database.commit()


def finish_usage(request_id: str) -> None:
    database = get_db()
    database.execute(
        "UPDATE ai_usage_reservations SET status = 'complete', updated_at = ? WHERE request_id = ? AND status = 'reserved'",
        (int(time.time()), request_id),
    )
    database.commit()


def refund_usage(request_id: str) -> None:
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    row = database.execute(
        "SELECT account_id FROM ai_usage_reservations WHERE request_id = ? AND status = 'reserved'",
        (request_id,),
    ).fetchone()
    if row is not None:
        database.execute(
            "UPDATE ai_usage_reservations SET status = 'refunded', updated_at = ? WHERE request_id = ?",
            (int(time.time()), request_id),
        )
        database.execute(
            "UPDATE accounts SET ai_used = CASE WHEN ai_used > 0 THEN ai_used - 1 ELSE 0 END WHERE id = ?",
            (row["account_id"],),
        )
    database.commit()


def record_provider_usage(request_id: str, provider: str, operation: str, model: str, status: str, usage: dict | None = None) -> None:
    usage = usage if isinstance(usage, dict) else {}
    database = get_db()
    database.execute(
        "INSERT INTO provider_usage (request_id, provider, operation, model, input_tokens, output_tokens, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            request_id,
            provider[:80],
            operation[:120],
            model[:160],
            usage.get("prompt_tokens", usage.get("input_tokens")) if isinstance(usage.get("prompt_tokens", usage.get("input_tokens")), int) else None,
            usage.get("completion_tokens", usage.get("output_tokens")) if isinstance(usage.get("completion_tokens", usage.get("output_tokens")), int) else None,
            status[:40],
            int(time.time()),
        ),
    )
    database.commit()
