class AcademicSchedule
  SCHEDULE_KEYS = %w[report_date debate_date dissertation_date final_date].freeze
  TEMPLATES = {
    "case" => [
      [ "case-theme", "Escolher e delimitar o tema" ],
      [ "case-narrative", "Construir a narrativa: personagens, contexto e conflito" ],
      [ "case-question", "Formular a questão jurídica central" ],
      [ "case-decisions", "Cadastrar as decisões possíveis" ],
      [ "case-research", "Pesquisar legislação, jurisprudência e doutrina" ],
      [ "case-arguments", "Montar argumentos para cada decisão" ],
      [ "case-criteria", "Registrar critérios e valores da decisão" ],
      [ "case-debate", "Preparar e participar do debate" ],
      [ "case-debate-notes", "Registrar objeções e aprendizados do debate" ],
      [ "case-dissertation", "Redigir a dissertação argumentativa" ],
      [ "case-review", "Conferir referências e checklist" ],
      [ "case-delivery", "Preparar a entrega" ]
    ].freeze,
    "paper" => [
      [ "paper-theme", "Delimitar o tema e o problema" ],
      [ "paper-hypothesis", "Definir hipóteses e objetivos" ],
      [ "paper-method", "Definir a metodologia" ],
      [ "paper-research", "Pesquisar e organizar as fontes" ],
      [ "paper-project", "Escrever o Projeto de Paper" ],
      [ "paper-project-review", "Revisar o Projeto de Paper" ],
      [ "paper-development", "Estruturar o desenvolvimento em tópicos" ],
      [ "paper-writing", "Escrever o Paper Final" ],
      [ "paper-conclusion", "Retomar problema, hipótese e conclusão" ],
      [ "paper-review", "Conferir referências e extensão" ],
      [ "paper-delivery", "Preparar a entrega" ]
    ].freeze
  }.freeze

  class << self
    def normalize_schedule(raw, project_type:, fallback_date: "")
      source = hash_value(raw)
      tasks = rows(source["tasks"]).first(100).filter_map do |item|
        values = hash_value(item)
        raw_date = values["date"]
        due_date = normalize_date(raw_date)
        next if raw_date.present? && due_date.blank?

        title = bounded(values["title"], 180)
        next if title.blank? && due_date.blank? && values["id"].blank?

        stage = integer_or_nil(values["stage"])
        {
          "id" => bounded(values["id"].presence || SecureRandom.uuid, 80),
          "title" => title,
          "date" => due_date,
          "done" => truthy?(values["done"]),
          "stage" => stage,
          "template_key" => bounded(values["template_key"].presence || values["templateKey"], 80).presence || template_key(project_type, title)
        }
      end

      {
        "report_date" => normalize_date(source["report_date"].presence || source["deliveryDate"].presence || source["paper_project_date"]).presence || normalize_date(fallback_date),
        "debate_date" => normalize_date(source["debate_date"].presence || source["debateDate"]),
        "dissertation_date" => normalize_date(source["dissertation_date"].presence || source["dissertationDate"]),
        "final_date" => normalize_date(source["final_date"].presence || source["finalDate"].presence || source["paperFinalDate"]),
        "tasks" => tasks
      }
    end

    def templates(project_type)
      paper_type?(project_type) ? TEMPLATES.fetch("paper") : TEMPLATES.fetch("case")
    end

    def deadlines(schedule, project_type, project_id: "", title: "")
      normalized = normalize_schedule(schedule, project_type:)
      keys = if project_type.to_s == "case"
        [ [ "report_date", "Entrega do relatório" ], [ "debate_date", "Debate" ], [ "dissertation_date", "Dissertação" ] ]
      else
        [ [ "report_date", "Projeto de Paper" ], [ "final_date", "Paper Final" ] ]
      end
      display_title = title.presence || (project_type.to_s == "case" ? "Relatório sem título" : "Paper sem título")
      keys.filter_map do |key, label|
        due = normalized[key]
        next if due.blank?

        entry(project_id, display_title, key, label, due)
      end
    end

    def entries(schedule, project_type, project_id: "", title: "")
      normalized = normalize_schedule(schedule, project_type:)
      display_title = title.presence || (project_type.to_s == "case" ? "Relatório sem título" : "Paper sem título")
      deadlines(normalized, project_type, project_id:, title: display_title) + normalized["tasks"].filter_map do |task|
        next if task["date"].blank?

        entry(project_id, display_title, "task", task["title"].presence || "Tarefa sem título", task["date"]).merge(
          "task_id" => task["id"],
          "done" => task["done"]
        )
      end
    end

    def summary(schedule, project_type)
      normalized = normalize_schedule(schedule, project_type:)
      upcoming = entries(normalized, project_type).reject { |item| item["done"] }.sort_by { |item| item["date"] }
      {
        "task_total" => normalized["tasks"].length,
        "task_done" => normalized["tasks"].count { |task| task["done"] },
        "deadline" => upcoming.first,
        "has_dates" => upcoming.any?
      }
    end

    def upcoming(projects, today: Date.current)
      entries = Array(projects).flat_map do |project|
        project_entries = project.respond_to?(:schedule) ? self.entries(project.schedule, project.project_type, project_id: project.id.to_s, title: project.title) : Array(project["deadlines"])
        project_entries
      end
      upcoming = entries.reject { |item| item["done"] || item["date"].blank? }.map do |item|
        item.merge("overdue" => item["date"] < today.iso8601)
      end.sort_by { |item| [ item["date"], item["title"], item["label"] ] }
      { "entries" => upcoming, "has_entries" => upcoming.any?, "today" => today.iso8601 }
    end

    private

    def hash_value(value)
      return value.to_unsafe_h.stringify_keys if value.respond_to?(:to_unsafe_h)
      return value.stringify_keys if value.is_a?(Hash)

      {}
    end

    def rows(value)
      return value if value.is_a?(Array)
      return value.values if value.is_a?(Hash)

      []
    end

    def normalize_date(value)
      text = value.to_s.strip
      return "" if text.blank?

      text = "#{text[6, 4]}-#{text[3, 2]}-#{text[0, 2]}" if text.match?(/\A\d{2}\/\d{2}\/\d{4}\z/)
      Date.iso8601(text).iso8601
    rescue Date::Error
      ""
    end

    def bounded(value, limit)
      value.to_s.strip[0, limit]
    end

    def integer_or_nil(value)
      return value if value.is_a?(Integer) && value >= 0
      return if value.to_s.blank?

      number = Integer(value, 10)
      number if number >= 0
    rescue ArgumentError, TypeError
      nil
    end

    def truthy?(value)
      value == true || value.to_s == "1" || value.to_s.casecmp("true").zero?
    end

    def paper_type?(project_type)
      %w[paper paper_project paper_final].include?(project_type.to_s)
    end

    def template_key(project_type, title)
      normalized = ActiveSupport::Inflector.transliterate(title.downcase)
      aliases = if paper_type?(project_type)
        [
          [ "metodologia", "paper-method" ],
          [ "hipotese", "paper-hypothesis" ],
          [ "hipoteses", "paper-hypothesis" ],
          [ "fontes", "paper-research" ],
          [ "projeto de paper", "paper-project" ],
          [ "paper final", "paper-writing" ],
          [ "conclusao", "paper-conclusion" ]
        ]
      else
        [
          [ "decisoes possiveis", "case-decisions" ],
          [ "debate", "case-debate" ],
          [ "dissertacao", "case-dissertation" ],
          [ "entrega", "case-delivery" ],
          [ "questao juridica", "case-question" ]
        ]
      end
      aliases.find { |fragment, _key| normalized.include?(fragment) }&.last || ""
    end

    def entry(project_id, title, kind, label, due_date)
      date = normalize_date(due_date)
      {
        "project_id" => project_id,
        "title" => title.presence || "Trabalho sem título",
        "kind" => kind,
        "label" => label,
        "date" => date,
        "date_label" => Date.iso8601(date).strftime("%d/%m/%Y")
      }
    end
  end
end
