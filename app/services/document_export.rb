require "fileutils"
require "json"
require "open3"
require "tmpdir"
require "timeout"

class DocumentExport
  INSTITUTION = "Faculdade Supremo Redentor - FACSUR"
  EXTENSION_DIR = Rails.root.join("vendor/quarto/_extensions/abnt")
  RENDER_TIMEOUT_SECONDS = 90
  MAX_PDF_BYTES = 25 * 1024 * 1024
  DOCUMENT_KINDS = {
    "case_report" => "case",
    "paper_project" => "paper",
    "paper_final" => "paper"
  }.freeze
  MARKDOWN_ESCAPABLE = "\\`*_{}[]<>()#+.!|~&+-".freeze
  NON_DOCUMENT_FIELDS = %w[
    title authors author dissertation_author partner assignment_prompt profile
    institution course city year discipline teacher period shift
    report_delivery_date debate_delivery_date dissertation_delivery_date
  ].freeze
  RENDER_MUTEX = Mutex.new
  @render_count = 0

  class ExportError < StandardError; end
  class QuartoUnavailable < ExportError; end
  class QuartoBusy < ExportError; end
  class QuartoRenderError < ExportError; end

  class << self
    def build_project_html(project, sources: [], phase: "report")
      data = project_payload(project, sources).merge("export_phase" => phase)
      fields = data.fetch("fields")
      title = fields["title"].presence || data["title"].presence || "Trabalho sem título"
      authors = author_names(fields, account_name: data["account_name"], phase:).join("\n").presence || "Autor não informado"
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
      data = legacy_project(project, sources)
      document_kind ||= default_document_kind(data["project_type"])
      expected_type = DOCUMENT_KINDS[document_kind]
      raise ExportError, "Tipo de documento inválido." unless expected_type
      raise ExportError, "O tipo de documento não corresponde ao projeto." unless data["projectType"] == expected_type

      front_matter = metadata(data)
      body = case document_kind
      when "case_report"
        raw_typst(case_header(data)) + "\n" + case_report(data)
      when "paper_project"
        raw_typst(project_identification(data)) + "\n" + paper_project(data)
      else
        raw_typst(article_header(data)) + "\n" + paper_final(data)
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
      executable = quarto_executable
      raise QuartoUnavailable, "O renderizador Quarto não está disponível." unless executable && EXTENSION_DIR.directory?
      raise QuartoBusy, "Há muitas renderizações em andamento." unless acquire_render_slot

      begin
        render_isolated(source, executable)
      ensure
        release_render_slot
      end
    end

    private

    def project_payload(project, sources)
      attributes = (project.respond_to?(:attributes) ? project.attributes : project.to_h).stringify_keys
      account_name = project.respond_to?(:account) ? project.account&.name : attributes["account_name"]
      fields = attributes["fields"].is_a?(Hash) ? attributes["fields"].stringify_keys : {}
      if project.respond_to?(:account)
        profile = project.account&.profile || {}
        %w[course city].each { |key| fields[key] = profile[key] if fields[key].blank? }
      end
      attributes.merge("fields" => fields, "account_name" => account_name, "sources" => sources)
    end

    def legacy_project(project, sources)
      fields = project["fields"].is_a?(Hash) ? project["fields"] : {}
      project_type = project["project_type"]
      account_name = project.respond_to?(:account) ? project.account&.name : project["account_name"]
      account_profile = project.respond_to?(:account) ? project.account&.profile : {}
      account_profile = account_profile.is_a?(Hash) ? account_profile : {}
      authors = fields["authors"].presence || fields["author"].presence || account_name
      mapped = {
        "title" => fields["title"].to_s,
        "author" => authors,
        "partner" => fields["partner"].to_s,
        "account_name" => account_name.to_s,
        "institution" => "",
        "course" => course_label(fields["course"].presence || account_profile["course"]),
        "city" => (fields["city"].presence || account_profile["city"]).to_s,
        "year" => (fields["year"].presence || Date.current.year.to_s).to_s,
        "report_delivery_date" => fields["report_delivery_date"].to_s,
        "dissertation" => fields["dissertation"].to_s,
        "profile" => fields["profile"].to_s,
        "discipline" => fields["discipline"].to_s,
        "teacher" => fields["teacher"].to_s,
        "classInfo" => class_info(fields),
        "period" => fields["period"].to_s,
        "subtitle" => (fields["subtitle"].presence || fields["sub_title"]).to_s,
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
      mapped["decisionA"] = fields["decision_a"].presence || fields["thesis_a"].to_s
      mapped["decisionB"] = fields["decision_b"].presence || fields["thesis_b"].to_s
      mapped["developmentSections"] = Array(project["development_sections"]).filter_map do |item|
        next unless item.is_a?(Hash)

        { "title" => item["title"].to_s, "content" => item["body"].to_s }
      end
      criteria = Array(project["criteria"]).filter_map do |item|
        next unless item.is_a?(Hash)

        { "term" => (item["title"].presence || item["term"]).to_s, "definition" => item["definition"].to_s, "basis" => item["basis"].to_s }
      end
      mapped_type = project_type == "case" ? "case" : "paper"
      { "projectType" => mapped_type, "project_type" => project_type, "fields" => mapped, "criteria" => criteria, "sources" => sources }
    end

    def default_document_kind(project_type)
      return "case_report" if project_type == "case"
      return "paper_final" if project_type == "paper_final"
      return "paper_project" if project_type == "paper_project"

      raise ExportError, "Tipo de projeto inválido."
    end

    def text(value)
      return "" unless value.is_a?(String)

      value.delete("\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F").gsub("\r\n", "\n").tr("\r", "\n")
    end

    def typst_literal(value)
      JSON.generate(text(value))
    end

    def yaml_typst_scalar(value)
      JSON.generate(typst_literal(value)[1...-1])
    end

    def markdown_text(value)
      text(value).each_char.map { |character| MARKDOWN_ESCAPABLE.include?(character) ? "\\#{character}" : character }.join
    end

    def paragraphs(value)
      text(value).strip.split(/\n[ \t]*\n+/).filter_map do |paragraph|
        next if paragraph.strip.empty?

        paragraph.split("\n").map { |line| markdown_text(line) }.join("  \n")
      end.join("\n\n")
    end

    def html_paragraphs(value)
      parts = text(value).strip.split(/\n[ \t]*\n+/).filter_map(&:presence)
      return '<p class="empty">Não preenchido.</p>' if parts.empty?

      parts.map { |part| "<p>#{escape(part.strip).gsub("\n", "<br>")}</p>" }.join
    end

    def escape(value)
      ERB::Util.html_escape(value.to_s).to_s
    end

    def yaml_list(name, values)
      return "#{name}: []" if values.empty?

      "#{name}:\n" + values.map { |value| "  - #{yaml_typst_scalar(value)}" }.join("\n")
    end

    def raw_typst(code)
      "```{=typst}\n#{code.strip}\n```\n"
    end

    def authors(project)
      author_names(project.fetch("fields", {}), account_name: project["account_name"])
    end

    def author_names(fields, account_name:, phase: nil)
      primary = fields["dissertation_author"].presence if phase == "dissertation"
      primary ||= fields["authors"].presence || fields["author"].presence || account_name
      names = primary.to_s.lines.map(&:strip).reject(&:empty?)
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
        "abnt-instituicao: #{yaml_typst_scalar(INSTITUTION)}",
        "abnt-curso: #{yaml_typst_scalar(fields["course"])}",
        "abnt-subtitulo: #{yaml_typst_scalar(fields["subtitle"] || fields["subTitle"])}",
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
      note = affiliations.any? ? "Discente #{affiliations.join(" ")} - FACSUR." : "Discente da #{INSTITUTION}."
      notes = authors(project).map { |author| [ author, note ] }
      teacher = text(fields["teacher"]).strip
      notes << [ teacher, "Docente da #{INSTITUTION}." ] if teacher.present?
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
      note = discipline.present? ?
        "Case apresentado à disciplina de #{discipline} da #{INSTITUTION}." :
        "Case acadêmico apresentado à #{INSTITUTION}."
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
      subtitle = text(fields["subtitle"] || fields["subTitle"]).strip
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
        section("DESCRIÇÃO DO CASO", [ text(fields["facts"]), text(fields["problem"]) ].reject(&:empty?).join("\n\n")),
        "# IDENTIFICAÇÃO E ANÁLISE DO CASO",
        case_possible_solutions(fields),
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
        next if %w[review reuse_decisions].include?(custom)

        content = stage.fetch("fields", []).filter_map do |field|
          next if NON_DOCUMENT_FIELDS.include?(field["id"])

          [ field["label"], fields[field["id"]] ]
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

    def quarto_executable
      binary = ENV.fetch("QUARTO_BINARY", "quarto")
      return binary if binary.include?(File::SEPARATOR) && File.executable?(binary)

      ENV.fetch("PATH", "/usr/local/bin:/usr/bin:/bin").split(File::PATH_SEPARATOR).each do |directory|
        candidate = File.join(directory, binary)
        return candidate if File.executable?(candidate)
      end
      nil
    end

    def acquire_render_slot
      RENDER_MUTEX.synchronize do
        return false if @render_count >= 2

        @render_count += 1
      end
      true
    end

    def release_render_slot
      RENDER_MUTEX.synchronize { @render_count -= 1 }
    end

    def render_isolated(source, executable)
      Dir.mktmpdir("assistente-quarto-") do |workspace|
        extensions = File.join(workspace, "_extensions")
        FileUtils.mkdir_p(extensions)
        FileUtils.cp_r(EXTENSION_DIR, File.join(extensions, "abnt"))
        source_path = File.join(workspace, "document.qmd")
        output_path = File.join(workspace, "document.pdf")
        File.write(source_path, source, mode: "w:UTF-8")
        home = File.join(workspace, "home")
        FileUtils.mkdir_p(home, mode: 0o700)
        environment = {
          "PATH" => ENV.fetch("PATH", "/usr/local/bin:/usr/bin:/bin"),
          "HOME" => home,
          "TMPDIR" => workspace,
          "TMP" => workspace,
          "TEMP" => workspace,
          "LANG" => ENV.fetch("LANG", "C.UTF-8"),
          "LC_ALL" => ENV.fetch("LC_ALL", "C.UTF-8")
        }
        pid = Process.spawn(
          environment,
          executable,
          "render",
          File.basename(source_path),
          "--output",
          File.basename(output_path),
          chdir: workspace,
          in: File::NULL,
          out: File::NULL,
          err: File::NULL,
          pgroup: true,
          unsetenv_others: true
        )
        status = wait_for_renderer(pid)
        unless status.success? && File.file?(output_path)
          raise QuartoRenderError, "O Quarto não conseguiu renderizar este documento."
        end
        raise QuartoRenderError, "O PDF gerado excedeu o limite de tamanho." if File.size(output_path) > MAX_PDF_BYTES

        pdf = File.binread(output_path)
        raise QuartoRenderError, "O renderizador não retornou um PDF válido." unless pdf.start_with?("%PDF-")

        pdf
      rescue Errno::ENOENT
        raise QuartoUnavailable, "Não foi possível iniciar o Quarto."
      end
    end

    def wait_for_renderer(pid)
      Timeout.timeout(RENDER_TIMEOUT_SECONDS) do
        Process.waitpid(pid)
        $CHILD_STATUS || $?
      end
    rescue Timeout::Error
      terminate_renderer(pid)
      raise QuartoRenderError, "A renderização excedeu o tempo limite."
    end

    def terminate_renderer(pid)
      Process.kill("TERM", -pid)
      sleep 0.25
      Process.kill("KILL", -pid)
    rescue Errno::ESRCH
      nil
    ensure
      begin
        Process.waitpid(pid)
      rescue Errno::ECHILD
        nil
      end
    end
  end
end
