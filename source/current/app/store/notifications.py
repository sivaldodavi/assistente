"""Fila de notificações (notification_outbox) - sem envio WhatsApp."""

from __future__ import annotations

import sqlite3
import time
from uuid import uuid4
from typing import Any

from .db import get_db


NOTIFICATION_KINDS = {
    "admin_comment",
    "project_shared",
    "ai_analysis_ready",
    "quarto_export_ready",
    "system_announcement",
    "deletion_requested",
    "deletion_confirmed",
}


def enqueue_notification(
    kind: str,
    text: str,
    account_id: str | None = None,
    project_id: str | None = None,
    destination: str | None = None,
    idempotency_key: str | None = None,
    next_attempt_at: int | None = None,
) -> int | None:
    """Adiciona notificação à fila de saída."""
    if kind not in NOTIFICATION_KINDS:
        raise ValueError(f"Tipo de notificação inválido: {kind}")
    if not text or not text.strip():
        raise ValueError("Texto da notificação não pode ser vazio")

    if idempotency_key is None:
        idempotency_key = f"{kind}:{account_id or 'global'}:{project_id or 'none'}:{uuid4().hex[:16]}"

    now = int(time.time())
    if next_attempt_at is None:
        next_attempt_at = now

    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        cursor = db.execute(
            """INSERT INTO notification_outbox
               (account_id, destination, kind, project_id, idempotency_key, text, status, attempts, next_attempt_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)""",
            (account_id, destination, kind, project_id, idempotency_key, text.strip()[:3000], next_attempt_at, now),
        )
        notification_id = cursor.lastrowid
        db.commit()
        return notification_id
    except sqlite3.IntegrityError:
        # Chave idempotente duplicada - ignora silenciosamente
        db.rollback()
        return None
    except Exception:
        db.rollback()
        raise


def get_pending_notifications(limit: int = 100) -> list[dict]:
    """Obtém notificações pendentes para processamento."""
    rows = get_db().execute(
        """SELECT id, account_id, destination, kind, project_id, idempotency_key, text, attempts, next_attempt_at, created_at
           FROM notification_outbox
           WHERE status = 'pending' AND next_attempt_at <= ?
           ORDER BY created_at ASC
           LIMIT ?""",
        (int(time.time()), limit),
    ).fetchall()
    return [dict(row) for row in rows]


def mark_notification_processing(notification_id: int) -> bool:
    """Marca notificação como em processamento."""
    db = get_db()
    cursor = db.execute(
        "UPDATE notification_outbox SET status = 'processing', attempts = attempts + 1 WHERE id = ? AND status = 'pending'",
        (notification_id,),
    )
    db.commit()
    return cursor.rowcount > 0


def mark_notification_sent(notification_id: int) -> bool:
    """Marca notificação como enviada."""
    db = get_db()
    cursor = db.execute(
        "UPDATE notification_outbox SET status = 'sent', next_attempt_at = NULL WHERE id = ?",
        (notification_id,),
    )
    db.commit()
    return cursor.rowcount > 0


def mark_notification_failed(notification_id: int, next_retry_seconds: int = 300) -> bool:
    """Marca notificação como falha e agenda nova tentativa."""
    next_attempt = int(time.time()) + next_retry_seconds
    db = get_db()
    cursor = db.execute(
        "UPDATE notification_outbox SET status = 'failed', next_attempt_at = ? WHERE id = ?",
        (next_attempt, notification_id),
    )
    db.commit()
    return cursor.rowcount > 0


def list_account_notifications(account_id: str, limit: int = 50, status: str | None = None) -> list[dict]:
    """Lista notificações de uma conta (para exibição no perfil/admin)."""
    query = """SELECT id, kind, project_id, text, status, attempts, created_at, next_attempt_at
               FROM notification_outbox WHERE account_id = ?"""
    params = [account_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = get_db().execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def get_notification_stats() -> dict:
    """Estatísticas da fila de notificações (para admin dashboard)."""
    db = get_db()
    rows = db.execute(
        """SELECT status, COUNT(*) as count
           FROM notification_outbox
           GROUP BY status"""
    ).fetchall()
    stats = {row["status"]: row["count"] for row in rows}
    # Total de hoje
    today_start = int(time.time()) - (int(time.time()) % 86400)
    today_count = db.execute(
        "SELECT COUNT(*) as count FROM notification_outbox WHERE created_at >= ?",
        (today_start,),
    ).fetchone()
    stats["today"] = today_count["count"] if today_count else 0
    return stats


def cleanup_old_notifications(days: int = 30) -> int:
    """Remove notificações antigas (enviadas/falhadas)."""
    cutoff = int(time.time()) - (days * 86400)
    db = get_db()
    cursor = db.execute(
        "DELETE FROM notification_outbox WHERE status IN ('sent', 'failed') AND created_at < ?",
        (cutoff,),
    )
    db.commit()
    return cursor.rowcount