import json


def login(client):
    response = client.post("/auth/dev-login", data={"email": "ana@example.test", "name": "Ana"})
    assert response.status_code == 302
    accepted = client.post("/account/settings/terms", data={"csrf_token": csrf(client), "accept": "on"})
    assert accepted.status_code == 302
    return response


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_login_create_and_open_case(client):
    login(client)
    response = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    assert response.status_code == 302
    editor = client.get(response.headers["Location"])
    assert editor.status_code == 200
    body = editor.get_data(as_text=True)
    assert "Linha do Tempo dos Fatos" not in body
    assert "Argumentação da tese A" in body
    assert "Argumentação da tese B" in body
    assert "Debate em grupo" in body
    assert "Dissertação" in body


def test_editor_uses_sources_from_personal_library(client):
    login(client)
    client.post("/library/sources", data={"csrf_token": csrf(client), "title": "Fonte do Case"})
    response = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    editor = client.get(response.headers["Location"])
    body = editor.get_data(as_text=True)
    assert "Fonte do Case" in body
    assert 'data-fact-sources' not in body
    assert 'data-project-source' in body


def test_editor_can_create_source_without_opening_library(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(
        f"/projects/{project_id}/sources",
        headers={"X-CSRF-Token": csrf(client)},
        json={"title": "Fonte inline", "author": "Autoria", "kind": "book", "notes": "Fichamento curto"},
    )
    assert response.status_code == 200
    source = response.get_json()["source"]
    assert source["title"] == "Fonte inline"
    assert source["notes"] == "Fichamento curto"
    saved = client.post(
        f"/projects/{project_id}/save",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf(client)},
        json={"revision": 1, "payload": {"fields": {}, "source_ids": [source["id"]]}},
    )
    assert saved.status_code == 200
    assert "Fonte inline" in client.get(f"/projects/{project_id}").get_data(as_text=True)


def test_save_rejects_stale_revision(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_url = created.headers["Location"]
    project_id = project_url.rsplit("/", 1)[-1]
    payload = {"version": 1, "fields": {"title": "Case inicial"}}
    headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf(client)}
    first = client.post(f"/projects/{project_id}/save", headers=headers, data=json.dumps({"revision": 1, "payload": payload}))
    assert first.status_code == 200
    stale = client.post(f"/projects/{project_id}/save", headers=headers, data=json.dumps({"revision": 1, "payload": payload}))
    assert stale.status_code == 409
    assert stale.get_json()["error"] == "project_conflict"


def test_case_fields_are_saved_and_normalized_on_server(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    payload = {
        "version": 1,
        "fields": {"title": "  Caso de teste  ", "authors": "Ana", "facts": "Fatos do caso", "unknown": "não salvar"},
        "timeline": [],
    }
    response = client.post(
        f"/projects/{project_id}/save",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf(client)},
        json={"revision": 1, "payload": payload},
    )
    assert response.status_code == 200
    editor = client.get(f"/projects/{project_id}").get_data(as_text=True)
    assert "Caso de teste" in editor
    assert "Fatos do caso" in editor
    assert "não salvar" not in editor


def test_project_sources_and_criteria_are_saved_with_ownership_filter(client):
    login(client)
    client.post("/library/sources", data={"csrf_token": csrf(client), "title": "Fonte autorizada"})
    from app.store.db import get_db
    with client.application.app_context():
        source_id = get_db().execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(
        f"/projects/{project_id}/save",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf(client)},
        json={"revision": 1, "payload": {"fields": {}, "source_ids": [source_id, "foreign-id"], "criteria": [{"id": "c1", "title": "Ponderação", "definition": "Definição", "basis": "CF"}]}},
    )
    assert response.status_code == 200
    editor = client.get(f"/projects/{project_id}").get_data(as_text=True)
    assert "Ponderação" in editor
    assert "Fonte autorizada" in editor


def test_paper_project_and_final_have_distinct_workflows(client):
    login(client)
    for project_type, expected in (("paper_project", "Identificação e delimitação"), ("paper_final", "Resumo")):
        created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": project_type})
        editor = client.get(created.headers["Location"])
        assert editor.status_code == 200
        body = editor.get_data(as_text=True)
        assert expected in body
        assert "Entrega do Projeto de Paper" in body
        assert "Entrega do Paper Final" in body


def test_project_creation_redirects_unaccepted_account_to_terms(client):
    client.post("/auth/dev-login", data={"email": "sem-termos@example.test", "name": "Sem Termos"})
    response = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    assert response.status_code == 302
    assert "/account/settings?required=terms" in response.headers["Location"]


def test_schedule_is_saved_and_invalid_dates_are_discarded(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(
        f"/projects/{project_id}/save",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf(client)},
        json={"revision": 1, "payload": {"fields": {}, "schedule": {"report_date": "2026-10-30", "debate_date": "invalid", "tasks": [{"title": "Ler fontes", "date": "2026-11-01"}, {"title": "sem data", "date": "bad"}]}}},
    )
    assert response.status_code == 200
    body = client.get(f"/projects/{project_id}").get_data(as_text=True)
    assert "2026-10-30" in body
    assert "Ler fontes" in body


def test_account_shows_schedule_calendar_and_completed_tasks(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    saved = client.post(
        f"/projects/{project_id}/save",
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf(client)},
        json={"revision": 1, "payload": {"fields": {}, "schedule": {"report_date": "2099-10-30", "tasks": [{"id": "task-1", "title": "Conferir fontes", "date": "2099-10-29", "done": True}]}}},
    )
    assert saved.status_code == 200
    editor = client.get(f"/projects/{project_id}").get_data(as_text=True)
    assert 'data-task-field="done" checked' in editor
    account = client.get("/account").get_data(as_text=True)
    assert "Agenda" in account
    assert "Salvamentos por dia" in account
    assert "Entrega do relatório" in account
    assert "30/10/2099" in account
    assert f"/projects/{project_id}" in account


def test_delete_project_requires_csrf_and_removes_owned_project(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]

    missing_csrf = client.post(f"/projects/{project_id}/delete")
    assert missing_csrf.status_code in {400, 403}
    assert client.get(f"/projects/{project_id}").status_code == 200

    deleted = client.post(f"/projects/{project_id}/delete", data={"csrf_token": csrf(client)})
    assert deleted.status_code == 302
    assert "deleted=1" in deleted.headers["Location"]
    assert client.get(f"/projects/{project_id}").status_code == 404
    assert "Trabalho excluído." in client.get(deleted.headers["Location"]).get_data(as_text=True)

    from app.store.db import get_db
    with client.application.app_context():
        assert get_db().execute("SELECT project_used FROM accounts").fetchone()["project_used"] == 0


def test_delete_unknown_project_returns_not_found(client):
    login(client)
    response = client.post("/projects/does-not-exist/delete", data={"csrf_token": csrf(client)})
    assert response.status_code == 404
