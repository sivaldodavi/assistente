from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class GoogleOAuthError(Exception):
    """Erro esperado ao iniciar ou validar um fluxo OAuth Google."""


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint: str = "https://oauth2.googleapis.com/token"

    @classmethod
    def from_mapping(cls, mapping):
        return cls(
            client_id=str(mapping.get("GOOGLE_CLIENT_ID", "") or "").strip(),
            client_secret=str(mapping.get("GOOGLE_CLIENT_SECRET", "") or "").strip(),
            redirect_uri=str(mapping.get("GOOGLE_REDIRECT_URI", "") or "").strip(),
        )

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret and valid_redirect_uri(self.redirect_uri))


def valid_redirect_uri(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return (
            parsed.scheme in {"https", "http"}
            and bool(parsed.hostname)
            and parsed.path == "/oauth/google/callback"
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and (port is None or 1 <= port <= 65535)
            and (parsed.scheme == "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"})
        )
    except ValueError:
        return False


def new_state() -> str:
    return secrets.token_urlsafe(32)


def new_nonce() -> str:
    return secrets.token_urlsafe(32)


def new_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class GoogleOAuthClient:
    def __init__(self, config: GoogleOAuthConfig):
        self.config = config

    def authorization_url(self, state: str, nonce: str, code_verifier: str) -> str:
        if not self.config.configured:
            raise GoogleOAuthError("google_login_unconfigured")
        query = urlencode({
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(code_verifier),
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        })
        return f"{self.config.authorization_endpoint}?{query}"

    def exchange_code(self, code: str, code_verifier: str, expected_nonce: str) -> dict:
        if not self.config.configured:
            raise GoogleOAuthError("google_login_unconfigured")
        if not code or len(code) > 2048 or not code_verifier:
            raise GoogleOAuthError("google_state_failed")
        body = urlencode({
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }).encode("ascii")
        request = Request(
            self.config.token_endpoint,
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload_bytes = response.read(64 * 1024 + 1)
            if len(payload_bytes) > 64 * 1024:
                raise ValueError("OAuth response too large")
            payload = json.loads(payload_bytes)
        except (HTTPError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise GoogleOAuthError("google_token_exchange_failed") from error
        token = payload.get("id_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise GoogleOAuthError("google_token_exchange_failed")
        return self.verify_id_token(token, expected_nonce)

    def verify_id_token(self, token: str, expected_nonce: str) -> dict:
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token
        except ImportError as error:
            raise GoogleOAuthError("google_verifier_unavailable") from error
        try:
            claims = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.config.client_id,
            )
        except Exception as error:
            raise GoogleOAuthError("invalid_google_credential") from error
        if (
            not isinstance(claims, dict)
            or claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or claims.get("email_verified") is not True
            or not isinstance(claims.get("sub"), str)
            or not claims["sub"]
            or len(claims["sub"]) > 255
            or not isinstance(claims.get("email"), str)
            or not claims["email"].strip()
            or not isinstance(claims.get("nonce"), str)
            or not secrets.compare_digest(claims["nonce"], expected_nonce)
        ):
            raise GoogleOAuthError("invalid_google_credential")
        return {
            "sub": claims["sub"],
            "email": claims["email"].strip().lower(),
            "name": claims.get("name", "") if isinstance(claims.get("name"), str) else "",
        }
