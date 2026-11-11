import pytest

from app.services.export import ExportUnavailable, build_project_html, build_typst_source, render_pdf


def login_and_terms(client):
    client.post("/auth/dev-login", data={"email": "export@example.test", "name": "Exportação"})
    with client.session_transaction() as session:
        token = session["csrf_token"]
    client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on"})


def test_html_export_escapes_user_content():
    html = build_project_html(
        {"project_type": "case", "fields": {"title": "<script>não</script>", "facts": "Fato"}, "criteria": []},
        [],
    )
    assert "&lt;script&gt;não&lt;/script&gt;" in html
    assert "<script>não</script>" not in html
    assert "Descrição do caso" in html


def test_paper_export_uses_paper_sections():
    html = build_project_html(
        {"project_type": "paper_final", "fields": {"title": "Paper", "abstract": "Resumo do paper"}, "criteria": []},
        [],
    )
    assert "Identificação, resumo e palavras-chave" in html
    assert "Resumo do paper" in html
    assert "Descrição do caso" not in html


def test_project_html_export_requires_login(client):
    response = client.get("/projects/unknown/export?format=html")
    assert response.status_code == 302


def test_typst_export_uses_the_abnt_extension_from_the_reference_project():
    source = build_typst_source(
        {
            "project_type": "case",
            "fields": {
                "title": "Case de teste",
                "authors": "Autor de teste",
                "institution": "Instituição",
                "course": "Curso",
                "discipline": "Disciplina",
                "teacher": "Professor",
                "facts": "Fatos do caso",
                "problem": "Qual é o problema?",
            },
            "criteria": [],
        },
        [],
    )
    assert "format: abnt-typst" in source
    assert '#import "_extensions/abnt/tipos/caso.typ": *' in source
    assert "tinytex" not in source.lower()


def test_case_pdf_is_not_offered_for_non_report_phases():
    with pytest.raises(ExportUnavailable, match="fase Relatório"):
        render_pdf({"project_type": "case", "export_phase": "dissertation", "fields": {}}, [])


def test_project_html_export_works_for_owned_project(client):
    login_and_terms(client)
    with client.session_transaction() as session:
        token = session["csrf_token"]
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    response = client.get(f"/projects/{project_id}/export?format=html")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "Linha do Tempo dos Fatos" not in response.get_data(as_text=True)
    assert "Descrição do caso" in response.get_data(as_text=True)


def test_project_export_rejects_unknown_format(client):
    login_and_terms(client)
    with client.session_transaction() as session:
        token = session["csrf_token"]
    created = client.post("/projects", data={"csrf_token": token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    assert client.get(f"/projects/{project_id}/export?format=doc").status_code == 400
