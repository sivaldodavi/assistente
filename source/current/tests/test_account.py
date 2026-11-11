def login(client):
    response = client.post("/auth/dev-login", data={"email": "perfil@example.test", "name": "Perfil"})
    assert response.status_code == 302


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_account_home_shows_first_login_setup(client):
    login(client)
    page = client.get("/account")
    body = page.get_data(as_text=True)
    assert "Configure sua conta" in body
    assert "Termos de uso e privacidade" in body
    assert "#terms" in body
    assert "Planos e valores" in body
    assert 'href="/planos"' in body
    assert 'value="paper_final"' not in body
    assert "Roteiro inicial" in body
    assert "Case — relatório, debate e dissertação" in body
    assert "Paper — começar pelo Projeto de Paper" in body
    assert "Paper: Projeto de Paper → Paper Final." in body


def test_profile_is_saved_separately_from_identity(client):
    login(client)
    response = client.post(
        "/account/settings/profile",
        data={
            "csrf_token": csrf(client),
            "name": "Perfil Atualizado",
            "institution": "Universidade",
            "course": "Direito",
            "discipline": "Metodologia",
            "professor": "Orientação",
        },
    )
    assert response.status_code == 302
    page = client.get("/account/settings")
    body = page.get_data(as_text=True)
    assert "Perfil Atualizado" in body
    assert "Universidade" in body


def test_terms_and_ai_consent_are_separate(client):
    login(client)
    response = client.post(
        "/account/settings/terms",
        data={"csrf_token": csrf(client), "accept": "on"},
    )
    assert response.status_code == 302
    page = client.get("/account/settings")
    body = page.get_data(as_text=True)
    assert 'name="accept"' in body
    assert 'name="ai_consent"' in body

    response = client.post(
        "/account/settings/terms",
        data={"csrf_token": csrf(client), "accept": "on", "ai_consent": "on"},
    )
    assert response.status_code == 302
    page = client.get("/account/settings")
    assert "Autorizo o uso da assistência de IA" in page.get_data(as_text=True)
