import json

import pytest

from app.store.db import get_db


ADMIN_COLUMNS = {
    "plan_code": "TEXT NOT NULL DEFAULT 'livre'",
    "project_limit": "INTEGER NOT NULL DEFAULT 0",
    "project_used": "INTEGER NOT NULL DEFAULT 0",
    "ai_limit": "INTEGER NOT NULL DEFAULT 0",
    "ai_used": "INTEGER NOT NULL DEFAULT 0",
    "is_blocked": "INTEGER NOT NULL DEFAULT 0",
}


@pytest.fixture()
def admin_ready(app):
    app.config["ADMIN_EMAILS"] = {"admin@example.test"}
    with app.app_context():
        database = get_db()
        existing = {row["name"] for row in database.execute("PRAGMA table_info(accounts)")}
        for name, definition in ADMIN_COLUMNS.items():
            if name not in existing:
                database.execute(f"ALTER TABLE accounts ADD COLUMN {name} {definition}")
        database.commit()
    return app


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client, email):
    response = client.post("/auth/dev-login", data={"email": email, "name": email.split("@", 1)[0]})
    assert response.status_code == 302
    return csrf(client)


def account_id(app, email):
    with app.app_context():
        return get_db().execute("SELECT id FROM accounts WHERE email = ?", (email,)).fetchone()["id"]


def test_admin_updates_plan_credits_and_block_without_automatic_payment(admin_ready, client):
    owner_token = login(client, "owner-admin@example.test")
    client.post("/account/settings/terms", data={"csrf_token": owner_token, "accept": "on"})
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    assert created.status_code == 302
    owner_id = account_id(admin_ready, "owner-admin@example.test")
    with admin_ready.app_context():
        database = get_db()
        database.execute(
            "UPDATE accounts SET project_limit = 6, project_used = 1, ai_limit = 12, ai_used = 2 WHERE id = ?",
            (owner_id,),
        )
        database.commit()

    admin_token = login(client, "admin@example.test")
    listing = client.get("/admin/accounts")
    assert listing.status_code == 200
    assert "owner-admin@example.test" in listing.get_data(as_text=True)
    assert "6 concedidos" in listing.get_data(as_text=True)

    with admin_ready.app_context():
        before = dict(get_db().execute("SELECT * FROM accounts WHERE id = ?", (owner_id,)).fetchone())
    changed_plan = client.post(
        f"/admin/accounts/{owner_id}/plan",
        data={"csrf_token": admin_token, "plan_code": "com_ia"},
    )
    assert changed_plan.status_code == 302
    with admin_ready.app_context():
        after_plan = dict(get_db().execute("SELECT * FROM accounts WHERE id = ?", (owner_id,)).fetchone())
    assert after_plan["plan_code"] == "com_ia"
    assert after_plan["project_limit"] == before["project_limit"]
    assert after_plan["project_used"] == before["project_used"]
    assert after_plan["ai_limit"] == before["ai_limit"]

    changed_credits = client.post(
        f"/admin/accounts/{owner_id}/credits",
        data={"csrf_token": csrf(client), "project_remaining": "3"},
    )
    assert changed_credits.status_code == 302
    with admin_ready.app_context():
        credits = get_db().execute(
            "SELECT project_limit, project_used FROM accounts WHERE id = ?", (owner_id,)
        ).fetchone()
    assert credits["project_limit"] == 4
    assert credits["project_used"] == 1

    blocked = client.post(
        f"/admin/accounts/{owner_id}/block",
        data={"csrf_token": csrf(client), "blocked": "1"},
    )
    assert blocked.status_code == 302
    with admin_ready.app_context():
        assert get_db().execute("SELECT is_blocked FROM accounts WHERE id = ?", (owner_id,)).fetchone()[0] == 1
    unblocked = client.post(
        f"/admin/accounts/{owner_id}/block",
        data={"csrf_token": csrf(client), "blocked": "0"},
    )
    assert unblocked.status_code == 302
    with admin_ready.app_context():
        assert get_db().execute("SELECT is_blocked FROM accounts WHERE id = ?", (owner_id,)).fetchone()[0] == 0


def test_admin_management_requires_admin_and_csrf(admin_ready, client):
    token = login(client, "student-admin@example.test")
    assert client.get("/admin/accounts").status_code == 403

    owner_id = account_id(admin_ready, "student-admin@example.test")
    login(client, "admin@example.test")
    missing_csrf = client.post(
        f"/admin/accounts/{owner_id}/plan",
        data={"plan_code": "com_ia"},
    )
    assert missing_csrf.status_code == 400


def test_account_projects_expose_metadata_but_private_content_requires_sharing(admin_ready, client):
    owner_token = login(client, "private-admin@example.test")
    client.post("/account/settings/terms", data={"csrf_token": owner_token, "accept": "on"})
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    saved = client.post(
        f"/projects/{project_id}/save",
        headers={"X-CSRF-Token": csrf(client), "Content-Type": "application/json"},
        data=json.dumps(
            {
                "revision": 1,
                "payload": {"fields": {"title": "Projeto privado", "facts": "segredo privado"}},
            }
        ),
    )
    assert saved.status_code == 200
    owner_id = account_id(admin_ready, "private-admin@example.test")

    admin_token = login(client, "admin@example.test")
    metadata = client.get(f"/admin/accounts/{owner_id}/projects")
    body = metadata.get_data(as_text=True)
    assert metadata.status_code == 200
    assert "Projeto privado" in body
    assert "Conteúdo privado · sem acesso" in body
    assert "segredo privado" not in body
    assert "payload" not in body
    assert client.get(f"/admin/projects/{project_id}").status_code == 404

    shared = client  # The session is admin; authenticate the owner for the consent change.
    owner_token = login(shared, "private-admin@example.test")
    consent = shared.post(
        f"/projects/{project_id}/sharing",
        data={"csrf_token": csrf(shared), "allow_admin_view": "on"},
    )
    assert consent.status_code == 302
    login(shared, "admin@example.test")
    detail = shared.get(f"/admin/projects/{project_id}")
    assert detail.status_code == 200
    assert "segredo privado" in detail.get_data(as_text=True)
    assert admin_token != owner_token
