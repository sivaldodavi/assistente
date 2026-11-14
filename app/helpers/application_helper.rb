module ApplicationHelper
  PROJECT_DELIVERY_FIELDS = {
    "case" => [
      [ "report_delivery_date", "Relatório", "report" ],
      [ "debate_delivery_date", "Debate", "debate" ],
      [ "dissertation_delivery_date", "Dissertação", "dissertation" ]
    ],
    "paper_project" => [
      [ "paper_project_delivery_date", "Projeto de paper · 1º BI", "paper_project" ]
    ],
    "paper_final" => [
      [ "paper_project_delivery_date", "Projeto de paper · 1º BI", "paper_project" ],
      [ "paper_final_delivery_date", "Paper final · 2º BI", "paper_final" ]
    ]
  }.freeze
  NAVIGATION_ICONS = {
    home: "M10 2 2 9h2v8h5v-5h2v5h5V9h2z",
    projects: "M4 3h12v14H4z M7 6h6 M7 9h6 M7 12h4",
    metrics: "M3 16h14 M5 13V9 M10 13V5 M15 13V7",
    chat: "M3 4h14v10H8l-5 3z M6 7h8 M6 10h5",
    guide: "m10 2 1.8 5.2L17 9l-5.2 1.8L10 16l-1.8-5.2L3 9l5.2-1.8z M16 13l.8 2.2L19 16l-2.2.8L16 19l-.8-2.2L13 16l2.2-.8z",
    library: "M4 3h12v14H4z M7 6h6 M7 9h6 M7 12h6",
    settings: "M10 3v2 M10 15v2 M3 10h2 M15 10h2 M5.1 5.1l1.4 1.4m7 7 1.4 1.4m0-9.9-1.4 1.4m-7 7-1.4 1.4 M13.5 10a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
  }.freeze

  WORKFLOW_PHASE_LABELS = {
    "report" => "Relatório",
    "debate" => "Debate",
    "dissertation" => "Dissertação",
    "paper_project" => "Projeto de paper",
    "paper_final" => "Paper final"
  }.freeze

  def workflow_phase_label(phase)
    WORKFLOW_PHASE_LABELS.fetch(phase.to_s, phase.to_s.humanize)
  end

  # Títulos do roteiro trazem o número no JSON ("1 · Descrição do caso"); a navegação já mostra o número.
  def stage_display_title(title)
    title.to_s.sub(/\A[\d.]+ · /, "")
  end

  def assessment_button_label(project, stage)
    case project.project_type
    when "case" then stage["phase"] == "dissertation" ? "Avaliar dissertação" : "Avaliar relatório"
    when "paper_project" then "Avaliar projeto de paper"
    else "Avaliar paper final"
    end
  end

  def brl(cents)
    number_to_currency(cents / 100.0, unit: "R$ ", separator: ",", delimiter: ".")
  end

  def project_type_label(project_type)
    {
      "case" => "Case",
      "paper_project" => "Projeto de paper",
      "paper_final" => "Paper final"
    }.fetch(project_type.to_s, project_type.to_s.humanize)
  end

  def navigation_icon(name)
    path = NAVIGATION_ICONS.fetch(name.to_sym)
    tag.svg(
      xmlns: "http://www.w3.org/2000/svg",
      width: 18,
      height: 18,
      viewBox: "0 0 20 20",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": 1.7,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      "aria-hidden": true
    ) { tag.path(d: path) }
  end

  def jev_stage_label(stage)
    return "Etapa do relatório" if stage.to_s.start_with?("case_section:")

    {
      "case_report" => "Relatório do Case",
      "case_dissertation" => "Dissertação do Case",
      "paper_project" => "Projeto de paper",
      "paper_final" => "Paper final"
    }.fetch(stage.to_s, stage.to_s.humanize)
  end

  def jev_assessment_score(assessment)
    result = assessment.result
    return "Etapa avaliada" unless result["expected_points"] && result["assessable_points"]

    "#{result["expected_points"]}/#{result["assessable_points"]} pontos indicativos"
  end

  def project_status(project)
    section = project.section_for
    return [ "Entregue", "delivered" ] if project.delivered?(section)
    return [ "Em revisão", "review" ] if section["custom"] == "review"

    [ "Em andamento", "in-progress" ]
  end

  def project_delivery_items(project)
    Array(PROJECT_DELIVERY_FIELDS[project.project_type]).filter_map do |field, label, delivery_key|
      next if project.deliveries.dig(delivery_key, "delivered") == true

      value = project.fields[field].to_s
      next if value.blank?

      { project:, field:, label:, date: Date.iso8601(value) }
    rescue Date::Error
      nil
    end
  end

  def upcoming_deliveries(projects, limit: 3)
    projects.flat_map { |project| project_delivery_items(project) }
      .select { |item| item[:date] >= Date.current }
      .sort_by { |item| [ item[:date], item[:project].title ] }
      .first(limit)
  end

  def next_project_delivery(project)
    project_delivery_items(project)
      .select { |item| item[:date] >= Date.current }
      .min_by { |item| item[:date] }
  end
end
