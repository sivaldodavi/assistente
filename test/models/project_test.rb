require "test_helper"

class ProjectTest < ActiveSupport::TestCase
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
      project_type: "case",
      criteria: [ { "title" => "  Dignidade ", "definition" => "x" * 3_100, "unknown" => "drop" } ],
      development_sections: [ { "title" => "Fundamentação", "body" => "Texto" } ]
    )

    assert_equal "Dignidade", project.criteria.first["title"]
    assert_equal 3_000, project.criteria.first["definition"].length
    assert_not_includes project.criteria.first, "unknown"
    assert_equal "Texto", project.development_sections.first["body"]
  end
end
