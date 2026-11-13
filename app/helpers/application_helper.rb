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

  def project_type_label(project_type)
    {
      "case" => "Case",
      "paper_project" => "Projeto de paper",
      "paper_final" => "Paper final"
    }.fetch(project_type.to_s, project_type.to_s.humanize)
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
