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

  test "cover follows the Typst reference institution and account academic data" do
    account = Account.create!(
      email: "cover@example.test",
      name: "Autora",
      profile: { "institution" => "Instituição Exemplo", "course" => "Direito", "city" => "Recife", "period" => "3", "shift" => "noturno" }
    )
    project = account.projects.create!(
      project_type: "case",
      fields: {
        "title" => "Relatório",
        "discipline" => "Direito Civil",
        "teacher" => "Professora Exemplo",
        "period" => "3",
        "shift" => "noturno",
        "report_delivery_date" => "2026-11-30"
      }
    )

    source = DocumentExport.build_quarto_source(project)

    assert_includes source, 'abnt-instituicao: "Instituição Exemplo"'
    assert_includes source, 'abnt-curso: "Curso de Direito"'
    assert_includes source, 'abnt-local: "Recife"'
    assert_includes source, %(abnt-ano: "#{Date.current.year}")
    assert_includes source, "Disciplina: Direito Civil"
    assert_includes source, "Professor(a): Professora Exemplo"
    assert_includes source, "Turma: Noturno, 3º período"
    assert_not_includes source, "30/11/2026"
    assert_includes source, "da Instituição Exemplo"
    assert_includes source, "Discente do 3º período do Curso de Direito - Instituição Exemplo."
  end

  test "dissertation preview uses one text field" do
    project = Project.new(
      project_type: "case",
      fields: { "dissertation" => "Texto único da dissertação." }
    )

    html = DocumentExport.build_project_html(project, phase: "dissertation")

    assert_includes html, "Dissertação"
    assert_includes html, "Texto único da dissertação."
    assert_not_includes html, "Introdução"
    assert_not_includes html, "Conclusão"
  end

  test "exports current decisions and ignores removed field aliases" do
    alternative_a = "A alternativa A tem conteúdo próprio."
    alternative_b = "A alternativa B tem conteúdo próprio."
    project = Project.new(
      project_type: "case",
      fields: {
        "title" => "Relatório",
        "decision_a" => alternative_a,
        "decision_b" => alternative_b,
        "thesis_a" => "Texto antigo duplicado A",
        "thesis_b" => "Texto antigo duplicado B",
        "author" => "Autoria antiga",
        "authors" => "Autoria antiga plural",
        "dissertation_author" => "Autoria antiga da dissertação",
        "sub_title" => "Subtítulo antigo"
      }
    )

    html = DocumentExport.build_project_html(project)
    source = DocumentExport.build_quarto_source(project)

    [ html, source ].each do |document|
      assert_equal (document == source ? 1 : 2), document.scan(alternative_a.delete_suffix(".")).length
      assert_equal (document == source ? 1 : 2), document.scan(alternative_b.delete_suffix(".")).length
      assert_not_includes document, "Texto antigo duplicado"
      assert_not_includes document, "Autoria antiga"
      assert_not_includes document, "Subtítulo antigo"
    end
    assert_not_includes source, "Descrição dos argumentos"
  end

  test "exports the argumentation of each alternative in the Case report" do
    project = Project.new(
      project_type: "case",
      fields: {
        "title" => "Relatório",
        "decision_a" => "Alternativa a de teste.",
        "decision_b" => "Alternativa b de teste.",
        "argument_a" => "Argumento exclusivo de a.",
        "argument_b" => "Argumento exclusivo de b."
      }
    )

    source = DocumentExport.build_quarto_source(project)
    html = DocumentExport.build_project_html(project)

    assert_includes source, "## Descrição das decisões possíveis"
    assert_includes source, "## Descrição dos argumentos"
    assert_includes source, "### Alternativa a de teste\n\nArgumento exclusivo de a"
    assert_includes source, "### Alternativa b de teste\n\nArgumento exclusivo de b"
    assert_includes html, "<h3>Alternativa a de teste</h3>"
    assert_includes html, "Argumento exclusivo de a."
    assert_equal 1, html.scan("Alternativa a de teste.").length
  end

  test "keeps internal Case delivery dates out of the exported report" do
    project = Project.new(
      project_type: "case",
      fields: {
        "title" => "Relatório",
        "facts" => "Fatos do caso.",
        "decision_a" => "Alternativa a de teste.",
        "report_delivery_date" => "2026-09-23",
        "debate_delivery_date" => "2026-10-14",
        "dissertation_delivery_date" => "2026-11-30"
      }
    )

    source = DocumentExport.build_quarto_source(project)
    html = DocumentExport.build_project_html(project)

    [ source, html ].each do |document|
      assert_not_includes document, "Data de entrega do relatório"
      assert_not_includes document, "Data do debate"
      assert_not_includes document, "Data de entrega da dissertação"
      assert_not_includes document, "23/09/2026"
      assert_not_includes document, "14/10/2026"
      assert_not_includes document, "30/11/2026"
    end
  end

  test "does not export removed decision aliases" do
    legacy_text = "Alternativa antiga preservada."
    project = Project.new(project_type: "case", fields: { "thesis_a" => legacy_text })

    source = DocumentExport.build_quarto_source(project)

    assert_not_includes source, legacy_text
  end

  test "PDF is restricted to the Case report phase" do
    project = Project.create!(project_type: "case")

    error = assert_raises(DocumentExport::ExportError) do
      DocumentExport.render_pdf(project, phase: "dissertation")
    end
    assert_includes error.message, "fase Relatório"
  end

  test "keeps internal Paper delivery dates out of both document exports" do
    {
      "paper_project" => [ "paper_project_delivery_date", "Data de entrega do projeto de paper", "2026-10-15", "15/10/2026" ],
      "paper_final" => [ "paper_final_delivery_date", "Data de entrega do paper final", "2026-11-20", "20/11/2026" ]
    }.each do |project_type, (date_field, label, iso_date, formatted_date)|
      project = Project.new(project_type:, fields: { "title" => "Paper de teste", date_field => iso_date })
      source = DocumentExport.build_quarto_source(project)
      html = DocumentExport.build_project_html(project)

      [ source, html ].each do |document|
        assert_not_includes document, label
        assert_not_includes document, iso_date
        assert_not_includes document, formatted_date
      end
    end
  end
end
