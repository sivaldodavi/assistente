require "test_helper"

class ProjectTest < ActiveSupport::TestCase
  test "does not persist the removed manual schedule" do
    assert_not_includes Project.column_names, "schedule"
  end

  test "new projects start at the first guided step and normalize title" do
    project = Project.create!(project_type: "case")

    assert_equal "identification", project.current_stage
    assert_equal "Novo Case", project.title
    assert_equal({}, project.fields.except(*AcademicWorkflow.field_rules("case").keys))
  end

  test "project paper can transition without losing its planning answers" do
    project = Project.create!(
      project_type: "paper_project",
      fields: { "title" => "Tema", "hypothesis" => "Resposta provisória" }
    )
    project.project_type = "paper_final"
    project.current_stage = "paper_final_identity"
    project.save!

    assert_equal "Tema", project.fields["title"]
    assert_equal "Resposta provisória", project.fields["hypothesis"]
    assert_includes project.sections.map { |section| section["id"] }, "paper_final_introduction"
  end

  test "revision snapshots are stored against the optimistic lock version" do
    project = Project.create!(project_type: "case")
    revision = project.revisions.sole

    assert_equal project.lock_version, revision.revision
    assert_equal "case", revision.snapshot["project_type"]
  end

  test "normalizes criteria and development sections within source limits" do
    project = Project.create!(
      project_type: "paper_final",
      criteria: [ { "title" => "  Dignidade ", "definition" => "x" * 3_100, "unknown" => "drop" } ],
      development_sections: [ { "title" => "Fundamentação", "body" => "Texto" } ]
    )

    assert_equal "Dignidade", project.criteria.first["title"]
    assert_equal 3_000, project.criteria.first["definition"].length
    assert_not_includes project.criteria.first, "unknown"
    assert_equal "Texto", project.development_sections.first["body"]
  end

  test "rejects delivery dates that are not valid calendar dates" do
    project = Project.new(project_type: "case", fields: { "report_delivery_date" => "2026-13-40" })

    refute project.valid?
    assert_includes project.errors.full_messages.join(" "), "Data de entrega do relatório inválida"
  end

  test "warns about delivery order without blocking the project" do
    project = Project.new(project_type: "case", fields: {
      "report_delivery_date" => "2026-10-20",
      "debate_delivery_date" => "2026-10-10"
    })

    assert project.valid?
    assert_includes project.schedule_warnings, "A entrega do relatório é depois da data do debate."
  end
end
