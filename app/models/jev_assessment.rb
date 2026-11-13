class JevAssessment < ApplicationRecord
  belongs_to :account
  belongs_to :project
  belongs_to :project_revision

  validates :stage, inclusion: { in: JevRubric::ASSESSMENT_STAGES }
  validates :rubric_version, :model, presence: true
  validates :result, presence: true
  validate :revision_belongs_to_project

  private

  def revision_belongs_to_project
    return if project_revision.blank? || project_id.blank?

    return unless project_revision.project_id == project_id

    project_type = project_revision.project.project_type
    valid_stage = if stage.to_s.start_with?("case_section:")
      project_type == "case"
    else
      JevRubric::STAGES_BY_PROJECT.fetch(project_type, []).include?(stage)
    end
    return if valid_stage

    errors.add(:project_revision, "não pertence ao projeto avaliado")
  end
end
