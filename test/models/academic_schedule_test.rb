require "test_helper"

class AcademicScheduleTest < ActiveSupport::TestCase
  test "keeps only task due dates and discards invalid task dates" do
    result = AcademicSchedule.normalize_schedule(
      {
        "report_date" => "30/10/2026",
        "debate_date" => "invalid",
        "tasks" => [
          { "title" => " Ler ", "date" => "2026-11-01", "done" => "1", "stage" => 2, "template_key" => "old" },
          { "title" => "Inválida", "date" => "not-a-date" }
        ]
      }
    )

    assert_equal [ "tasks" ], result.keys
    assert_equal 1, result["tasks"].length
    assert_equal "Ler", result["tasks"].first["title"]
    assert_equal "2026-11-01", result["tasks"].first["date"]
    assert_equal true, result["tasks"].first["done"]
    assert_not_includes result["tasks"].first, "stage"
    assert_not_includes result["tasks"].first, "template_key"
  end

  test "counts tasks without calculating project deadlines" do
    result = AcademicSchedule.normalize_schedule(
      {
        "deliveryDate" => "30/10/2026",
        "finalDate" => "2026-11-30",
        "tasks" => [ { "id" => "t1", "title" => "Revisar", "date" => "2026-10-29", "done" => "1" } ]
      }
    )
    assert_equal true, result["tasks"].first["done"]
    assert_equal({ "task_total" => 1, "task_done" => 1 }, AcademicSchedule.summary(result))
  end

  test "shows only task due dates in the upcoming list" do
    schedule = {
      "report_date" => "2026-10-20",
      "final_date" => "2026-11-30",
      "tasks" => [
        { "id" => "overdue", "title" => "Entregar rascunho", "date" => "2026-10-20" },
        { "id" => "t1", "title" => "Tarefa futura", "date" => "2026-10-28" },
        { "id" => "t2", "title" => "Tarefa concluída", "date" => "2026-10-27", "done" => true }
      ]
    }

    upcoming = AcademicSchedule.upcoming(
      [ { "id" => "p1", "title" => "Pesquisa", "schedule" => schedule } ],
      today: Date.new(2026, 10, 26)
    )

    assert_equal [ "Entregar rascunho", "Tarefa futura" ], upcoming["entries"].map { |item| item["label"] }
    assert_equal [ true, false ], upcoming["entries"].map { |item| item["overdue"] }
    assert_equal "2026-10-26", upcoming["today"]
  end

  test "persists schedule in a project revision" do
    project = Project.create!(
      project_type: "case",
      schedule: { "report_date" => "2026-10-30", "tasks" => [ { "title" => "Revisar", "date" => "2026-10-31", "done" => true } ] }
    )

    assert_equal [ "tasks" ], project.reload.schedule.keys
    assert_equal "Revisar", project.revisions.sole.snapshot.dig("schedule", "tasks", 0, "title")
    assert_equal "2026-10-31", project.schedule.dig("tasks", 0, "date")
  end
end
