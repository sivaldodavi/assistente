from app.store.db import get_db


def start(client, kind="case"):
    client.post("/auth/dev-login", data={"email": "roteiro@example.test", "name": "Roteiro"})
    with client.session_transaction() as session:
        token = session["csrf_token"]
        account_id = session["account_id"]
    client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on"})
    created = client.post("/projects", data={"csrf_token": token, "project_type": kind})
    return created.headers["Location"], token, account_id


def test_case_restores_single_panel_and_all_original_phases(client):
    url, _, _ = start(client)
    body = client.get(url).get_data(as_text=True)
    assert body.count('data-stage="') == 11
    assert 'class="workspace"' in body
    assert 'data-previous-step' in body and 'data-next-step' in body
    assert 'data-stage="thesis_a"' in body and 'data-stage="thesis_b"' in body
    assert 'data-stage="dissertation"' in body
    assert 'data-stage="dissertation_development"' not in body
    assert 'data-stage="description"' in body and 'hidden' in body
    assert 'data-case-field="thesis_a"' in body
    assert 'data-workflow-check="facts-original"' in body
    assert 'data-fact' not in body
    assert 'timeline' not in body


def test_save_keeps_theses_checks_and_discards_timeline(client):
    url, token, account_id = start(client)
    response = client.post(url + "/save", headers={"X-CSRF-Token": token}, json={"revision": 1, "payload": {"fields": {"thesis_a": "Tese A", "thesis_b": "Tese B"}, "checks": {"facts-original": True, "unknown": True}, "timeline": [{"fact": "Excluir"}], "development_sections": [{"title": "Fundamento", "body": "Texto"}]}})
    assert response.status_code == 200
    from app.store.projects import get_project
    with client.application.app_context():
        project = get_project(account_id, url.rsplit("/", 1)[-1])
    assert project["fields"]["thesis_a"] == "Tese A"
    assert project["checks"] == {"facts-original": True}
    assert project["development_sections"][0]["body"] == "Texto"
    assert "timeline" not in project


def test_paper_mode_preserves_research_planning_and_identity(client):
    url, token, account_id = start(client, "paper_project")
    headers = {"X-CSRF-Token": token}
    saved = client.post(url + "/save", headers=headers, json={"revision": 1, "payload": {"fields": {"title": "Paper", "hypothesis": "Hipótese original"}}})
    revision = saved.get_json()["revision"]
    switched = client.post(url + "/paper-mode", headers=headers, json={"revision": revision, "project_type": "paper_final"})
    assert switched.status_code == 200
    revision = switched.get_json()["revision"]
    page = client.get(url).get_data(as_text=True)
    assert 'data-stage="paper_final_introduction"' in page
    assert 'Consultar Projeto de Paper' in page
    saved = client.post(url + "/save", headers=headers, json={"revision": revision, "payload": {"fields": {"abstract": "Resumo"}}})
    assert saved.status_code == 200
    from app.store.projects import get_project
    with client.application.app_context():
        project = get_project(account_id, url.rsplit("/", 1)[-1])
    assert project["fields"]["hypothesis"] == "Hipótese original"
    assert project["fields"]["abstract"] == "Resumo"
    assert client.post(url + "/paper-mode", headers=headers, json={"revision": revision, "project_type": "paper_project"}).status_code == 409


def test_profile_does_not_collect_automatic_messaging_contact(client):
    _, token, account_id = start(client)
    accepted = client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on", "whatsapp_phone": "5598981417363", "whatsapp_opt_in": "on"})
    assert accepted.status_code == 302
    page = client.get("/account/settings").get_data(as_text=True)
    assert "whatsapp_phone" not in page
    with client.application.app_context():
        columns = {row["name"] for row in get_db().execute("PRAGMA table_info(accounts)")}
    assert not columns.intersection({"whatsapp_phone", "whatsapp_opt_in", "whatsapp_opt_in_at", "whatsapp_opt_out_at"})


def test_blocked_account_cannot_continue_existing_session(client):
    _, _, account_id = start(client)
    with client.application.app_context():
        db = get_db()
        db.execute("UPDATE accounts SET is_blocked = 1 WHERE id = ?", (account_id,))
        db.commit()
    assert client.get('/account').status_code == 403
    with client.session_transaction() as session:
        assert 'account_id' not in session
    assert client.post('/auth/dev-login', data={'email': 'roteiro@example.test'}).status_code == 403


def test_export_separates_report_and_dissertation(client):
    url, token, _ = start(client)
    client.post(url+'/save', headers={'X-CSRF-Token': token}, json={'revision': 1, 'payload': {'fields': {'facts': 'Narrativa do relatório', 'dissertation_intro': 'Introdução individual', 'dissertation_conclusion': 'Conclusão individual'}, 'development_sections': [{'id': 'topic-1', 'title': 'Fundamentação', 'body': 'Desenvolvimento individual'}]}})
    report = client.get(url+'/export?phase=report').get_data(as_text=True)
    dissertation = client.get(url+'/export?phase=dissertation').get_data(as_text=True)
    assert 'Narrativa do relatório' in report and 'Introdução individual' not in report
    assert 'Introdução individual' in dissertation and 'Narrativa do relatório' not in dissertation
    assert dissertation.index('Introdução individual') < dissertation.index('Desenvolvimento individual') < dissertation.index('Conclusão individual')
    assert client.get(url+'/export?phase=unrecognized').status_code == 400
