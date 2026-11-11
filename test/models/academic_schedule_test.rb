require "test_helper"

class AcademicScheduleTest < ActiveSupport::TestCase
  test "provides the original suggested task sets for each workflow" do
    assert_equal 12, AcademicSchedule.templates("case").length
    assert_equal 11, AcademicSchedule.templates("paper_project").length
    assert_equal [ "case-theme", "Escolher e delimitar o tema" ], AcademicSchedule.templates("case").first
    assert_equal [ "paper-delivery", "Preparar a entrega" ], AcademicSchedule.templates("paper_final").last
  end

  test "normalizes schedule dates and discards tasks with invalid dates" do
    result = AcademicSchedule.normalize_schedule(
      {
        "report_date" => "30/10/2026",
        "debate_date" => "invalid",
        "tasks" => [
          { "title" => " Ler ", "date" => "2026-11-01" },
          { "title" => "Inválida", "date" => "not-a-date" }
        ]
      },
      project_type: "case"
    )

    assert_equal "2026-10-30", result["report_date"]
    assert_equal "", result["debate_date"]
    assert_equal 1, result["tasks"].length
    assert_equal "Ler", result["tasks"].first["title"]
  end

  test "preserves paper deadlines and task state" do
    result = AcademicSchedule.normalize_schedule(
      {
        "deliveryDate" => "30/10/2026",
        "finalDate" => "2026-11-30",
        "tasks" => [ { "id" => "t1", "title" => "Revisar", "date" => "2026-10-29", "done" => "1", "stage" => 4, "templateKey" => "paper-review" } ]
      },
      project_type: "paper_project"
    )
    deadlines = AcademicSchedule.deadlines(result, "paper_project", project_id: "p1", title: "Paper")

    assert_equal "2026-10-30", result["report_date"]
    assert_equal "2026-11-30", result["final_date"]
    assert_equal true, result["tasks"].first["done"]
    assert_equal 4, result["tasks"].first["stage"]
    assert_equal "paper-review", result["tasks"].first["template_key"]
    assert_equal [ "Projeto de Paper", "Paper Final" ], deadlines.map { |item| item["label"] }
    assert_equal "29/10/2026", AcademicSchedule.entries(result, "paper_project", project_id: "p1", title: "Paper").last["date_label"]
  end

  test "summarizes tasks and sorts upcoming dated items" do
    schedule = {
      "report_date" => "2026-10-20",
      "final_date" => "2026-11-30",
      "tasks" => [
        { "id" => "t1", "title" => "Tarefa futura", "date" => "2026-10-28" },
        { "id" => "t2", "title" => "Tarefa concluída", "date" => "2026-10-27", "done" => true }
      ]
    }

    summary = AcademicSchedule.summary(schedule, "paper_project")
    upcoming = AcademicSchedule.upcoming(
      [ { "deadlines" => AcademicSchedule.entries(schedule, "paper_project", project_id: "p1", title: "Pesquisa") } ],
      today: Date.new(2026, 10, 26)
    )

    assert_equal 2, summary["task_total"]
    assert_equal 1, summary["task_done"]
    assert_equal [ "Projeto de Paper", "Tarefa futura", "Paper Final" ], upcoming["entries"].map { |item| item["label"] }
    assert_equal [ true, false, false ], upcoming["entries"].map { |item| item["overdue"] }
    assert_equal "2026-10-26", upcoming["today"]
  end

  test "persists schedule in a project revision" do
    project = Project.create!(
      project_type: "case",
      schedule: { "report_date" => "2026-10-30", "tasks" => [ { "title" => "Revisar", "done" => true } ] }
    )

    assert_equal "2026-10-30", project.reload.schedule["report_date"]
    assert_equal "Revisar", project.revisions.sole.snapshot.dig("schedule", "tasks", 0, "title")
  end
end
