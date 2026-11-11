class Project < ApplicationRecord
  PROJECT_TYPES = %w[case paper_project paper_final].freeze

  has_many :revisions, class_name: "ProjectRevision", dependent: :destroy, inverse_of: :project
  has_many :ai_usage_reservations, dependent: :destroy
  belongs_to :account, optional: true, inverse_of: :projects

  after_create :record_revision!
  before_validation :normalize_workflow_data

  validates :project_type, inclusion: { in: PROJECT_TYPES }
  validates :title, length: { maximum: 240 }
  validate :current_stage_belongs_to_workflow

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

  def schedule_summary
    AcademicSchedule.summary(schedule, project_type)
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
        "schedule" => schedule,
        "deliveries" => deliveries
      }
    )
  end

  private

  def normalize_workflow_data
    return unless PROJECT_TYPES.include?(project_type)

    self.fields = AcademicWorkflow.normalize_fields(project_type, fields)
    self.checks = AcademicWorkflow.normalize_checks(project_type, checks)
    self.criteria = AcademicWorkflow.normalize_criteria(criteria)
    self.development_sections = AcademicWorkflow.normalize_development_sections(development_sections)
    self.source_ids = AcademicWorkflow.normalize_source_ids(source_ids)
    self.deliveries = AcademicWorkflow.normalize_deliveries(deliveries)
    self.schedule = AcademicSchedule.normalize_schedule(schedule, project_type:, fallback_date: fields["deliveryDate"])
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
