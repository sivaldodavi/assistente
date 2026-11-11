def login(client, email):
    response = client.post("/auth/dev-login", data={"email": email, "name": "Leitor"})
    assert response.status_code == 302


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_library_adds_and_lists_source(client):
    login(client, "biblioteca@example.test")
    response = client.get("/library")
    assert response.status_code == 200
    assert "Biblioteca Pessoal" in response.get_data(as_text=True)
    response = client.post(
        "/library/sources",
        data={
            "csrf_token": csrf(client),
            "title": "Teoria do Direito",
            "author": "Autoria Exemplo",
            "kind": "book",
            "reference": "São Paulo, 2026",
            "notes": "Usar no capítulo inicial.",
        },
    )
    assert response.status_code == 302
    assert "Teoria do Direito" in client.get("/library").get_data(as_text=True)


def test_library_does_not_expose_other_account_sources(client):
    login(client, "primeira@example.test")
    client.post("/library/sources", data={"csrf_token": csrf(client), "title": "Privada"})
    client.post("/auth/logout", data={"csrf_token": csrf(client)})
    login(client, "segunda@example.test")
    assert "Privada" not in client.get("/library").get_data(as_text=True)


def test_library_edits_source_and_private_fichamento(client):
    login(client, "editar@example.test")
    response = client.post(
        "/library/sources",
        data={
            "csrf_token": csrf(client),
            "title": "Título inicial",
            "kind": "book",
            "notes": "Anotação inicial",
        },
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        account_id = session["account_id"]
    from app.store.sources import list_sources

    with client.application.app_context():
        source_id = list_sources(account_id)[0]["id"]
    response = client.post(
        f"/library/sources/{source_id}",
        data={
            "csrf_token": csrf(client),
            "title": "Título revisado",
            "author": "Autoria revisada",
            "kind": "article",
            "reference": "Revista, 2026",
            "notes": "Fichamento privado revisado",
        },
    )
    assert response.status_code == 302
    page = client.get("/library").get_data(as_text=True)
    assert "Título revisado" in page
    assert "Fichamento privado revisado" in page
    assert "Título inicial" not in page


def test_library_delete_is_owner_scoped(client):
    login(client, "dona@example.test")
    client.post("/library/sources", data={"csrf_token": csrf(client), "title": "Fonte protegida"})
    with client.session_transaction() as session:
        owner_id = session["account_id"]
    from app.store.sources import list_sources

    with client.application.app_context():
        source_id = list_sources(owner_id)[0]["id"]
    client.post("/auth/logout", data={"csrf_token": csrf(client)})
    login(client, "outra@example.test")
    response = client.post(
        f"/library/sources/{source_id}/delete",
        data={"csrf_token": csrf(client)},
    )
    assert response.status_code == 404
    client.post("/auth/logout", data={"csrf_token": csrf(client)})
    login(client, "dona@example.test")
    response = client.post(
        f"/library/sources/{source_id}/delete",
        data={"csrf_token": csrf(client)},
    )
    assert response.status_code == 302
    assert "Fonte protegida" not in client.get("/library").get_data(as_text=True)


def test_library_only_shows_personal_sources_not_catalog_search(client):
    login(client, "sem-indice@example.test")
    page = client.get("/library").get_data(as_text=True)
    assert "Minhas fontes" not in page
    assert "Índice alfabético-remissivo" not in page
    assert "data-research-form" not in page
    # Catalog endpoint exists but returns 503 when catalog is not mounted
    assert client.get("/api/research/catalog?q=contrato").status_code == 503
