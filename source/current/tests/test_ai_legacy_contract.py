import uuid

import app.routes.ai as ai_route
from app.services.providers import ProviderError


def login(client):
    client.post("/auth/dev-login", data={"email": "legacy-ai@example.test", "name": "IA"})
    with client.session_transaction() as session:
        token = session["csrf_token"]
    client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on", "ai_consent": "on"})
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    return token, created.headers["Location"].rsplit("/", 1)[-1]


class FakeDeepSeek:
    def __init__(self, *_args, **_kwargs):
        pass

    def complete_json(self, messages, max_tokens=1400):
        assert messages[1]["content"]["action"] == "suggest_problem"
        return {
            "model": "fake-deepseek",
            "result": {
                "answer": "A pergunta pode delimitar o conflito jurídico e o recorte factual.",
                "suggestions": [{"field_id": "problem", "text": "Qual solução jurídica é aplicável ao conflito descrito?"}],
                "rewrite": "",
                "checklist": [],
            },
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }


class FakeJev:
    def __init__(self, *_args, **_kwargs):
        pass

    def score(self, state, questions):
        answers = {
            question_id: {
                "score": 2,
                "confidence": 0.8,
                "probabilities": [0.05, 0.15, 0.55, 0.25],
                "observation": "A resposta tem relação com o recorte fornecido.",
            }
            for question_id in questions
        }
        return {"model": "fake-jev", "answers": answers, "usage": {"input_tokens": 10}}


class BrokenDeepSeek:
    def __init__(self, *_args, **_kwargs):
        pass

    def complete_json(self, messages, max_tokens=1400):
        return {"model": "broken", "result": {"answer": "sem contrato"}}


class DisabledDeepSeek:
    def __init__(self, *_args, **_kwargs):
        pass

    def complete_json(self, messages, max_tokens=1400):
        raise ProviderError("provider_auth", "primário indisponível", 502, retryable=True)


class FakeGemini:
    def __init__(self, *_args, **_kwargs):
        pass

    def complete_json(self, messages, max_tokens=1400):
        return {
            "model": "fake-gemini",
            "result": {"answer": "Resposta de fallback.", "suggestions": [], "rewrite": "", "checklist": []},
            "usage": {"prompt_tokens": 8},
        }


def test_specialized_action_returns_suggestion_and_jev_validation(client, monkeypatch):
    monkeypatch.setattr(ai_route, "DeepSeekClient", FakeDeepSeek)
    monkeypatch.setattr(ai_route, "JevClient", FakeJev)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token, project_id = login(client)
    response = client.post(
        f"/projects/{project_id}/ai/action",
        headers={"X-CSRF-Token": token},
        json={
            "action": "suggest_problem",
            "request_id": str(uuid.uuid4()),
            "project_revision": 1,
            "context_fields": ["assignment_prompt", "facts", "problem"],
        },
    )
    assert response.status_code == 200
    payload = response.get_json()["response"]
    assert payload["suggestions"][0]["field_id"] == "problem"
    assert payload["validation"]["status"] == "nao_avaliado"


def test_jev_section_returns_scores_and_probabilities(client, monkeypatch):
    monkeypatch.setattr(ai_route, "JevClient", FakeJev)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token, project_id = login(client)
    response = client.post(
        f"/projects/{project_id}/ai/jev-section",
        headers={"X-CSRF-Token": token},
        json={"section": "case_description", "request_id": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    analysis = response.get_json()["analysis"]
    assert analysis["criteria"][0]["score"] == 2
    assert len(analysis["criteria"][0]["probabilities"]) == 4


def test_gemini_is_used_once_when_deepseek_returns_invalid_structure(client, monkeypatch):
    monkeypatch.setattr(ai_route, "DeepSeekClient", BrokenDeepSeek)
    monkeypatch.setattr(ai_route, "GeminiClient", FakeGemini)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token, project_id = login(client)
    response = client.post(
        f"/projects/{project_id}/ai/action",
        headers={"X-CSRF-Token": token},
        json={"action": "chat", "request_id": str(uuid.uuid4()), "project_revision": 1, "message": "Como começo?"},
    )
    assert response.status_code == 200
    assert response.get_json()["response"]["provider"] == "gemini"


def test_gemini_fallback_covers_disabled_primary(client, monkeypatch):
    monkeypatch.setattr(ai_route, "DeepSeekClient", DisabledDeepSeek)
    monkeypatch.setattr(ai_route, "GeminiClient", FakeGemini)
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")
    token, project_id = login(client)
    response = client.post(
        f"/projects/{project_id}/ai/action",
        headers={"X-CSRF-Token": token},
        json={"action": "chat", "request_id": str(uuid.uuid4()), "project_revision": 1, "message": "Como começo?"},
    )
    assert response.status_code == 200
    payload = response.get_json()["response"]
    assert payload["provider"] == "gemini"
    assert payload["fallback_reason"] == "provider_auth"


def test_editor_places_ai_inside_stages_not_in_generic_panel(client):
    token, project_id = login(client)
    response = client.get(f"/projects/{project_id}")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'data-ai-stage-action="suggest_problem"' in html
    assert 'data-jev-section="case_description"' in html
    assert 'data-ai-inline="problem"' in html
    assert 'class="ai-icon-button"' in html
    assert 'class="ui-disclosure stage-ai-tools"' in html
    assert 'class="assisted-control"' in html
    assert 'field-actions' not in html
    assert 'class="review-progress"' in html
    assert 'Trilha de fundamentação' in html
    assert 'data-toggle-delivery' in html
    assert 'data-jev-report' in html
    assert html.count("data-legal-research") == 1
    assert html.index("data-stage=\"decisions\"") < html.index("data-legal-research")
    assert "assistant-disclosure" not in html
    assert "JEV" in html  # JEV functionality is now implemented
    assert "DeepSeek" not in html
    assert "Gemini" not in html
