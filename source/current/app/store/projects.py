import json
import time
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python suportado já inclui zoneinfo.
    ZoneInfo = None

from .db import get_db
from ..domain.schedule import normalize_schedule, schedule_deadlines, schedule_summary


def _edit_date(timestamp: int | None = None) -> str:
    moment = datetime.fromtimestamp(timestamp or time.time(), ZoneInfo("America/Sao_Paulo")) if ZoneInfo else datetime.now()
    return moment.date().isoformat()


class ProjectConflict(Exception):
    def __init__(self, current_revision):
        self.current_revision = current_revision
        super().__init__("A versão do projeto mudou em outra sessão.")


class ProjectQuotaError(RuntimeError):
    """A conta não possui crédito de projeto disponível."""


def _row_payload(row):
    payload = json.loads(row["payload"])
    payload.pop("timeline", None)
    payload["id"] = row["id"]
    payload["project_type"] = row["project_type"]
    payload["title"] = row["title"]
    payload["revision"] = row["revision"]
    return payload


def create_project(account_id, project_type):
    project_id = str(uuid4())
    now = int(time.time())
    from .accounts import get_account
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    account = get_account(account_id)
    if account is None:
        database.rollback()
        raise ProjectQuotaError("Conta não encontrada.")
    if not account["unlimited"] and int(account["project_remaining"] or 0) <= 0:
        database.rollback()
        raise ProjectQuotaError("A conta não possui crédito de projeto disponível.")
    profile = account.get("profile", {})
    fields = {"title": "", "authors": account.get("name", ""), **{key: profile.get(key, "") for key in ("institution", "course", "city")}}
    payload = {"version": 1, "fields": fields, "source_ids": [], "criteria": [], "deliveries": {}, "schedule": {"report_date": "", "debate_date": "", "dissertation_date": "", "final_date": "", "tasks": []}}
    database.execute(
        """INSERT INTO projects
           (id, account_id, project_type, title, revision, payload, created_at, updated_at)
           VALUES (?, ?, ?, '', 1, ?, ?, ?)""",
        (project_id, account_id, project_type, json.dumps(payload, ensure_ascii=False), now, now),
    )
    database.execute("UPDATE accounts SET project_used = project_used + 1 WHERE id = ?", (account_id,))
    database.commit()
    return project_id


def delete_project(account_id, project_id):
    """Exclui um projeto do proprietário e reduz o contador de projetos."""
    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    row = database.execute(
        "SELECT id FROM projects WHERE id = ? AND account_id = ?",
        (project_id, account_id),
    ).fetchone()
    if row is None:
        database.rollback()
        return False
    database.execute("DELETE FROM projects WHERE id = ? AND account_id = ?", (project_id, account_id))
    database.execute(
        "UPDATE accounts SET project_used = CASE WHEN project_used > 0 THEN project_used - 1 ELSE 0 END WHERE id = ?",
        (account_id,),
    )
    database.commit()
    return True


def list_projects(account_id):
    rows = get_db().execute(
        "SELECT id, project_type, title, revision, updated_at, payload FROM projects WHERE account_id = ? ORDER BY updated_at DESC",
        (account_id,),
    ).fetchall()
    projects = []
    for row in rows:
        project = {key: row[key] for key in ("id", "project_type", "title", "revision", "updated_at")}
        try:
            payload = json.loads(row["payload"])
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        fields = payload.get("fields") if isinstance(payload, dict) else {}
        fields = fields if isinstance(fields, dict) else {}
        schedule = normalize_schedule(
            payload.get("schedule") if isinstance(payload, dict) else {},
            fields.get("deliveryDate", ""),
            row["project_type"],
        )
        project["deadlines"] = schedule_deadlines(schedule, row["project_type"], row["id"], row["title"])
        project["schedule_summary"] = schedule_summary(schedule, row["project_type"])
        projects.append(project)
    return projects


def get_project(account_id, project_id):
    row = get_db().execute(
        "SELECT * FROM projects WHERE id = ? AND account_id = ?",
        (project_id, account_id),
    ).fetchone()
    return _row_payload(row) if row else None


def save_project(account_id, project_id, expected_revision, payload):
    database = get_db()
    now = int(time.time())
    title = str(payload.get("fields", {}).get("title") or "")[:240]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    database.execute("BEGIN IMMEDIATE")
    row = database.execute(
        "SELECT revision FROM projects WHERE id = ? AND account_id = ?",
        (project_id, account_id),
    ).fetchone()
    if row is None:
        database.rollback()
        return None
    if int(expected_revision) != int(row["revision"]):
        database.rollback()
        raise ProjectConflict(row["revision"])
    next_revision = int(row["revision"]) + 1
    database.execute(
        """UPDATE projects SET title = ?, revision = ?, payload = ?, updated_at = ?
           WHERE id = ? AND account_id = ?""",
        (title, next_revision, encoded, now, project_id, account_id),
    )
    edit_date = _edit_date(now)
    database.execute(
        """INSERT INTO project_edit_days (account_id, project_id, edit_date, edit_count, updated_at)
           VALUES (?, ?, ?, 1, ?)
           ON CONFLICT(project_id, edit_date) DO UPDATE SET
             edit_count = project_edit_days.edit_count + 1,
             updated_at = excluded.updated_at""",
        (account_id, project_id, edit_date, now),
    )
    cutoff = (datetime.fromtimestamp(now, ZoneInfo("America/Sao_Paulo")) - timedelta(days=365)).date().isoformat() if ZoneInfo else ""
    if cutoff:
        database.execute("DELETE FROM project_edit_days WHERE account_id = ? AND edit_date < ?", (account_id, cutoff))
    database.commit()
    return next_revision


def list_edit_activity(account_id, start_date: str, end_date: str) -> list[dict]:
    rows = get_db().execute(
        """SELECT edit_date AS date, SUM(edit_count) AS count
           FROM project_edit_days
           WHERE account_id = ? AND edit_date >= ? AND edit_date < ?
           GROUP BY edit_date ORDER BY edit_date""",
        (account_id, start_date, end_date),
    ).fetchall()
    return [{"date": row["date"], "count": int(row["count"] or 0)} for row in rows]


def switch_paper_mode(account_id, project_id, project_type, expected_revision):
    """Alterna Projeto/Paper Final mantendo identidade, fontes e planejamento."""
    if project_type not in {"paper_project", "paper_final"}:
        raise ValueError("Roteiro de Paper inválido.")
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT project_type, revision FROM projects WHERE id = ? AND account_id = ?", (project_id, account_id)).fetchone()
    if row is None or row["project_type"] not in {"paper_project", "paper_final"}:
        db.rollback()
        return None
    if int(expected_revision) != row["revision"]:
        db.rollback()
        raise ProjectConflict(row["revision"])
    revision = row["revision"] + 1
    db.execute("UPDATE projects SET project_type = ?, revision = ?, updated_at = ? WHERE id = ?", (project_type, revision, int(time.time()), project_id))
    db.commit()
    return revision
