require "fileutils"
require "json"
require "open3"
require "tmpdir"
require "timeout"

class DocumentExport
  DOCUMENT_KINDS = {
    "case_report" => "case",
    "paper_project" => "paper",
    "paper_final" => "paper"
  }.freeze
  NON_DOCUMENT_FIELDS = %w[
    title partner assignment_prompt institution course city year discipline teacher period shift
  ].freeze
  class ExportError < StandardError; end
  class QuartoUnavailable < ExportError; end
  class QuartoBusy < ExportError; end
  class QuartoRenderError < ExportError; end

  class << self
    include TextFormatting

    def build_project_html(project, sources: [], phase: "report")
      data = project_payload(project, sources).merge("export_phase" => phase)
      fields = data.fetch("fields")
      title = fields["title"].presence || data["title"].presence || "Trabalho sem título"
      authors = author_names(fields, account_name: data["account_name"]).join("\n").presence || "Autor não informado"
      sections = document_sections(data, sources).map do |heading, content|
        body = content.map do |label, value|
          heading_html = label.present? ? "<h3>#{escape(label)}</h3>" : ""
          "#{heading_html}#{html_paragraphs(value)}"
        end.join
        body = '<p class="empty">Não preenchido.</p>' if body.blank?
        "<section><h2>#{escape(heading)}</h2>#{body}</section>"
      end.join

      <<~HTML
        <!doctype html>
        <html lang="pt-BR"><head><meta charset="utf-8"><title>#{escape(title)}</title>
        <style>body{font:16px/1.6 Georgia,serif;max-width:850px;margin:3rem auto;padding:0 1.5rem;color:#171717}h1,h2,h3{font-family:system-ui,sans-serif}h1{font-size:2.3rem}h2{margin-top:2.5rem;border-bottom:1px solid #bbb;padding-bottom:.35rem}.meta{color:#555}.empty{color:#666;font-style:italic}</style></head>
        <body><header><h1>#{escape(title)}</h1><p class="meta">#{escape(authors).gsub("\n", "<br>")}</p></header>#{sections}</body></html>
      HTML
    end

    def build_quarto_source(project, sources: [], document_kind: nil)
      data = template_project_data(project, sources)
      document_kind ||= default_document_kind(data["project_type"])
      expected_type = DOCUMENT_KINDS[document_kind]
      raise ExportError, "Tipo de documento inválido." unless expected_type
      raise ExportError, "O tipo de documento não corresponde ao projeto." unless data["projectType"] == expected_type

      front_matter = metadata(data)
      body = case document_kind
      when "case_report"
        raw_typst(case_header(data)) + "\n" + case_report(data)
      when "paper_project"
        raw_typst(project_identification(data)) + "\n" + paper_schedule_block(data["fields"], document_kind) + paper_project(data)
      else
        raw_typst(article_header(data)) + "\n" + paper_schedule_block(data["fields"], document_kind) + paper_final(data)
      end
      "#{front_matter}\n#{body.strip}\n"
    end

    def render_pdf(project, sources: [], phase: "report")
      data = project_payload(project, sources).merge("export_phase" => phase)
      if data["project_type"] == "case" && phase != "report"
        raise ExportError, "O PDF do Case é gerado na fase Relatório; as demais fases podem ser consultadas na prévia."
      end
      document_kind = default_document_kind(data["project_type"])
      source = build_quarto_source(project, sources:, document_kind:)
      QuartoRenderer.render(source)
    end

    private

    def project_payload(project, sources)
      attributes = (project.respond_to?(:attributes) ? project.attributes : project.to_h).stringify_keys
      account_name = project.respond_to?(:account) ? project.account&.name : attributes["account_name"]
      fields = attributes["fields"].is_a?(Hash) ? attributes["fields"].stringify_keys : {}
      if project.respond_to?(:account)
        profile = project.account&.profile || {}
        %w[institution course city].each { |key| fields[key] = profile[key] if fields[key].blank? }
      end
      attributes.merge("fields" => fields, "account_name" => account_name, "sources" => sources)
    end

    def template_project_data(project, sources)
      fields = project["fields"].is_a?(Hash) ? project["fields"] : {}
      project_type = project["project_type"]
      account_name = project.respond_to?(:account) ? project.account&.name : project["account_name"]
      account_profile = project.respond_to?(:account) ? project.account&.profile : {}
      account_profile = account_profile.is_a?(Hash) ? account_profile : {}
      mapped = {
        "title" => fields["title"].to_s,
        "partner" => fields["partner"].to_s,
        "account_name" => account_name.to_s,
        "institution" => (fields["institution"].presence || account_profile["institution"]).to_s,
        "course" => course_label(fields["course"].presence || account_profile["course"]),
        "city" => (fields["city"].presence || account_profile["city"]).to_s,
        "year" => (fields["year"].presence || Date.current.year.to_s).to_s,
        "report_delivery_date" => fields["report_delivery_date"].to_s,
        "debate_delivery_date" => fields["debate_delivery_date"].to_s,
        "dissertation_delivery_date" => fields["dissertation_delivery_date"].to_s,
        "paper_project_delivery_date" => fields["paper_project_delivery_date"].to_s,
        "paper_final_delivery_date" => fields["paper_final_delivery_date"].to_s,
        "dissertation" => fields["dissertation"].to_s,
        "discipline" => fields["discipline"].to_s,
        "teacher" => fields["teacher"].to_s,
        "classInfo" => class_info(fields),
        "period" => fields["period"].to_s,
        "subtitle" => fields["subtitle"].to_s,
        "abstract" => fields["abstract"].to_s,
        "keywords" => fields["keywords"].to_s,
        "paperKind" => project_type == "paper_final" ? "final" : "project"
      }
      field_map = {
        "assignment_prompt" => "assignmentPrompt",
        "facts" => "facts",
        "problem" => "problem",
        "decision_basis" => "decisionBasis",
        "decision_a" => "decisionA",
        "decision_b" => "decisionB",
        "argument_a" => "argumentA",
        "argument_b" => "argumentB",
        "area" => "area",
        "delimitation" => "delimitation",
        "research_context" => "researchContext",
        "research_object" => "researchObject",
        "problem_context" => "problemContext",
        "hypothesis" => "hypothesis",
        "justification" => "justification",
        "objective_general" => "objectiveGeneral",
        "objective1" => "objective1",
        "objective2" => "objective2",
        "objective3" => "objective3",
        "theory" => "theory",
        "method_author" => "methodAuthor",
        "nature" => "nature",
        "approach" => "approach",
        "ends" => "ends",
        "procedure" => "procedure",
        "instruments" => "instruments",
        "introduction" => "introduction",
        "conclusion" => "conclusion",
        "ai_note" => "aiNote"
      }
      field_map.each { |source, target| mapped[target] = fields[source].to_s }
      mapped["decisionA"] = fields["decision_a"].to_s
      mapped["decisionB"] = fields["decision_b"].to_s
      mapped["developmentSections"] = Array(project["development_sections"]).filter_map do |item|
        next unless item.is_a?(Hash)

        { "title" => item["title"].to_s, "content" => item["body"].to_s }
      end
      criteria = Array(project["criteria"]).filter_map do |item|
        next unless item.is_a?(Hash)

        { "term" => item["title"].to_s, "definition" => item["definition"].to_s, "basis" => item["basis"].to_s }
      end
      mapped_type = project_type == "case" ? "case" : "paper"
      {
        "projectType" => mapped_type,
        "project_type" => project_type,
        "account_name" => account_name.to_s,
        "fields" => mapped,
        "criteria" => criteria,
        "sources" => sources
      }
    end

    def default_document_kind(project_type)
      return "case_report" if project_type == "case"
      return "paper_final" if project_type == "paper_final"
      return "paper_project" if project_type == "paper_project"

      raise ExportError, "Tipo de projeto inválido."
    end

    def authors(project)
      author_names(project.fetch("fields", {}), account_name: project["account_name"])
    end

    def author_names(fields, account_name:)
      names = text(account_name).lines.map(&:strip).reject(&:empty?)
      partner = text(fields["partner"]).strip
      names << partner if partner.present?
      names.uniq { |name| name.downcase }
    end

    def metadata(project)
      fields = project.fetch("fields")
      details = [
        ("Disciplina: #{text(fields["discipline"])}" if text(fields["discipline"]).present?),
        ("Professor(a): #{text(fields["teacher"])}" if text(fields["teacher"]).present?),
        ("Turma: #{text(fields["classInfo"])}" if text(fields["classInfo"]).present?),
        ("Data de entrega: #{formatted_date(fields["report_delivery_date"])}" if formatted_date(fields["report_delivery_date"]).present?)
      ].compact
      title = text(fields["title"]).strip
      [
        "---",
        "title: #{yaml_typst_scalar(title)}",
        "lang: pt-BR",
        "abnt-capa: true",
        "abnt-folha-rosto: false",
        "abnt-instituicao: #{yaml_typst_scalar(fields["institution"])}",
        "abnt-curso: #{yaml_typst_scalar(fields["course"])}",
        "abnt-subtitulo: #{yaml_typst_scalar(fields["subtitle"])}",
        yaml_list("abnt-autores", authors(project)),
        yaml_list("abnt-dados", details),
        "abnt-local: #{yaml_typst_scalar(fields["city"])}",
        "abnt-ano: #{yaml_typst_scalar(fields["year"].presence || Date.current.year.to_s)}",
        'abnt-numeracao: "1"',
        'abnt-numeracao-secoes: "1.1"',
        "abnt-sem-quebra-secoes: true",
        'abnt-fonte: "Liberation Sans"',
        "format: abnt-typst",
        "---"
      ].join("\n")
    end

    def author_notes(project)
      fields = project.fetch("fields")
      course = text(fields["course"]).presence
      period = text(fields["period"]).presence
      affiliations = [
        ("do #{period}º período" if period.present?),
        ("do #{course}" if course.present?)
      ].compact
      institution = text(fields["institution"]).strip
      affiliation = affiliations.join(" ")
      note = if affiliation.present?
        "Discente #{affiliation}#{institution.present? ? " - #{institution}" : ""}."
      elsif institution.present?
        "Discente da #{institution}."
      else
        "Discente."
      end
      notes = authors(project).map { |author| [ author, note ] }
      teacher = text(fields["teacher"]).strip
      notes << [ teacher, "Docente da #{institution}." ] if teacher.present? && institution.present?
      notes
    end

    def course_label(value)
      course = text(value).strip
      return "" if course.blank?
      return course if course.match?(/\Acurso\b/i)

      "Curso de #{course}"
    end

    def class_info(fields)
      period = text(fields["period"]).strip
      shift = text(fields["shift"]).strip
      parts = []
      parts << shift.capitalize if shift.present?
      period_label = period.match?(/\A\d+\z/) ? "#{period}º período" : period
      parts << period_label if period_label.present?
      parts.join(", ")
    end

    def formatted_date(value)
      return "" if value.blank?

      Date.iso8601(value).strftime("%d/%m/%Y")
    rescue Date::Error
      ""
    end

    def typst_author_pairs(project)
      pairs = author_notes(project).map do |name, note|
        "(#{typst_literal(name)}, [#text(#{typst_literal(note)})])"
      end
      "(" + pairs.join(",\n  ") + (pairs.length == 1 ? "," : "") + ")"
    end

    def case_header(project)
      fields = project.fetch("fields")
      title = text(fields["title"]).strip.upcase
      discipline = text(fields["discipline"]).strip
      institution = text(fields["institution"]).strip
      note = if discipline.present? && institution.present?
        "Case apresentado à disciplina de #{discipline} da #{institution}."
      elsif institution.present?
        "Case acadêmico apresentado à #{institution}."
      else
        "Case acadêmico."
      end
      [
        '#import "_extensions/abnt/tipos/caso.typ": *',
        "#caso-cabecalho(",
        "  titulo: #{typst_literal(title)},",
        "  nota-titulo: [#text(#{typst_literal(note)})],",
        "  autores: #{typst_author_pairs(project)},",
        ")"
      ].join("\n")
    end

    def article_header(project)
      fields = project.fetch("fields")
      subtitle = text(fields["subtitle"]).strip
      parts = [
        '#import "_extensions/abnt/tipos/artigo.typ": *',
        "#artigo-cabecalho(",
        "  titulo: #{typst_literal(text(fields["title"]).strip.upcase)},",
        "  subtitulo: #{subtitle.present? ? "[#text(#{typst_literal(subtitle)})]" : "none"},",
        "  autores: #{typst_author_pairs(project)},",
        ")"
      ]
      abstract = text(fields["abstract"]).strip
      keywords = text(fields["keywords"]).strip
      if abstract.present? || keywords.present?
        parts.concat([
          "#artigo-resumo(",
          "  palavras: [#text(#{typst_literal(keywords)})],",
          ")[",
          abstract.present? ? "  #text(#{typst_literal(abstract)})" : "  []",
          "]"
        ])
      end
      parts.join("\n")
    end

    def project_identification(project)
      fields = project.fetch("fields")
      [
        '#import "_extensions/abnt/tipos/projeto.typ": *',
        "#pagina-identificacao-projeto(",
        "  curso: #{typst_literal(fields["course"])},",
        "  titulo: #{typst_literal(text(fields["title"]).strip.upcase)},",
        "  periodo: #{typst_literal(fields["classInfo"])},",
        "  disciplina: #{typst_literal(fields["discipline"])},",
        "  professor: #{typst_literal(fields["teacher"])},",
        "  aluno: #{typst_literal(authors(project).join(" e "))},",
        ")"
      ].join("\n")
    end

    def bibliography(project)
      references = Array(project["sources"]).filter_map do |source|
        text(source["reference"]).strip if source.is_a?(Hash)
      end.reject(&:empty?).uniq.sort_by(&:downcase)
      return "" if references.empty?

      entries = references.map do |reference|
        "  ref-texto(#{typst_literal(reference)}, [#text(#{typst_literal(reference)})]),"
      end
      "#abnt-bibliografia((\n#{entries.join("\n")}\n), ordenar: true)"
    end

    def section(title, value, level = 1)
      content = paragraphs(value)
      return "" if content.empty?

      "#{("#" * level)} #{markdown_text(title)}\n\n#{content}"
    end

    def case_possible_solutions(fields)
      blocks = [ paragraphs(fields["decisionBasis"]) ]
      [ [ "a", "decisionA", ";" ], [ "b", "decisionB", "." ] ].each do |marker, key, ending|
        content = text(fields[key]).strip
        next if content.empty?

        content = content.sub(/[.;?!]\s*\z/, "").rstrip + ending
        rendered = paragraphs(content)
        blocks << "#{marker}) \u2003#{rendered.gsub("\n", "\n   ")}" if rendered.present?
      end
      blocks.reject(&:empty?).join("\n\n")
    end

    def case_decisions_section(fields)
      solutions = case_possible_solutions(fields)
      return "" if solutions.empty?

      "## Descrição das decisões possíveis\n\n#{solutions}"
    end

    def case_argumentation(fields)
      titled = [ [ "decisionA", "argumentA", "Alternativa a)" ], [ "decisionB", "argumentB", "Alternativa b)" ] ].map do |title_key, key, fallback|
        title = AcademicWorkflow.alternative_title(fields[title_key]).presence || fallback
        section(title, fields[key], 3)
      end.reject(&:empty?)
      return "" if titled.empty?

      "## Descrição dos argumentos\n\n#{titled.join("\n\n")}"
    end

    def schedule_block(pairs)
      pairs.filter_map do |label, value|
        date = formatted_date(value)
        "#{label}: #{date}" if date.present?
      end.map { |line| markdown_text(line) }.join("\n\n")
    end

    def case_schedule(fields)
      schedule_block([
        [ "Data de entrega do relatório", fields["report_delivery_date"] ],
        [ "Data do debate", fields["debate_delivery_date"] ],
        [ "Data de entrega da dissertação", fields["dissertation_delivery_date"] ]
      ])
    end

    def paper_schedule_block(fields, document_kind)
      pair = if document_kind == "paper_project"
        [ "Data de entrega do projeto de paper (1º BI)", fields["paper_project_delivery_date"] ]
      else
        [ "Data de entrega do paper final (2º BI)", fields["paper_final_delivery_date"] ]
      end
      block = schedule_block([ pair ])
      block.empty? ? "" : block + "\n\n"
    end

    def case_report(project)
      fields = project.fetch("fields")
      criteria = Array(project["criteria"]).filter_map do |item|
        next unless item.is_a?(Hash)

        term = text(item["term"]).strip
        definition = text(item["definition"]).strip
        basis = text(item["basis"]).strip
        next unless [ term, definition, basis ].any?(&:present?)

        sentence = term.present? ? "#{term}: #{definition}" : definition
        sentence += " Base normativa ou ética: #{basis}" if basis.present?
        sentence.strip
      end
      parts = [
        case_schedule(fields),
        section("DESCRIÇÃO DO CASO", [ text(fields["facts"]), text(fields["problem"]) ].reject(&:empty?).join("\n\n")),
        "# IDENTIFICAÇÃO E ANÁLISE DO CASO",
        case_decisions_section(fields),
        case_argumentation(fields),
        section("Descrição dos critérios e valores", criteria.join("\n\n"), 2)
      ]
      body = parts.reject(&:empty?).join("\n\n")
      references = bibliography(project)
      body + (references.present? ? "\n\n#{raw_typst(references)}" : "")
    end

    def paper_project(project)
      fields = project.fetch("fields")
      objectives = [ section("Objetivo Geral", fields["objectiveGeneral"], 2) ]
      specific = (1..3).filter_map { |number| text(fields["objective#{number}"]).strip.presence }
      if specific.any?
        objectives << "## Objetivos específicos\n\n" + specific.each_with_index.map { |value, index| "#{index + 1}. #{markdown_text(value)}" }.join("\n\n")
      end
      methodology = [
        ("Autor de metodologia adotado: #{text(fields["methodAuthor"])}." if text(fields["methodAuthor"]).strip.present?),
        ("Natureza: #{text(fields["nature"])}." if text(fields["nature"]).strip.present?),
        ("Abordagem: #{text(fields["approach"])}." if text(fields["approach"]).strip.present?),
        ("Fins: #{text(fields["ends"])}." if text(fields["ends"]).strip.present?),
        ("Procedimentos: #{text(fields["procedure"])}." if text(fields["procedure"]).strip.present?),
        text(fields["instruments"])
      ].compact.reject(&:empty?).join("\n\n")
      parts = [
        section("TEMA", fields["area"]),
        section("TÍTULO E DELIMITAÇÃO", [ fields["delimitation"], fields["researchContext"], fields["researchObject"] ].map { |value| text(value) }.reject(&:empty?).join("\n\n")),
        section("PROBLEMA", [ fields["problemContext"], fields["problem"] ].map { |value| text(value) }.reject(&:empty?).join("\n\n")),
        section("HIPÓTESE", fields["hypothesis"]),
        section("JUSTIFICATIVA", fields["justification"]),
        "# OBJETIVOS\n\n#{objectives.reject(&:empty?).join("\n\n")}",
        section("REFERENCIAL TEÓRICO", fields["theory"]),
        section("METODOLOGIA", methodology)
      ]
      body = parts.reject(&:empty?).join("\n\n")
      references = bibliography(project)
      body + (references.present? ? "\n\n#{raw_typst(references)}" : "")
    end

    def paper_final(project)
      fields = project.fetch("fields")
      parts = [ section("INTRODUÇÃO", fields["introduction"]) ]
      Array(fields["developmentSections"]).each_with_index do |item, index|
        next unless item.is_a?(Hash)

        title = text(item["title"]).strip.presence || "DESENVOLVIMENTO #{index + 1}"
        parts << section(title, item["content"])
      end
      parts << section("DECLARAÇÃO SOBRE USO DE IA", fields["aiNote"]) if text(fields["aiNote"]).strip.present?
      parts << section("CONCLUSÃO", fields["conclusion"])
      body = parts.reject(&:empty?).join("\n\n")
      references = bibliography(project)
      body + (references.present? ? "\n\n#{raw_typst(references)}" : "")
    end

    def document_sections(project, sources)
      fields = project["fields"]
      stages = if project["project_type"] == "case"
        AcademicWorkflow.sections("case").select { |stage| stage["phase"] == project["export_phase"] }
      else
        AcademicWorkflow.sections(project["project_type"])
      end
      stages.filter_map do |stage|
        custom = stage["custom"]
        next if custom == "review"

        content = stage.fetch("fields", []).filter_map do |field|
          next if NON_DOCUMENT_FIELDS.include?(field["id"])

          [ AcademicWorkflow.field_label(fields, field), fields[field["id"]] ]
        end
        case custom
        when "criteria"
          content = Array(project["criteria"]).map { |item| [ item["title"].presence || "Critério", [ item["definition"], ("Base: #{item["basis"]}" if item["basis"].present?) ].compact.join("\n\n") ] }
        when "dissertation"
          content = [ [ "Dissertação", fields["dissertation"] ] ]
        when "development"
          content = Array(project["development_sections"]).map { |item| [ item["title"].presence || "Tópico", item["body"] ] }
        when "sources"
          content = Array(sources).sort_by { |item| (item["author"].presence || item["title"]).to_s.downcase }.map do |source|
            [ nil, source["reference"].presence || [ source["author"], source["title"] ].compact_blank.join(" — ") ]
          end
        end
        [ stage["title"], content ]
      end
    end
  end
end
