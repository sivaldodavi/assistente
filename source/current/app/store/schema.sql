CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO app_meta (key, value)
VALUES ('schema_version', '12')
ON CONFLICT(key) DO UPDATE SET value = excluded.value;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    google_sub TEXT UNIQUE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    plan_code TEXT NOT NULL DEFAULT 'livre',
    project_limit INTEGER NOT NULL DEFAULT 0,
    project_used INTEGER NOT NULL DEFAULT 0,
    ai_limit INTEGER NOT NULL DEFAULT 0,
    ai_used INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    profile_json TEXT NOT NULL DEFAULT '{}',
    terms_accepted INTEGER NOT NULL DEFAULT 0,
    terms_version TEXT NOT NULL DEFAULT '',
    terms_accepted_at INTEGER,
    ai_consent INTEGER NOT NULL DEFAULT 0,
    sharing_preferences_version INTEGER NOT NULL DEFAULT 1,
    sharing_allow_admin_view INTEGER NOT NULL DEFAULT 0,
    sharing_allow_admin_comments INTEGER NOT NULL DEFAULT 0,
    sharing_inherit_default INTEGER NOT NULL DEFAULT 1,
    deletion_request_pending INTEGER NOT NULL DEFAULT 0,
    ai_analysis_limit INTEGER NOT NULL DEFAULT 0,
    deepseek_explanation_limit INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_login INTEGER
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    project_type TEXT NOT NULL CHECK(project_type IN ('case', 'paper_project', 'paper_final')),
    title TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    payload TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS projects_by_account ON projects(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS project_edit_days (
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    edit_date TEXT NOT NULL,
    edit_count INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (project_id, edit_date)
);

CREATE INDEX IF NOT EXISTS project_edit_days_by_account ON project_edit_days(account_id, edit_date);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'other',
    reference TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS sources_by_account ON sources(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS project_sharing (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    allow_admin_view INTEGER NOT NULL DEFAULT 0,
    allow_admin_comments INTEGER NOT NULL DEFAULT 0,
    inherit_account_default INTEGER NOT NULL DEFAULT 1,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS project_comments (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    author_role TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS project_comments_by_project ON project_comments(project_id, created_at);

CREATE TABLE IF NOT EXISTS ai_usage_reservations (
    request_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    units INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL CHECK(status IN ('reserved', 'complete', 'refunded')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS ai_usage_by_account ON ai_usage_reservations(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS provider_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    status TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS provider_usage_by_request ON provider_usage(request_id, created_at);

-- project_revisions (retention: 30)
CREATE TABLE IF NOT EXISTS project_revisions (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    title TEXT NOT NULL,
    project_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_revisions_project ON project_revisions(project_id, revision DESC);

-- deletion_requests
CREATE TABLE IF NOT EXISTS deletion_requests (
    account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    requested_by TEXT NOT NULL REFERENCES accounts(id),
    status TEXT NOT NULL CHECK(status IN ('pending','accepted','rejected')),
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);

-- notification_outbox
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
);

CREATE INDEX IF NOT EXISTS idx_notif_status ON notification_outbox(status, next_attempt_at);

-- account_grants (ledger de créditos)
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
);
