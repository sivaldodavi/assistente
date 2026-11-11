from urllib.parse import parse_qs, urlsplit

from app.services.google_oauth import GoogleOAuthClient, valid_redirect_uri


def configure_google(app):
    app.config.update({
        "GOOGLE_CLIENT_ID": "client-id",
        "GOOGLE_CLIENT_SECRET": "client-secret",
        "GOOGLE_REDIRECT_URI": "https://example.test/oauth/google/callback",
    })


def test_google_start_requires_configuration(client):
    response = client.get("/oauth/google/start")
    assert response.status_code == 302
    assert "google_login=unconfigured" in response.headers["Location"]


def test_google_start_uses_state_nonce_and_pkce(app):
    configure_google(app)
    with app.test_client() as client:
        response = client.get("/oauth/google/start")
        assert response.status_code == 302
        query = parse_qs(urlsplit(response.headers["Location"]).query)
        assert query["client_id"] == ["client-id"]
        assert query["code_challenge_method"] == ["S256"]
        assert len(query["state"][0]) >= 32
        assert len(query["nonce"][0]) >= 32
        assert len(query["code_challenge"][0]) == 43
        with client.session_transaction() as session:
            flow = session["google_oauth"]
        assert flow["state"] == query["state"][0]
        assert flow["nonce"] == query["nonce"][0]


def test_google_callback_uses_fake_verified_claims(app, monkeypatch):
    configure_google(app)
    claims = {"sub": "google-sub", "email": "ana@example.test", "name": "Ana"}
    monkeypatch.setattr(GoogleOAuthClient, "exchange_code", lambda self, code, verifier, nonce: claims)
    with app.test_client() as client:
        start = client.get("/oauth/google/start")
        query = parse_qs(urlsplit(start.headers["Location"]).query)
        callback = client.get(f"/oauth/google/callback?state={query['state'][0]}&code=fake-code")
        assert callback.status_code == 302
        assert callback.headers["Location"].endswith("/account")
        with client.session_transaction() as session:
            assert session["account_id"]
            assert session["csrf_token"]


def test_google_redirect_validation_rejects_external_http_and_query_strings():
    assert valid_redirect_uri("https://example.test/oauth/google/callback")
    assert valid_redirect_uri("http://localhost:5000/oauth/google/callback")
    assert not valid_redirect_uri("http://example.test/oauth/google/callback")
    assert not valid_redirect_uri("https://example.test/oauth/google/callback?next=/")
    assert not valid_redirect_uri("https://example.test/other")


def test_google_callback_rejects_state_mismatch(app):
    configure_google(app)
    with app.test_client() as client:
        client.get("/oauth/google/start")
        response = client.get("/oauth/google/callback?state=wrong&code=fake-code")
        assert response.status_code == 302
        assert "google_login=failed" in response.headers["Location"]
        with client.session_transaction() as session:
            assert "google_oauth" not in session
