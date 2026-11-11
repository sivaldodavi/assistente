import json
from uuid import uuid4

import app.routes.ai as ai_route
from app.services.legal_recommendations import recommend
from app.services.providers import GeminiClient, ProviderError


CANDIDATES = [
    {"id": "vademecum-2023:law", "kind": "legislation", "title": "Responsabilidade civil", "reference": "Código Civil — art. 927", "source_year": 2023, "source": "Índice remissivo · 2023"},
    {"id": "stj-case", "kind": "case-law", "title": "Dano moral — Processo 1", "abstract": "Ementa oficial do STJ", "source_year": 2024, "source": "Ementas STJ"},
    {"id": "ufob-book", "kind": "book", "title": "Responsabilidade civil contemporânea", "author": "Autora Exemplo", "source_year": 2021, "source": "Livros jurídicos · 2021"},
]


def login_with_ai(client):
    client.post("/auth/dev-login", data={"email": "legal@example.test", "name": "Legal"})
    with client.session_transaction() as session:
        token = session["csrf_token"]
    response = client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on", "ai_consent": "on"})
    assert response.status_code == 302
    return token


def create_project(client, token):
    response = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_recommend_uses_deepseek_without_calling_gemini():
    calls = []

    class DeepSeek:
        def complete_json(self, messages, max_tokens):
            calls.append("deepseek")
            return {"model": "deepseek-test", "result": {"law": [{"source_id": "vademecum-2023:law", "why": "Relaciona o tema", "rank": 1}], "jurisprudence": [], "doctrine": [], "warnings": []}, "usage": {"prompt_tokens": 3}}

    result = recommend(
        {"problem_question": "Qual é a responsabilidade?", "professor_instructions": "Compare posições.", "keywords": [], "request_id": str(uuid4()), "project_revision": 1},
        {"project_type": "case", "fields": {}},
        CANDIDATES,
        deepseek_factory=DeepSeek,
        gemini_factory=lambda: (_ for _ in ()).throw(AssertionError("Gemini não deveria ser chamado")),
    )
    assert calls == ["deepseek"]
    assert result["provider"]["name"] == "deepseek"
    assert result["recommendations"]["law"][0]["source_id"] == "vademecum-2023:law"


def test_recommend_falls_back_to_gemini_once_on_technical_failure():
    calls = []

    class DeepSeek:
        def complete_json(self, messages, max_tokens):
            calls.append("deepseek")
            raise ProviderError("provider_busy", "ocupado", 503, retryable=True)

    class Gemini:
        def complete_json(self, messages, max_tokens):
            calls.append("gemini")
            return {"model": "gemini-test", "result": {"law": [], "jurisprudence": [], "doctrine": [{"source_id": "ufob-book", "why": "Oferece base doutrinária", "rank": 1}], "warnings": []}, "usage": {"prompt_tokens": 4}}

    result = recommend(
        {"problem_question": "Qual é a responsabilidade?", "professor_instructions": "Compare posições.", "keywords": [], "request_id": str(uuid4()), "project_revision": 1},
        {"project_type": "case", "fields": {}},
        CANDIDATES,
        deepseek_factory=DeepSeek,
        gemini_factory=Gemini,
    )
    assert calls == ["deepseek", "gemini"]
    assert result["provider"]["fallback_used"] is True
    assert result["provider"]["fallback_reason"] == "provider_busy"
    assert result["recommendations"]["doctrine"][0]["source_id"] == "ufob-book"


def test_legal_route_uses_fake_catalog_and_reserves_one_unit(client, monkeypatch):
    token = login_with_ai(client)
    project_id = create_project(client, token)
    monkeypatch.setattr(ai_route, "search_catalog", lambda *args, **kwargs: {"entries": CANDIDATES[:1]})
    monkeypatch.setattr(ai_route, "load_secret", lambda *args: "fake-secret")

    class FakeDeepSeek:
        def __init__(self, *_args, **_kwargs):
            pass

        def complete_json(self, messages, max_tokens):
            return {"model": "fake", "result": {"law": [{"source_id": "vademecum-2023:law", "why": "Pista legal", "rank": 1}], "jurisprudence": [], "doctrine": [], "warnings": []}, "usage": {"prompt_tokens": 1}}

    monkeypatch.setattr(ai_route, "DeepSeekClient", FakeDeepSeek)
    response = client.post(
        f"/projects/{project_id}/ai/legal-recommendations",
        headers={"X-CSRF-Token": token},
        json={"request_id": str(uuid4()), "project_revision": 1, "problem_question": "Qual é a responsabilidade?", "professor_instructions": "Compare.", "keywords": [], "catalog_source_ids": []},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["provider"]["name"] == "deepseek"
    assert body["recommendations"]["law"][0]["source_id"] == "vademecum-2023:law"

    from app.store.db import get_db
    with client.application.app_context():
        row = get_db().execute("SELECT ai_used FROM accounts WHERE email = ?", ("legal@example.test",)).fetchone()
        assert row["ai_used"] == 1


def test_attach_catalog_source_requires_explicit_endpoint(client, monkeypatch):
    token = login_with_ai(client)
    project_id = create_project(client, token)
    monkeypatch.setattr(ai_route, "entries_by_ids", lambda ids: [CANDIDATES[2]])
    response = client.post(
        f"/projects/{project_id}/ai/legal-recommendations/attach",
        headers={"X-CSRF-Token": token},
        json={"source_id": "ufob-book"},
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_gemini_client_parses_json_and_uses_api_key_header():
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit):
            return json.dumps({"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}], "usageMetadata": {"promptTokenCount": 2}}).encode()

    def opener(request, timeout):
        assert request.headers["X-goog-api-key"] == "Bearer secret" or request.headers["X-goog-api-key"] == "secret"
        assert timeout == 30
        return Response()

    result = GeminiClient("secret", opener=opener).complete_json([{"role": "user", "content": "teste"}])
    assert result["result"] == {"ok": True}
