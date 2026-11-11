import json
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "public-navigation-test",
            "DATA_DIR": str(tmp_path),
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "ALLOW_DEV_AUTH": True,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.mark.parametrize("path", ["/termos", "/termos/", "/privacidade", "/privacidade/", "/ajuda-ia", "/ajuda-ia/", "/jornada", "/jornada/"])
def test_public_document_routes_are_reachable(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert "Assistente Acadêmico" in response.get_data(as_text=True)


def test_public_home_uses_real_routes_and_no_old_site_hash(client):
    html = client.get("/").get_data(as_text=True)

    assert "#/site" not in html
    assert 'href="/termos/"' in html
    assert 'href="/privacidade/"' in html
    assert 'href="/ajuda-ia/"' in html
    assert 'href="/jornada/"' in html
    assert html.count("<main") == 1
    assert 'href="/oauth/google/start"' in html
    assert "Começar com Google" in html


def test_plans_have_a_direct_destination(client):
    response = client.get("/planos")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'class="sales-page pricing-only"' in body
    assert "Planos" in body
    assert "Voltar à apresentação" in body


def test_authenticated_home_points_to_account_instead_of_google(client):
    with client.session_transaction() as session:
        session["account_id"] = "temporary-account"

    html = client.get("/").get_data(as_text=True)

    assert 'href="/account"' in html
    assert "Minha conta" in html
    assert "Meus trabalhos" in html
    assert "Começar com Google" not in html
    assert 'href="/oauth/google/start"' not in html


def test_demo_buttons_have_all_legacy_public_models_and_safe_payload(client):
    html = client.get("/").get_data(as_text=True)
    data = json.loads(html.split('<script id="public-demo-data" type="application/json">', 1)[1].split("</script>", 1)[0])
    model_ids = {model["id"] for model in data}

    assert model_ids == {"civil-personality", "projeto-paper-modelo", "paper-final-modelo"}
    for model_id in model_ids:
        assert f'data-model-workflow="{model_id}"' in html
    assert 'data-model-document="civil-personality"' in html
    assert 'data-model-workflow="projeto-paper-modelo"' in html
    assert 'data-model-workflow="paper-final-modelo"' in html
    assert "public-demo-dialog" in html
    assert len(next(model for model in data if model["id"] == "civil-personality")["sections"]) >= 5
    assert "ADPF 130/DF" in html
    assert "FACSUR" in html
    assert "quote" not in html
    for model in data:
        assert len(model["stages"]) >= 6
        assert any(field.get("value") for field in model["stages"][0].get("fields", []))
    assert "data-public-model-step" in Path("static/js/app.js").read_text(encoding="utf-8")


def test_filled_models_keep_their_original_workflow(client):
    html = client.get("/").get_data(as_text=True)
    data = json.loads(html.split('<script id="public-demo-data" type="application/json">', 1)[1].split("</script>", 1)[0])
    models = {model["id"]: model for model in data}
    assert models["civil-personality"]["stages"][2]["title"] == "2.1 · Decisões possíveis"
    assert models["projeto-paper-modelo"]["stages"][0]["title"] == "Identificação e delimitação"
    assert models["paper-final-modelo"]["stages"][0]["title"] == "Identificação, resumo e palavras-chave"


def test_filled_models_attach_legacy_text_to_the_matching_stage(client):
    html = client.get("/").get_data(as_text=True)
    data = json.loads(html.split('<script id="public-demo-data" type="application/json">', 1)[1].split("</script>", 1)[0])
    models = {model["id"]: model for model in data}

    case_stages = models["civil-personality"]["stages"]
    assert case_stages[1]["demo_sections"][0]["title"] == "1 DESCRIÇÃO DO CASO"
    assert case_stages[2]["demo_sections"][0]["title"] == "2.1. Descrição das decisões possíveis"
    assert "liberdade de expressão" in case_stages[3]["demo_sections"][0]["title"].lower()
    assert "interesse público" in case_stages[4]["demo_sections"][0]["title"].lower()
    assert case_stages[5]["demo_sections"][0]["title"] == "2.3. Descrição dos critérios e valores"

    paper_stages = models["projeto-paper-modelo"]["stages"]
    paper_fields = {field["id"]: field["value"] for field in paper_stages[0]["fields"]}
    assert paper_fields["delimitation"]
    assert paper_fields["research_context"]
    assert paper_fields["research_object"]
    assert paper_stages[1]["demo_sections"][0]["title"] == "3 PROBLEMA"
    assert paper_stages[7]["demo_sections"][0]["title"] == "9 REFERÊNCIAS"

    final_stages = models["paper-final-modelo"]["stages"]
    assert final_stages[1]["demo_sections"][0]["title"] == "1 INTRODUÇÃO"
    assert len(final_stages[2]["demo_sections"]) == 3
    assert final_stages[3]["demo_sections"][0]["title"] == "5 CONCLUSÃO"
    assert final_stages[4]["demo_sections"][0]["title"] == "REFERÊNCIAS"


def test_document_pages_do_not_nest_main_elements(client):
    for path in ("/termos/", "/privacidade/", "/ajuda-ia/", "/jornada/"):
        html = client.get(path).get_data(as_text=True)
        assert html.count("<main") == 1, path
        assert "<main class=\"shell sales-shell\"" not in html, path


@pytest.mark.parametrize("filename", ["avulso-ai.svg", "sem-ia.svg", "com-ia.svg"])
def test_existing_pix_assets_are_served_without_copying_new_payment(client, filename):
    response = client.get(f"/pix/{filename}")
    assert response.status_code == 200
    assert response.content_type.startswith("image/svg+xml")
    assert response.data.startswith(b"<?xml")


def test_pix_asset_route_is_allowlisted(client):
    assert client.get("/pix/extra-completo.svg").status_code == 404
    assert client.get("/pix/not-an-asset.svg").status_code == 404


def test_public_js_contains_handlers_for_demo_and_pix_actions():
    source = Path("static/js/app.js").read_text(encoding="utf-8")
    assert "data-model-workflow" in source
    assert "data-model-document" in source
    assert "data-pix-copy" in source
    assert "public-demo-dialog" in source
    assert "Etapas do modelo preenchido" in source
