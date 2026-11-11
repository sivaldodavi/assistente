"""Ledger de créditos da conta (account_grants)."""

from __future__ import annotations

import time
from uuid import uuid4

from .db import get_db


def create_grant(
    account_id: str,
    plan_code: str,
    project_credits: int = 0,
    ai_analysis_credits: int = 0,
    deepseek_explanation_credits: int = 0,
    expires_at: int | None = None,
) -> str:
    """Cria um grant de créditos para a conta."""
    grant_id = str(uuid4())
    now = int(time.time())
    db = get_db()
    db.execute(
        """INSERT INTO account_grants
           (grant_id, account_id, plan_code, project_credits, project_consumed,
            ai_analysis_credits, ai_analysis_consumed,
            deepseek_explanation_credits, deepseek_explanation_consumed,
            created_at, expires_at)
           VALUES (?, ?, ?, ?, 0, ?, 0, ?, 0, ?, ?)""",
        (
            grant_id,
            account_id,
            plan_code,
            project_credits,
            ai_analysis_credits,
            deepseek_explanation_credits,
            now,
            expires_at,
        ),
    )
    db.commit()
    return grant_id


def list_grants(account_id: str) -> list[dict]:
    """Lista grants da conta (mais recentes primeiro)."""
    rows = get_db().execute(
        """SELECT grant_id, plan_code, project_credits, project_consumed,
                  ai_analysis_credits, ai_analysis_consumed,
                  deepseek_explanation_credits, deepseek_explanation_consumed,
                  created_at, expires_at
           FROM account_grants
           WHERE account_id = ?
           ORDER BY created_at DESC""",
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
    return grants


def consume_project_credit(account_id: str) -> bool:
    """Consome 1 crédito de projeto do grant mais antigo com saldo (FIFO)."""
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
    """Devolve 1 crédito de projeto (LIFO - devolve do grant mais recente consumido)."""
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


def consume_ai_analysis_credit(account_id: str) -> bool:
    """Consome 1 crédito de análise IA (FIFO)."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        """SELECT grant_id, ai_analysis_credits, ai_analysis_consumed
           FROM account_grants
           WHERE account_id = ? AND ai_analysis_consumed < ai_analysis_credits
           ORDER BY created_at ASC
           LIMIT 1""",
        (account_id,),
    ).fetchone()
    if row is None:
        db.rollback()
        return False
    db.execute(
        "UPDATE account_grants SET ai_analysis_consumed = ai_analysis_consumed + 1 WHERE grant_id = ?",
        (row["grant_id"],),
    )
    db.commit()
    return True


def consume_deepseek_explanation_credit(account_id: str) -> bool:
    """Consome 1 crédito de explicação DeepSeek (FIFO)."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        """SELECT grant_id, deepseek_explanation_credits, deepseek_explanation_consumed
           FROM account_grants
           WHERE account_id = ? AND deepseek_explanation_consumed < deepseek_explanation_credits
           ORDER BY created_at ASC
           LIMIT 1""",
        (account_id,),
    ).fetchone()
    if row is None:
        db.rollback()
        return False
    db.execute(
        "UPDATE account_grants SET deepseek_explanation_consumed = deepseek_explanation_consumed + 1 WHERE grant_id = ?",
        (row["grant_id"],),
    )
    db.commit()
    return True


def get_available_credits(account_id: str) -> dict:
    """Retorna créditos disponíveis agregados (soma de todos os grants não expirados)."""
    now = int(time.time())
    rows = get_db().execute(
        """SELECT
            SUM(project_credits - project_consumed) as project_remaining,
            SUM(ai_analysis_credits - ai_analysis_consumed) as ai_analysis_remaining,
            SUM(deepseek_explanation_credits - deepseek_explanation_consumed) as deepseek_explanation_remaining
           FROM account_grants
           WHERE account_id = ? AND (expires_at IS NULL OR expires_at > ?)""",
        (account_id, now),
    ).fetchone()
    return {
        "project": max(0, rows["project_remaining"] or 0),
        "ai_analysis": max(0, rows["ai_analysis_remaining"] or 0),
        "deepseek_explanation": max(0, rows["deepseek_explanation_remaining"] or 0),
    }


def get_grants_summary(account_id: str) -> dict:
    """Retorna resumo detalhado dos grants para exibição no admin/perfil."""
    return {"grants": list_grants(account_id)}


def cleanup_expired_grants() -> int:
    """Remove grants expirados (opcional, rodar periodicamente)."""
    now = int(time.time())
    db = get_db()
    cursor = db.execute(
        "DELETE FROM account_grants WHERE expires_at IS NOT NULL AND expires_at < ?",
        (now,),
    )
    db.commit()
    return cursor.rowcount