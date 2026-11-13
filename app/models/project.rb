class Project < ApplicationRecord
  PROJECT_TYPES = %w[case paper_project paper_final].freeze
  DELIVERY_DATE_LABELS = {
    "report_delivery_date" => "Data de entrega do relatório",
    "debate_delivery_date" => "Data do debate",
    "dissertation_delivery_date" => "Data de entrega da dissertação",
    "paper_project_delivery_date" => "Data de entrega do projeto de paper",
    "paper_final_delivery_date" => "Data de entrega do paper final"
  }.freeze

  has_many :revisions, class_name: "ProjectRevision", dependent: :destroy, inverse_of: :project
  has_many :ai_usage_reservations, dependent: :destroy
  belongs_to :account, optional: true, inverse_of: :projects

  after_create :record_revision!
  before_validation :normalize_workflow_data

  validates :project_type, inclusion: { in: PROJECT_TYPES }
  validates :title, length: { maximum: 240 }
  validate :current_stage_belongs_to_workflow
  validate :delivery_dates_are_valid

  def sections
    AcademicWorkflow.sections(project_type)
  end

  def section_for(stage_id = current_stage)
    sections.find { |section| section["id"] == stage_id.to_s } || sections.first
  end

  def stage_index(stage_id = current_stage)
    sections.index { |section| section["id"] == stage_id.to_s } || 0
  end

  def progress(phase = section_for["phase"])
    AcademicWorkflow.progress(project_type, fields, phase)
  end

  def review_summary(phase = section_for["phase"])
    AcademicWorkflow.review_summary(project_type, checks, phase)
  end

  # Avisos de ordem entre as datas do Case. Não impedem salvar, porque o calendário pode mudar.
  def schedule_warnings
    report = parse_iso_date(fields["report_delivery_date"])
    debate = parse_iso_date(fields["debate_delivery_date"])
    dissertation = parse_iso_date(fields["dissertation_delivery_date"])
    warnings = []
    warnings << "A entrega do relatório é depois da data do debate." if report && debate && report > debate
    warnings << "O debate é depois da entrega da dissertação." if debate && dissertation && debate > dissertation
    warnings << "A entrega do relatório é depois da entrega da dissertação." if report && dissertation && report > dissertation
    paper_project = parse_iso_date(fields["paper_project_delivery_date"])
    paper_final = parse_iso_date(fields["paper_final_delivery_date"])
    warnings << "A entrega do paper final é antes do projeto de paper." if paper_project && paper_final && paper_final < paper_project
    warnings
  end

  def delivery_key(section = section_for)
    return "report" if project_type == "case" && section["phase"] == "report"
    return "dissertation" if section["phase"] == "dissertation"
    return "paper_project" if project_type == "paper_project"

    "paper_final"
  end

  def delivered?(section = section_for)
    deliveries.dig(delivery_key(section), "delivered") == true
  end

  def record_revision!
    revisions.create!(
      revision: lock_version,
      snapshot: {
        "project_type" => project_type,
        "fields" => fields,
        "checks" => checks,
        "criteria" => criteria,
        "development_sections" => development_sections,
        "source_ids" => source_ids,
        "deliveries" => deliveries
      }
    )
  end

  def fields=(value)
    if value.respond_to?(:to_h)
      v_hash = value.to_h.stringify_keys
      @raw_delivery_dates ||= {}
      DELIVERY_DATE_LABELS.each_key do |k|
        @raw_delivery_dates[k] = v_hash[k].to_s if v_hash.key?(k) && !@normalizing_workflow
      end
    end
    super
  end

  private

  def delivery_dates_are_valid
    raw_source = @raw_delivery_dates || fields
    DELIVERY_DATE_LABELS.each do |key, label|
      value = raw_source.key?(key) ? raw_source[key].to_s : fields[key].to_s
      next if value.blank? || parse_iso_date(value)

      errors.add(:base, "#{label} inválida. Use uma data válida do calendário.")
    end
  end

  def parse_iso_date(value)
    return nil if value.blank?

    Date.iso8601(value.to_s)
  rescue Date::Error
    nil
  end

  def normalize_workflow_data
    return unless PROJECT_TYPES.include?(project_type)

    @normalizing_workflow = true
    self.fields = AcademicWorkflow.normalize_fields(project_type, fields)
    @normalizing_workflow = false
    self.development_sections = project_type == "case" ? [] : AcademicWorkflow.normalize_development_sections(development_sections)
    self.checks = AcademicWorkflow.normalize_checks(project_type, checks)
    self.criteria = AcademicWorkflow.normalize_criteria(criteria)
    self.source_ids = AcademicWorkflow.normalize_source_ids(source_ids)
    self.deliveries = AcademicWorkflow.normalize_deliveries(deliveries)
    self.current_stage = AcademicWorkflow.first_stage_id(project_type) unless sections.any? { |section| section["id"] == current_stage }
    self.title = fields["title"].presence || default_title
  end

  def current_stage_belongs_to_workflow
    return if !PROJECT_TYPES.include?(project_type) || sections.any? { |section| section["id"] == current_stage }

    errors.add(:current_stage, "não pertence ao roteiro deste projeto")
  end

  def default_title
    project_type == "case" ? "Novo Case" : "Novo Projeto de Paper"
  end
end
