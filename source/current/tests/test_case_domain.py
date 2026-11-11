from app.domain.case import case_progress, missing_case_fields, normalize_case_fields, normalize_criteria


def test_case_progress_only_counts_required_fields():
    fields = {"title": "Case", "authors": "Ana", "discipline": "Direito", "teacher": "Prof."}
    progress = case_progress(fields)
    assert progress["done"] == 4
    assert progress["total"] == 13
    assert progress["percent"] == 31


def test_case_normalization_keeps_known_fields_and_bounds_text():
    fields = normalize_case_fields({"title": "  Case  ", "facts": "X" * 20000, "unknown": "não persistir"})
    assert fields["title"] == "Case"
    assert len(fields["facts"]) == 16000
    assert "unknown" not in fields


def test_case_missing_fields_are_explicit():
    missing = missing_case_fields({"title": "Case"})
    assert missing[:3] == ["authors", "discipline", "teacher"]
    assert "facts" in missing
    assert "decision_b" in missing


def test_criteria_are_bounded_and_empty_rows_are_ignored():
    criteria = normalize_criteria([
        {"id": "one", "title": "  Ponderação  ", "definition": "Definição", "basis": "CF"},
        {"id": "empty", "title": "", "definition": "", "basis": ""},
        "ignorar",
    ])
    assert criteria == [{"id": "one", "title": "Ponderação", "definition": "Definição", "basis": "CF"}]
