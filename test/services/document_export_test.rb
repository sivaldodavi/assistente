require "test_helper"

class DocumentExportTest < ActiveSupport::TestCase
  test "HTML preview escapes answer content and keeps the Case route sections" do
    project = Project.create!(
      project_type: "case",
      fields: { "title" => "<script>não</script>", "facts" => "Fato do caso" }
    )
    html = DocumentExport.build_project_html(project)

    assert_includes html, "&lt;script&gt;não&lt;/script&gt;"
    assert_not_includes html, "<script>não</script>"
    assert_includes html, "Descrição do caso"
    assert_includes html, "Fato do caso"
  end

  test "uses the account name and optional duo partner as document authors" do
    account = Account.create!(email: "authors@example.test", name: "Ana Estudante")
    project = account.projects.create!(
      project_type: "case",
      fields: { "title" => "Relatório", "partner" => "Bruno Colega" }
    )

    html = DocumentExport.build_project_html(project)
    source = DocumentExport.build_quarto_source(project)

    assert_includes html, "Ana Estudante"
    assert_includes html, "Bruno Colega"
    assert_includes source, '  - "Ana Estudante"'
    assert_includes source, '  - "Bruno Colega"'
    assert_not_includes html, "Colega de dupla"
  end

  test "Paper preview uses the original Paper stages and not Case sections" do
    project = Project.create!(
      project_type: "paper_final",
      fields: { "title" => "Paper", "abstract" => "Resumo do paper" }
    )
    html = DocumentExport.build_project_html(project)

    assert_includes html, "Identificação, resumo e palavras-chave"
    assert_includes html, "Resumo do paper"
    assert_not_includes html, "Descrição do caso"
  end

  test "QMD generation uses the original ABNT Typst templates for each route" do
    expected_templates = {
      "case" => "_extensions/abnt/tipos/caso.typ",
      "paper_project" => "_extensions/abnt/tipos/projeto.typ",
      "paper_final" => "_extensions/abnt/tipos/artigo.typ"
    }

    expected_templates.each do |project_type, template|
      project = Project.create!(project_type:)
      source = DocumentExport.build_quarto_source(project)

      assert_includes source, "format: abnt-typst"
      assert_includes source, %(#import "#{template}": *)
    end
  end

  test "QMD generation escapes user text rather than treating it as Markdown or Typst" do
    project = Project.create!(project_type: "case", fields: { "facts" => "#import \"evil.typ\": *" })
    source = DocumentExport.build_quarto_source(project)

    assert_includes source, "\\#import"
    assert_not_includes source, "```{=typst}\n#import \"evil.typ\""
  end

  test "PDF is restricted to the Case report phase" do
    project = Project.create!(project_type: "case")

    error = assert_raises(DocumentExport::ExportError) do
      DocumentExport.render_pdf(project, phase: "dissertation")
    end
    assert_includes error.message, "fase Relatório"
  end
end
