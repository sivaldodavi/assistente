import os
import sqlite3
import fcntl
from pathlib import Path

from flask import current_app, g


def _migration_lock(database_path: Path):
    """File-based lock to prevent concurrent migrations in multi-worker environments."""
    lock_file = database_path.with_suffix(".migration.lock")
    lock_fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        os.close(lock_fd)
        return None


def _release_migration_lock(lock_fd):
    if lock_fd is not None:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def get_db():
    if "db" not in g:
        database = Path(current_app.config["DATABASE"])
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        g.db = connection
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def _remove_automatic_messaging(database):
    columns = {row["name"] for row in database.execute("PRAGMA table_info(accounts)")}
    outbox = database.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'notification_outbox'"
    ).fetchone()
    old_columns = {"whatsapp_phone", "whatsapp_opt_in", "whatsapp_opt_in_at", "whatsapp_opt_out_at"} & columns
    if not old_columns and outbox is None:
        return
    database.execute("PRAGMA foreign_keys = OFF")
    try:
        database.execute("BEGIN")
        if outbox is not None:
            database.execute("DROP TABLE notification_outbox")
        for name in sorted(old_columns):
            database.execute(f"ALTER TABLE accounts DROP COLUMN {name}")
        database.execute("UPDATE app_meta SET value = '11' WHERE key = 'schema_version'")
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.execute("PRAGMA foreign_keys = ON")


def _migrate_schema_v12(database):
    """Migração para schema v12 - funcionalidades do legado"""
    # Novas colunas em accounts
    account_columns = {row["name"] for row in database.execute("PRAGMA table_info(accounts)")}
    account_additions = {
        "sharing_preferences_version": "INTEGER NOT NULL DEFAULT 1",
        "sharing_allow_admin_view": "INTEGER NOT NULL DEFAULT 0",
        "sharing_allow_admin_comments": "INTEGER NOT NULL DEFAULT 0",
        "sharing_inherit_default": "INTEGER NOT NULL DEFAULT 1",
        "deletion_request_pending": "INTEGER NOT NULL DEFAULT 0",
        "ai_analysis_limit": "INTEGER NOT NULL DEFAULT 0",
        "deepseek_explanation_limit": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in account_additions.items():
        if name not in account_columns:
            database.execute(f"ALTER TABLE accounts ADD COLUMN {name} {definition}")

    # Nova coluna em project_sharing
    sharing_columns = {row["name"] for row in database.execute("PRAGMA table_info(project_sharing)")}
    if "inherit_account_default" not in sharing_columns:
        database.execute("ALTER TABLE project_sharing ADD COLUMN inherit_account_default INTEGER NOT NULL DEFAULT 1")

    # Novas tabelas
    # project_revisions
    database.execute("""
        CREATE TABLE IF NOT EXISTS project_revisions (
            snapshot_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            title TEXT NOT NULL,
            project_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    database.execute("CREATE INDEX IF NOT EXISTS idx_revisions_project ON project_revisions(project_id, revision DESC)")

    # deletion_requests
    database.execute("""
        CREATE TABLE IF NOT EXISTS deletion_requests (
            account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
            requested_by TEXT NOT NULL REFERENCES accounts(id),
            status TEXT NOT NULL CHECK(status IN ('pending','accepted','rejected')),
            created_at INTEGER NOT NULL,
            resolved_at INTEGER
        )
    """)

    # notification_outbox
    database.execute("""
        CREATE TABLE IF NOT EXISTS notification_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL,
            destination TEXT,
            kind TEXT NOT NULL,
            project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
            idempotency_key TEXT UNIQUE,
            text TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','processing','sent','failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at INTEGER,
            created_at INTEGER NOT NULL
        )
    """)
    database.execute("CREATE INDEX IF NOT EXISTS idx_notif_status ON notification_outbox(status, next_attempt_at)")

    # account_grants
    database.execute("""
        CREATE TABLE IF NOT EXISTS account_grants (
            grant_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            plan_code TEXT NOT NULL,
            project_credits INTEGER NOT NULL DEFAULT 0,
            project_consumed INTEGER NOT NULL DEFAULT 0,
            ai_analysis_credits INTEGER NOT NULL DEFAULT 0,
            ai_analysis_consumed INTEGER NOT NULL DEFAULT 0,
            deepseek_explanation_credits INTEGER NOT NULL DEFAULT 0,
            deepseek_explanation_consumed INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            expires_at INTEGER
        )
    """)

    # Atualizar versão do schema
    database.execute("UPDATE app_meta SET value = '12' WHERE key = 'schema_version'")


def init_db():
    database = get_db()
    db_path = Path(current_app.config["DATABASE"])

    # Try to acquire migration lock; if another worker holds it, skip migrations
    lock_fd = _migration_lock(db_path)
    if lock_fd is None:
        # Another worker is running migrations; wait briefly and proceed without migrations
        import time
        time.sleep(0.5)
        return

    try:
        schema = Path(current_app.root_path) / "store" / "schema.sql"
        database.executescript(schema.read_text(encoding="utf-8"))
        _remove_automatic_messaging(database)
        columns = {row["name"] for row in database.execute("PRAGMA table_info(accounts)")}
        additions = {"plan_code": "TEXT NOT NULL DEFAULT 'livre'", "project_limit": "INTEGER NOT NULL DEFAULT 0", "project_used": "INTEGER NOT NULL DEFAULT 0", "ai_limit": "INTEGER NOT NULL DEFAULT 0", "ai_used": "INTEGER NOT NULL DEFAULT 0", "is_blocked": "INTEGER NOT NULL DEFAULT 0"}
        added_usage = "project_used" not in columns
        for name, definition in additions.items():
            if name not in columns:
                database.execute(f"ALTER TABLE accounts ADD COLUMN {name} {definition}")
        if added_usage:
            database.execute("UPDATE accounts SET project_used = (SELECT COUNT(*) FROM projects p WHERE p.account_id = accounts.id)")
        database.execute("UPDATE projects SET payload = json_remove(payload, '$.timeline') WHERE json_valid(payload) AND json_type(payload, '$.timeline') IS NOT NULL")

        # Migração para v12
        meta = database.execute("SELECT value FROM app_meta WHERE key = 'schema_version'").fetchone()
        current_version = int(meta["value"]) if meta else 0
        if current_version < 12:
            _migrate_schema_v12(database)

        database.commit()
    finally:
        _release_migration_lock(lock_fd)
