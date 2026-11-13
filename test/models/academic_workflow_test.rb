require "test_helper"

class AcademicWorkflowTest < ActiveSupport::TestCase
  test "keeps workflow stages while using account defaults and duo-only author entry" do
    assert_equal 10, AcademicWorkflow.sections("case").length
    assert_equal 9, AcademicWorkflow.sections("paper_project").length
    assert_equal 6, AcademicWorkflow.sections("paper_final").length
    field_count = AcademicWorkflow.types.sum do |type|
      AcademicWorkflow.sections(type).sum { |section| section.fetch("fields", []).length }
    end
    assert_equal 65, field_count
    fields = AcademicWorkflow.types.flat_map do |type|
      AcademicWorkflow.sections(type).flat_map { |section| section.fetch("fields", []) }
    end
    field_ids = fields.map { |field| field["id"] }
    assert_not_includes field_ids, "authors"
    assert_not_includes field_ids, "dissertation_author"
    assert_not_includes field_ids, "profile"
    assert_not_includes field_ids, "institution"
    assert_not_includes field_ids, "thesis_a"
    assert_not_includes field_ids, "thesis_b"
    assert_not_includes field_ids, "dissertation_intro"
    assert_not_includes field_ids, "dissertation_conclusion"
    assert_equal 1, field_ids.count("dissertation")
    assert_equal "select", fields.find { |field| field["id"] == "discipline" }["type"]
    assert_equal "disciplines", fields.find { |field| field["id"] == "discipline" }["source"]
    assert_equal "select", fields.find { |field| field["id"] == "teacher" }["type"]
    assert_equal "teachers", fields.find { |field| field["id"] == "teacher" }["source"]
    assert_equal %w[identification description decisions thesis_argumentation criteria sources review_report debate dissertation review_dissertation],
      AcademicWorkflow.sections("case").map { |section| section["id"] }
    assert_equal "Pergunta-problema", AcademicWorkflow.sections("case")[1]["fields"][1]["label"]
    assert_equal "reuse_decisions", AcademicWorkflow.sections("case").find { |section| section["id"] == "thesis_argumentation" }["custom"]
  end

  test "normalizes fields, limits, and select values using the source contract" do
    fields = AcademicWorkflow.normalize_fields("case", {
      "title" => "  Meu Case  ",
      "profile" => "unknown",
      "assignment_prompt" => "x" * 12_050,
      "report_delivery_date" => "2026-02-30",
      "debate_delivery_date" => "2026-11-30",
      "unlisted_field" => "discard"
    })

    assert_equal "Meu Case", fields["title"]
    assert_not_includes fields, "profile"
    assert_equal 12_000, fields["assignment_prompt"].length
    assert_equal "", fields["report_delivery_date"]
    assert_equal "2026-11-30", fields["debate_delivery_date"]
    assert_not_includes fields, "unlisted_field"

    paper_fields = AcademicWorkflow.normalize_fields("paper_project", {
      "report_delivery_date" => "2026-11-30"
    })
    assert_not_includes paper_fields, "report_delivery_date"
  end

  test "progress counts required fields only for the selected phase" do
    report = AcademicWorkflow.progress("case", {}, "report")
    dissertation = AcademicWorkflow.progress("case", {}, "dissertation")

    assert_equal 10, report["total"]
    assert_equal 1, dissertation["total"]
    assert_equal 0, report["done"]
    assert_equal 100, AcademicWorkflow.progress("case", {}, "unknown")["percent"]
  end

  test "keeps the argumentation fields of step 2.2 for each alternative" do
    fields = AcademicWorkflow.normalize_fields("case", {
      "argument_a" => "Fundamentos da alternativa a).",
      "argument_b" => "Fundamentos da alternativa b).",
      "thesis_a" => "Campo antigo"
    })

    assert_equal "Fundamentos da alternativa a).", fields["argument_a"]
    assert_equal "Fundamentos da alternativa b).", fields["argument_b"]
    assert_not_includes fields, "thesis_a"
  end

  test "argument fields take the title of the alternative they argue for" do
    values = { "decision_a" => "Reconhecimento do direito à eutanásia;", "decision_b" => "" }
    rules = AcademicWorkflow.field_rules("case")

    assert_equal "Reconhecimento do direito à eutanásia", AcademicWorkflow.field_label(values, rules["argument_a"])
    assert_equal "Alternativa b)", AcademicWorkflow.field_label(values, rules["argument_b"])
  end

  test "discards author and decision fields that are not part of the current workflow" do
    fields = AcademicWorkflow.normalize_fields("case", {
      "author" => "Nome da conta",
      "authors" => "Autora antiga",
      "dissertation_author" => "Nome anterior",
      "partner" => "Colega",
      "decision_a" => "Decisão atual",
      "thesis_a" => "Alternativa antiga"
    })

    assert_not_includes fields, "author"
    assert_not_includes fields, "authors"
    assert_not_includes fields, "dissertation_author"
    assert_equal "Decisão atual", fields["decision_a"]
    assert_equal "", fields["decision_b"]
    assert_not_includes fields, "thesis_a"
    assert_equal "Colega", fields["partner"]
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
