from datetime import date

from app.domain.schedule import account_calendar, normalize_schedule, schedule_deadlines


def test_schedule_normalizes_dates_and_discards_invalid_tasks():
    result = normalize_schedule({"report_date": "2026-10-30", "debate_date": "bad", "tasks": [{"title": "Ler", "date": "2026-11-01"}, {"title": "Inválida", "date": "x"}]})
    assert result["report_date"] == "2026-10-30"
    assert result["debate_date"] == ""
    assert len(result["tasks"]) == 1


def test_schedule_is_empty_for_unknown_payload():
    assert normalize_schedule({"report_date": "30/10/2026"})["tasks"] == []


def test_paper_schedule_keeps_project_and_final_dates_and_task_state():
    result = normalize_schedule(
        {
            "deliveryDate": "30/10/2026",
            "finalDate": "2026-11-30",
            "tasks": [{"id": "t1", "title": "Revisar", "date": "2026-10-29", "done": True, "templateKey": "paper-review"}],
        },
        project_type="paper_project",
    )
    assert result["report_date"] == "2026-10-30"
    assert result["final_date"] == "2026-11-30"
    assert result["tasks"][0]["done"] is True
    assert result["tasks"][0]["template_key"] == "paper-review"
    assert [item["label"] for item in schedule_deadlines(result, "paper_project", "p1", "Paper")] == ["Projeto de Paper", "Paper Final"]


def test_account_calendar_groups_dates_and_upcoming_entries():
    projects = [{
        "deadlines": schedule_deadlines(
            {"report_date": "2026-10-30", "final_date": "2026-11-30"},
            "paper_project",
            "p1",
            "Pesquisa",
        )
    }]
    result = account_calendar(projects, date(2026, 10, 26))
    assert result["has_dates"] is True
    assert result["month_label"] == "outubro de 2026"
    assert result["upcoming"][0]["label"] == "Projeto de Paper"
    assert any(cell.get("entries") for cell in result["cells"] if cell)

    future_only = account_calendar(
        [{"deadlines": schedule_deadlines({"final_date": "2026-11-30"}, "paper_final", "p1", "Pesquisa")}],
        date(2026, 10, 26),
    )
    assert future_only["has_dates"] is True
    assert future_only["month_has_dates"] is False


def test_account_calendar_heatmap_uses_edit_counts_not_planned_dates():
    result = account_calendar(
        [],
        [{"date": "2026-10-26", "count": 1}, {"date": "2026-10-27", "count": 7}],
        date(2026, 10, 27),
    )
    cells = {cell["number"]: cell for cell in result["cells"] if cell}
    assert result["has_dates"] is False
    assert result["has_activity"] is True
    assert cells[26]["edit_count"] == 1
    assert cells[26]["edit_level"] == 1
    assert cells[27]["edit_count"] == 7
    assert cells[27]["edit_level"] == 4
