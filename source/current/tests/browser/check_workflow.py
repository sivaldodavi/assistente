"""Verificação opcional de navegador: só localhost, banco temporário e nenhuma API real.
Rodar: python3 tests/browser/check_workflow.py
Requer playwright e Chromium instalados no ambiente de desenvolvimento.
"""
from pathlib import Path
import sys
import sqlite3
import json
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import create_app
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def check_saved(page):
    page.wait_for_function("document.querySelector('[data-save-state]').textContent === 'Salvo agora'")


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Conteúdo ultrapassa a largura da tela"


with tempfile.TemporaryDirectory(prefix="assistente-ui-") as directory:
    app = create_app({"TESTING": True, "SECRET_KEY": "visual-test-only", "DATA_DIR": directory,
                      "DATABASE": str(Path(directory)/"test.sqlite3"), "ALLOW_DEV_AUTH": True,
                      "ADMIN_EMAILS": {"visual@example.test"}})
    catalog_path = Path(directory)/"catalog.sqlite3"
    with sqlite3.connect(catalog_path) as catalog:
        catalog.execute("CREATE TABLE entries (id TEXT, kind TEXT, title TEXT, reference TEXT, author TEXT, abstract TEXT, source_year INTEGER, source TEXT, search_text TEXT, payload TEXT)")
        for name, title in (("water", "ÁGUA"), ("faith", "Boa-fé objetiva")):
            catalog.execute("INSERT INTO entries VALUES (?, 'legislation', ?, 'CC, art. 422', '', '', 2023, 'Catálogo fictício', ?, ?)", (name, title, title, json.dumps({"id":name,"kind":"legislation","title":title,"reference":"CC, art. 422"})))
    app.config["RESEARCH_CATALOG_PATH"] = str(catalog_path)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    captures = Path(directory)/"captures"
    captures.mkdir()
    output = Path("/home/ubuntu/assistente-parity-captures")
    output.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base)
            page.request.post(base+"/auth/dev-login", form={"email":"visual@example.test", "name":"Pessoa de teste"})
            page.goto(base+"/account")
            assert page.get_by_text("Configure sua conta", exact=True).is_visible()
            assert page.get_by_role("link", name="Administração", exact=True).is_visible()
            page.get_by_role("link", name="Ler e aceitar", exact=True).click()
            assert page.locator('[data-profile-panel="terms"]').is_visible()
            assert page.locator('[data-profile-panel="profile"]').is_hidden()
            page.locator('input[name="accept"]').check()
            page.get_by_role("button", name="Salvar termos e consentimento", exact=True).click()
            page.get_by_role("button", name="Dados pessoais", exact=True).click()
            assert page.locator('[data-profile-panel]:visible').count() == 1
            assert page.locator('h1').evaluate("e => parseFloat(getComputedStyle(e).fontSize)") <= 32
            no_overflow(page)
            page.screenshot(path=str(output/"perfil-desktop.png"), full_page=False)
            page.goto(base+"/account")
            page.get_by_role("button", name="Criar trabalho", exact=True).click()
            case_url = page.url.split("#")[0]
            assert page.locator('[data-stage]:visible').count() == 1
            assert page.locator('[data-fact]').count() == 0
            assert page.locator('.workspace').evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length") == 2
            page.locator('[data-case-field="title"]').fill("Relatório de teste")
            check_saved(page)
            page.locator("#project-planning > summary").click()
            page.locator('[data-schedule-field="report_date"]').fill("2099-10-30")
            page.get_by_role("button", name="Usar roteiro sugerido", exact=True).click()
            assert page.locator("[data-task]").count() == 12
            page.locator('[data-task-field="done"]').first.check()
            check_saved(page)
            page.reload()
            page.locator("#project-planning > summary").click()
            assert page.locator('[data-schedule-field="report_date"]').input_value() == "2099-10-30"
            assert page.locator('[data-task-field="done"]').first.is_checked()
            page.screenshot(path=str(output/"project-schedule-desktop.png"), full_page=False)
            page.get_by_role("button", name="1 · Descrição do caso", exact=False).click()
            page.locator('[data-case-field="facts"]').fill("Narrativa de teste preservada ao mudar de etapa.")
            page.locator('[data-workflow-check="facts-original"]').check()
            check_saved(page)
            page.get_by_role("button", name="2.2.1 · Argumentação da tese A", exact=False).click()
            page.locator('[data-case-field="thesis_a"]').fill("Argumentação A com as próprias palavras.")
            check_saved(page)
            page.get_by_role("button", name="1 · Descrição do caso", exact=False).click()
            assert page.locator('[data-case-field="facts"]').input_value().startswith("Narrativa de teste")
            assert page.locator('[data-workflow-check="facts-original"]').is_checked()
            no_overflow(page)
            page.screenshot(path=str(output/"case-desktop.png"), full_page=False)
            page.get_by_role("button", name="Revisão e entrega do relatório", exact=False).click()
            review_stage = page.locator('[data-stage="review_report"]')
            assert review_stage.is_visible()
            assert review_stage.locator('.review-panel').is_visible()
            assert review_stage.get_by_text("Trilha de fundamentação", exact=True).is_visible()
            assert review_stage.get_by_role("button", name="Avaliar", exact=True).is_visible()
            assert review_stage.locator('[data-delivery-state]').is_visible()
            no_overflow(page)
            page.screenshot(path=str(output/"case-review-desktop.png"), full_page=False)
            review_stage.get_by_role("button", name="Marcar relatório como entregue", exact=True).click()
            check_saved(page)
            assert review_stage.get_by_text("Relatório marcado como entregue.", exact=True).is_visible()
            page.reload()
            review_stage = page.locator('[data-stage="review_report"]')
            assert review_stage.get_by_text("Relatório marcado como entregue.", exact=True).is_visible()
            page.set_viewport_size({"width":390,"height":844})
            assert page.locator('[data-stage]:visible').count() == 1
            no_overflow(page)
            page.get_by_role("button", name="Dissertação", exact=True).click()
            dissertation_stage = page.locator('[data-stage="dissertation"]')
            assert dissertation_stage.is_visible()
            assert dissertation_stage.get_by_text("Desenvolvimento e fundamentação", exact=True).is_visible()
            assert dissertation_stage.locator('[data-case-field="dissertation_conclusion"]').is_visible()
            page.screenshot(path=str(output/"case-mobile.png"), full_page=False)
            page.goto(case_url+"#stage-thesis_a")
            assert page.locator('[data-stage="thesis_a"]').is_visible()
            assert page.locator('[data-case-field="thesis_a"]').input_value().startswith("Argumentação A")
            exported = page.request.get(case_url+"/export?format=html&phase=report")
            assert exported.ok
            assert "Argumentação A" in exported.text()
            assert "Linha do Tempo" not in exported.text()
            page.set_viewport_size({"width":1366,"height":900})
            page.goto(base+"/account")
            assert page.get_by_role("heading", name="Agenda", exact=True).is_visible()
            assert page.get_by_text("Salvamentos por dia", exact=True).is_visible()
            assert page.get_by_text("30/10/2099", exact=True).is_visible()
            assert page.locator(f'a[href="/projects/{case_url.rsplit("/", 1)[-1]}"]').count() >= 1
            page.screenshot(path=str(output/"account-agenda-desktop.png"), full_page=False)
            page.set_viewport_size({"width":390,"height":844})
            no_overflow(page)
            page.screenshot(path=str(output/"account-agenda-mobile.png"), full_page=False)
            page.set_viewport_size({"width":1366,"height":900})
            page.locator('[name="project_type"]').select_option("paper_project")
            page.get_by_role("button", name="Criar trabalho", exact=True).click()
            page.get_by_role("button", name="Hipótese", exact=False).click()
            page.locator('[data-case-field="hypothesis"]').fill("Hipótese a preservar no Paper Final")
            check_saved(page)
            page.get_by_role("button", name="Revisão do Projeto de Paper", exact=False).click()
            page.get_by_role("button", name="Continuar para Paper Final", exact=True).click()
            page.wait_for_selector('[data-project-type="paper_final"]')
            assert page.locator('[data-stage]:visible').count() == 1
            no_overflow(page)
            page.screenshot(path=str(output/"paper-mobile.png"), full_page=False)
            page.set_viewport_size({"width":1366,"height":900})
            page.goto(base+"/library")
            add = page.locator(".library-add-form")
            add.locator('[name="title"]').fill("Fonte de teste")
            page.get_by_text("Fichamento pessoal (opcional)", exact=True).click()
            add.locator('[name="notes"]').fill("Fichamento privado de teste")
            page.get_by_role("button", name="Adicionar à biblioteca", exact=True).click()
            assert page.locator(".source-row").count() == 1
            page.get_by_role("link", name="Editar", exact=True).click()
            edit = page.locator(".source-editor[open]")
            edit.locator('[name="notes"]').fill("Fichamento revisado")
            edit.get_by_role("button", name="Salvar alterações", exact=True).click()
            page.get_by_text("Fichamento pessoal", exact=True).click()
            assert page.locator(".source-note p").filter(has_text="Fichamento revisado").is_visible()
            no_overflow(page)
            page.screenshot(path=str(output/"biblioteca-desktop.png"), full_page=False)
            assert not page.get_by_text("Índice alfabético-remissivo", exact=True).count()
            page.set_viewport_size({"width":390,"height":844})
            no_overflow(page)
            page.screenshot(path=str(output/"biblioteca-mobile.png"), full_page=False)
            page.goto(base+"/admin/accounts")
            assert page.get_by_role("heading", name="Contas, planos e acesso", exact=True).is_visible()
            no_overflow(page)
            page.screenshot(path=str(output/"admin-mobile.png"), full_page=False)
            assert not errors, errors
            browser.close()
            print("OK: perfil, etapas Case/Paper, autosave, conferências, exportação, biblioteca/fichamento e administração; desktop/celular.")
            print(f"Capturas locais: {output}")
    finally:
        server.shutdown()
