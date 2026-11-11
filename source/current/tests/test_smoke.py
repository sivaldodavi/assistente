def test_healthcheck(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "assistente-academico"}


def test_public_shell_is_server_rendered(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Case e Paper, em um só lugar." in body
    assert "Seus projetos são privados por padrão." in body


def test_database_starts_without_legacy_tables(app):
    from app.store.db import get_db

    with app.app_context():
        names = {row[0] for row in get_db().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
    # Core tables plus new tables from v12 migration
    expected_tables = {
        "app_meta",
        "accounts",
        "projects",
        "sources",
        "project_sharing",
        "project_comments",
        "ai_usage_reservations",
        "provider_usage",
        "project_edit_days",
        "sqlite_sequence",
        # New tables from v12 migration
        "project_revisions",
        "deletion_requests",
        "notification_outbox",
        "account_grants",
    }
    assert names == expected_tables
    assert not any("legacy" in name.lower() for name in names)
