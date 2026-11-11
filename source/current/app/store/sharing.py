import time
from uuid import uuid4

from .db import get_db


def get_sharing(account_id: str, project_id: str) -> dict:
    row = get_db().execute("SELECT * FROM project_sharing WHERE account_id = ? AND project_id = ?", (account_id, project_id)).fetchone()
    if row is None:
        return {"project_id": project_id, "allow_admin_view": False, "allow_admin_comments": False, "inherit_account_default": True}
    return {"project_id": row["project_id"], "allow_admin_view": bool(row["allow_admin_view"]), "allow_admin_comments": bool(row["allow_admin_comments"]), "inherit_account_default": bool(row["inherit_account_default"])}


def save_sharing(account_id: str, project_id: str, allow_view: bool, allow_comments: bool, inherit_account_default: bool = True) -> dict | None:
    database = get_db()
    exists = database.execute("SELECT id FROM projects WHERE id = ? AND account_id = ?", (project_id, account_id)).fetchone()
    if exists is None:
        return None
    database.execute(
        """INSERT INTO project_sharing (project_id, account_id, allow_admin_view, allow_admin_comments, inherit_account_default, updated_at)
           VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET allow_admin_view=excluded.allow_admin_view, allow_admin_comments=excluded.allow_admin_comments, inherit_account_default=excluded.inherit_account_default, updated_at=excluded.updated_at""",
        (project_id, account_id, int(allow_view), int(allow_comments and allow_view), int(inherit_account_default), int(time.time())),
    )
    database.commit()
    return get_sharing(account_id, project_id)


def list_comments(project_id: str) -> list[dict]:
    rows = get_db().execute("SELECT body, author_role, created_at FROM project_comments WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
    return [dict(row) for row in rows]


def list_shared_projects() -> list[dict]:
    rows = get_db().execute("""SELECT p.id, p.title, p.project_type, p.updated_at, a.email, s.allow_admin_comments
                             FROM projects p JOIN project_sharing s ON s.project_id=p.id JOIN accounts a ON a.id=p.account_id
                             WHERE s.allow_admin_view=1 ORDER BY p.updated_at DESC""").fetchall()
    return [dict(row) for row in rows]


def get_shared_project(project_id: str) -> dict | None:
    row = get_db().execute("""SELECT p.*, s.allow_admin_comments, a.email
                            FROM projects p JOIN project_sharing s ON s.project_id=p.id JOIN accounts a ON a.id=p.account_id
                            WHERE p.id=? AND s.allow_admin_view=1""", (project_id,)).fetchone()
    return dict(row) if row else None


def add_admin_comment(project_id: str, admin_account_id: str, body: str) -> bool:
    body = str(body or "").strip()[:3000]
    row = get_db().execute("SELECT allow_admin_comments FROM project_sharing WHERE project_id = ? AND allow_admin_view = 1", (project_id,)).fetchone()
    if not row or not row["allow_admin_comments"] or not body:
        return False
    get_db().execute("INSERT INTO project_comments (id, project_id, author_account_id, author_role, body, created_at) VALUES (?, ?, ?, 'admin', ?, ?)", (str(uuid4()), project_id, admin_account_id, body, int(time.time())))
    get_db().commit()
    return True
