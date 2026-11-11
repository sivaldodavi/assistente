require "test_helper"
require "digest"

class AcademicWorkflowTest < ActiveSupport::TestCase
  WORKFLOW_SHA256 = "19ee277dc9bf9bd9686b7d98a91794deaf099aafe30ecb9e462e8c639233d777"

  test "workflow specification remains byte-for-byte identical to the recovered source" do
    path = Rails.root.join("config/academic_workflows.json")

    assert_equal WORKFLOW_SHA256, Digest::SHA256.file(path).hexdigest
  end

  test "keeps all original route stages and fields" do
    assert_equal 10, AcademicWorkflow.sections("case").length
    assert_equal 9, AcademicWorkflow.sections("paper_project").length
    assert_equal 6, AcademicWorkflow.sections("paper_final").length
    field_count = AcademicWorkflow.types.sum do |type|
      AcademicWorkflow.sections(type).sum { |section| section.fetch("fields", []).length }
    end
    assert_equal 73, field_count
    assert_equal %w[identification description decisions thesis_argumentation criteria sources review_report debate dissertation review_dissertation],
      AcademicWorkflow.sections("case").map { |section| section["id"] }
    assert_equal "Pergunta-problema", AcademicWorkflow.sections("case")[1]["fields"][1]["label"]
  end

  test "normalizes fields, limits, and select values using the source contract" do
    fields = AcademicWorkflow.normalize_fields("case", {
      "title" => "  Meu Case  ",
      "profile" => "unknown",
      "assignment_prompt" => "x" * 12_050,
      "unlisted_field" => "discard"
    })

    assert_equal "Meu Case", fields["title"]
    assert_equal "", fields["profile"]
    assert_equal 12_000, fields["assignment_prompt"].length
    assert_not_includes fields, "unlisted_field"
  end

  test "progress counts required fields only for the selected phase" do
    report = AcademicWorkflow.progress("case", {}, "report")
    dissertation = AcademicWorkflow.progress("case", {}, "dissertation")

    assert_equal 13, report["total"]
    assert_equal 3, dissertation["total"]
    assert_equal 0, report["done"]
    assert_equal 100, AcademicWorkflow.progress("case", {}, "unknown")["percent"]
  end

  test "checklists discard unknown keys and normalize submitted checkboxes" do
    checks = AcademicWorkflow.normalize_checks("case", {
      "facts-original" => "1",
      "made-up" => true
    })

    assert_equal true, checks["facts-original"]
    assert_equal false, checks["facts-neutral"]
    assert_not_includes checks, "made-up"
  end
end
