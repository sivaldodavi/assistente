from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 503, retryable: bool = False):
        self.code = code
        self.status = status
        self.retryable = retryable
        super().__init__(message)


# Configurable timeouts via environment variables
DEFAULT_PROVIDER_TIMEOUT = int(os.environ.get("PROVIDER_TIMEOUT", "30"))
DEFAULT_JEV_TIMEOUT = int(os.environ.get("JEV_TIMEOUT", "60"))
DEFAULT_DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "30"))
DEFAULT_GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "30"))


def load_secret(env_name: str, file_env_name: str, default_file: str = "") -> str:
    value = os.environ.get(env_name, "").strip()
    path = os.environ.get(file_env_name, default_file)
    if not value and path:
        try:
            value = Path(path).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            # Não vazar o caminho do arquivo na mensagem de erro
            raise ProviderError("secret_unavailable", "A configuração do provedor não pôde ser carregada.")
    if not value or len(value) > 4096 or "\n" in value or "\r" in value:
        raise ProviderError("secret_invalid", "A configuração do provedor é inválida.")
    return value


class _JsonProvider:
    def __init__(self, api_key: str, api_url: str, model: str, opener=urlopen, timeout: int = DEFAULT_PROVIDER_TIMEOUT):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.opener = opener
        self.timeout = timeout

    def post(self, payload: dict, timeout: int | None = None) -> dict:
        effective_timeout = timeout if timeout is not None else self.timeout
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.api_url,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=effective_timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
        except HTTPError as error:
            status = error.code
            error.close()
            if status in {408, 429, 529} or status >= 500:
                raise ProviderError("provider_busy", "O provedor está temporariamente ocupado.", 503, retryable=True) from error
            if status == 401:
                raise ProviderError("provider_auth", "A configuração do provedor foi recusada.", 502, retryable=True) from error
            if status == 402:
                raise ProviderError("provider_quota", "O provedor não possui crédito disponível.", 503, retryable=True) from error
            raise ProviderError("provider_error", "O provedor não concluiu a solicitação.", 502) from error
        except (TimeoutError, URLError, OSError) as error:
            raise ProviderError("provider_unreachable", "Não foi possível conectar ao provedor.", 503) from error
        if len(raw) > 4 * 1024 * 1024:
            raise ProviderError("response_too_large", "A resposta do provedor é grande demais.", 502)
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProviderError("invalid_response", "O provedor retornou uma resposta inválida.", 502, retryable=True) from error
        if not isinstance(data, dict):
            raise ProviderError("invalid_response", "O provedor retornou uma resposta inválida.", 502, retryable=True)
        return data


class DeepSeekClient(_JsonProvider):
    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/chat/completions", model: str = "deepseek-chat", opener=urlopen, timeout: int = DEFAULT_DEEPSEEK_TIMEOUT):
        super().__init__(api_key, api_url, model, opener, timeout)

    def complete_json(self, messages: list[dict], max_tokens: int = 1400) -> dict:
        response = self.post({"model": self.model, "messages": messages, "response_format": {"type": "json_object"}, "max_tokens": max_tokens, "stream": False})
        choices = response.get("choices")
        content = choices[0].get("message", {}).get("content") if isinstance(choices, list) and len(choices) == 1 else None
        if not isinstance(content, str):
            raise ProviderError("invalid_response", "A resposta DeepSeek não trouxe conteúdo JSON.", 502, retryable=True)
        try:
            result = json.loads(content)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProviderError("invalid_response", "A resposta DeepSeek não trouxe JSON válido.", 502, retryable=True) from error
        if not isinstance(result, dict):
            raise ProviderError("invalid_response", "A resposta DeepSeek não trouxe um objeto JSON.", 502, retryable=True)
        return {"model": response.get("model") or self.model, "result": result, "usage": response.get("usage", {})}


class GeminiClient:
    def __init__(self, api_key: str, api_url: str = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", model: str = "gemini-2.5-flash", opener=urlopen, timeout: int = DEFAULT_GEMINI_TIMEOUT):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.opener = opener
        self.timeout = timeout

    def complete_json(self, messages: list[dict], max_tokens: int = 1400) -> dict:
        system = ""
        contents = []
        for message in messages:
            role = message.get("role") if isinstance(message, dict) else "user"
            content = message.get("content") if isinstance(message, dict) else message
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, separators=(",", ":"))
            if role == "system":
                system = text
            else:
                contents.append({"role": "user", "parts": [{"text": text}]})
        payload = {
            "systemInstruction": {"parts": [{"text": system}]} if system else None,
            "contents": contents or [{"role": "user", "parts": [{"text": "Responda em JSON."}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_tokens},
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.api_url.format(model=self.model),
            data=body,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
        except HTTPError as error:
            status = error.code
            error.close()
            if status in {408, 429} or status >= 500:
                raise ProviderError("provider_busy", "O provedor Gemini está temporariamente ocupado.", 503, retryable=True) from error
            if status in {400, 401, 403}:
                raise ProviderError("provider_auth", "A configuração do Gemini foi recusada.", 502) from error
            raise ProviderError("provider_error", "O Gemini não concluiu a solicitação.", 502) from error
        except (TimeoutError, URLError, OSError) as error:
            raise ProviderError("provider_unreachable", "Não foi possível conectar ao Gemini.", 503, retryable=True) from error
        if len(raw) > 4 * 1024 * 1024:
            raise ProviderError("response_too_large", "A resposta do Gemini é grande demais.", 502, retryable=True)
        try:
            response = json.loads(raw)
            candidates = response.get("candidates")
            parts = candidates[0].get("content", {}).get("parts", []) if isinstance(candidates, list) and candidates else []
            content = parts[0].get("text") if parts and isinstance(parts[0], dict) else None
            result = json.loads(content) if isinstance(content, str) else None
            if not isinstance(result, dict):
                raise ValueError("JSON ausente")
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
            raise ProviderError("invalid_response", "O Gemini retornou uma resposta inválida.", 502, retryable=True) from error
        usage = response.get("usageMetadata") or {}
        return {
            "model": self.model,
            "result": result,
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "prompt_cache_hit_tokens": usage.get("cachedContentTokenCount", 0),
            },
        }


class JevClient(_JsonProvider):
    def __init__(self, api_key: str, api_url: str = "https://api.typesafe.ai/v1/systemone", model: str = "jev-latest", opener=urlopen, timeout: int = DEFAULT_JEV_TIMEOUT):
        super().__init__(api_key, api_url, model, opener, timeout)

    def score(self, state: dict, questions: dict) -> dict:
        response = self.post({"state": state, "model": self.model, "questions": questions})
        answers = response.get("answers")
        if not isinstance(answers, dict):
            raise ProviderError("invalid_response", "A resposta JEV não trouxe respostas estruturadas.", 502)
        return {"model": response.get("model") or self.model, "answers": answers, "usage": response.get("usage", {})}
