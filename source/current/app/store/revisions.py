"""Operações de revisão de projetos (histórico, diff, retenção 30)."""

from __future__ import annotations

import json
import time
from uuid import uuid4

from .db import get_db


MAX_REVISIONS_PER_PROJECT = 30
MAX_REVISION_AGE_DAYS = 30


def create_revision(
    account_id: str,
    project_id: str,
    revision: int,
    title: str,
    project_type: str,
    payload: dict,
) -> str:
    """Cria um snapshot de revisão do projeto."""
    snapshot_id = str(uuid4())
    now = int(time.time())
    db = get_db()
    db.execute(
        """INSERT INTO project_revisions
           (snapshot_id, project_id, account_id, revision, title, project_type, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot_id,
            project_id,
            account_id,
            revision,
            title[:240],
            project_type,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            now,
        ),
    )
    # Limpeza: manter apenas as últimas MAX_REVISIONS_PER_PROJECT revisões
    db.execute(
        """DELETE FROM project_revisions
           WHERE project_id = ? AND snapshot_id NOT IN (
               SELECT snapshot_id FROM project_revisions
               WHERE project_id = ?
               ORDER BY revision DESC LIMIT ?
           )""",
        (project_id, project_id, MAX_REVISIONS_PER_PROJECT),
    )
    # Limpeza por idade (opcional, rodar periodicamente)
    db.commit()
    return snapshot_id


def list_revisions(project_id: str, account_id: str) -> list[dict]:
    """Lista revisões de um projeto (mais recentes primeiro)."""
    rows = get_db().execute(
        """SELECT snapshot_id, revision, title, project_type, payload, created_at
           FROM project_revisions
           WHERE project_id = ? AND account_id = ?
           ORDER BY revision DESC""",
        (project_id, account_id),
    ).fetchall()
    return [
        {
            "snapshot_id": row["snapshot_id"],
            "revision": row["revision"],
            "title": row["title"],
            "project_type": row["project_type"],
            "payload": json.loads(row["payload"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_revision(account_id: str, project_id: str, snapshot_id: str) -> dict | None:
    """Obtém uma revisão específica."""
    row = get_db().execute(
        """SELECT snapshot_id, revision, title, project_type, payload, created_at
           FROM project_revisions
           WHERE project_id = ? AND account_id = ? AND snapshot_id = ?""",
        (project_id, account_id, snapshot_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "snapshot_id": row["snapshot_id"],
        "revision": row["revision"],
        "title": row["title"],
        "project_type": row["project_type"],
        "payload": json.loads(row["payload"]),
        "created_at": row["created_at"],
    }


def diff_revisions(
    account_id: str,
    project_id: str,
    snapshot_id_a: str,
    snapshot_id_b: str,
) -> dict | None:
    """Compara duas revisões e retorna diff simplificado."""
    rev_a = get_revision(account_id, project_id, snapshot_id_a)
    rev_b = get_revision(account_id, project_id, snapshot_id_b)
    if not rev_a or not rev_b:
        return None

    payload_a = rev_a.get("payload", {})
    payload_b = rev_b.get("payload", {})

    fields_a = payload_a.get("fields", {}) if isinstance(payload_a, dict) else {}
    fields_b = payload_b.get("fields", {}) if isinstance(payload_b, dict) else {}

    all_keys = set(fields_a.keys()) | set(fields_b.keys())
    diff = {}
    for key in sorted(all_keys):
        val_a = fields_a.get(key, "")
        val_b = fields_b.get(key, "")
        if val_a != val_b:
            diff[key] = {"from": val_a, "to": val_b}

    return {
        "revision_a": {"snapshot_id": snapshot_id_a, "revision": rev_a["revision"], "title": rev_a["title"]},
        "revision_b": {"snapshot_id": snapshot_id_b, "revision": rev_b["revision"], "title": rev_b["title"]},
        "fields_diff": diff,
    }


def restore_revision(
    account_id: str,
    project_id: str,
    snapshot_id: str,
    expected_revision: int,
) -> int | None:
    """Restaura uma revisão anterior como nova revisão do projeto."""
    from .projects import save_project, ProjectConflict, get_project

    revision_data = get_revision(account_id, project_id, snapshot_id)
    if not revision_data:
        return None

    current = get_project(account_id, project_id)
    if current is None:
        return None

    # Usa o payload da revisão como novo payload
    payload = revision_data["payload"]
    try:
        next_revision = save_project(account_id, project_id, expected_revision, payload)
        return next_revision
    except ProjectConflict:
        raise
    except Exception:
        return None


def cleanup_old_revisions(account_id: str | None = None) -> int:
    """Remove revisões antigas (> MAX_REVISION_AGE_DAYS). Retorna quantidade removida."""
    cutoff = int(time.time()) - (MAX_REVISION_AGE_DAYS * 86400)
    db = get_db()
    if account_id:
        cursor = db.execute(
            "DELETE FROM project_revisions WHERE account_id = ? AND created_at < ?",
            (account_id, cutoff),
        )
    else:
        cursor = db.execute("DELETE FROM project_revisions WHERE created_at < ?", (cutoff,))
    db.commit()
    return cursor.rowcount