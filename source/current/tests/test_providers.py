import json

import pytest

from app.services.providers import DeepSeekClient, JevClient, ProviderError, load_secret


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, _limit):
        return self.payload


def fake_opener(payload):
    def opener(request, timeout):
        assert request.get_method() == "POST"
        assert request.headers["Authorization"] == "Bearer secret"
        assert timeout == 30
        return FakeResponse(payload)
    return opener


def test_deepseek_client_parses_structured_json_without_network():
    client = DeepSeekClient("secret", opener=fake_opener({"model": "deepseek-chat", "choices": [{"message": {"content": '{"answer":"ok"}'}}], "usage": {"prompt_tokens": 1}}))
    result = client.complete_json([{"role": "user", "content": "teste"}])
    assert result["result"] == {"answer": "ok"}


def test_jev_client_preserves_structured_answers():
    client = JevClient("secret", opener=fake_opener({"model": "jev-latest", "answers": {"q1": {"score": 2}}, "usage": {"input_tokens": 1}}), timeout=30)
    result = client.score({"text": "teste"}, {"q1": {"type": "score"}})
    assert result["answers"]["q1"]["score"] == 2


def test_provider_rejects_invalid_json_content():
    client = DeepSeekClient("secret", opener=fake_opener({"choices": [{"message": {"content": "não-json"}}]}))
    with pytest.raises(ProviderError) as error:
        client.complete_json([])
    assert error.value.code == "invalid_response"


def test_secret_file_is_loaded_without_printing_value(tmp_path, monkeypatch):
    secret_file = tmp_path / "key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.delenv("TEST_SECRET", raising=False)
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    assert load_secret("TEST_SECRET", "TEST_SECRET_FILE") == "file-secret"
