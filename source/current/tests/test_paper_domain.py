from app.domain.paper import normalize_paper_fields, paper_progress, paper_sections


def test_paper_project_has_research_planning_stages():
    sections = paper_sections("paper_project")
    titles = [section["title"] for section in sections]
    assert titles[:3] == ["Identificação e delimitação", "Problema de pesquisa", "Hipótese"]
    progress = paper_progress({"title": "Tema", "authors": "Ana"}, "paper_project")
    assert progress["done"] == 2
    assert progress["total"] > 10


def test_paper_final_has_summary_and_writing_fields():
    fields = normalize_paper_fields({"title": "  Paper  ", "abstract": "Resumo", "unknown": "x"}, "paper_final")
    assert fields["title"] == "Paper"
    assert fields["abstract"] == "Resumo"
    assert "unknown" not in fields
    assert "Introdução" in [section["title"] for section in paper_sections("paper_final")]
