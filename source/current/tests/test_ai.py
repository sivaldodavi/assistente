import app.routes.ai as ai_route


def login(client, consent=False):
    client.post("/auth/dev-login", data={"email": "ia@example.test", "name": "IA"})
    with client.session_transaction() as session:
        token = session["csrf_token"]
    data = {"csrf_token": token, "accept": "on"}
    if consent:
        data["ai_consent"] = "on"
    client.post("/account/settings/terms", data=data)
    return token


class FakeDeepSeek:
    def __init__(self, *_args, **_kwargs):
        pass

    def complete_json(self, messages, max_tokens=1400):
        assert messages[1]["content"]["field_id"] == "problem"
        return {"result": {"answer": "Confira se a pergunta é aberta.", "suggestions": [{"text": "Relacione a pergunta aos fatos."}]}}


def test_ai_requires_separate_consent(client):
    token = login(client, consent=False)
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(f"/projects/{project_id}/ai/review", headers={"X-CSRF-Token": token}, json={"field_id": "problem", "instruction": "Revise"})
    assert response.status_code == 403
    assert response.get_json()["error"] == "ai_consent_required"


def test_ai_review_uses_fake_provider_after_consent(client, monkeypatch):
    monkeypatch.setattr(ai_route, "DeepSeekClient", FakeDeepSeek)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token = login(client, consent=True)
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(f"/projects/{project_id}/ai/review", headers={"X-CSRF-Token": token}, json={"field_id": "problem", "instruction": "Revise"})
    assert response.status_code == 200
    assert response.get_json()["suggestions"][0]["text"] == "Relacione a pergunta aos fatos."


def test_ai_rejects_field_outside_contract(client):
    token = login(client, consent=True)
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(f"/projects/{project_id}/ai/review", headers={"X-CSRF-Token": token}, json={"field_id": "authors", "instruction": "Revise"})
    assert response.status_code == 400


def test_jev_validation_uses_fixed_questions_and_fake_provider(client, monkeypatch):
    class FakeJev:
        def __init__(self, *_args, **_kwargs):
            pass

        def score(self, state, questions):
            assert state["field_id"] == "problem"
            assert "coherence" in questions
            return {"model": "fake-jev", "answers": {"coherence": {"score": 2}}, "usage": {}}

    monkeypatch.setattr(ai_route, "JevClient", FakeJev)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token = login(client, consent=True)
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(f"/projects/{project_id}/ai/validate", headers={"X-CSRF-Token": token}, json={"field_id": "problem"})
    assert response.status_code == 200
    assert response.get_json()["answers"]["coherence"]["score"] == 2
