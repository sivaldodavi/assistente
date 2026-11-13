class PublicPagesController < ApplicationController
  MONTH_LABELS = %w[jan fev mar abr mai jun jul ago set out nov dez].freeze

  before_action :authenticate_account!, only: :metrics

  def home
    return if current_account.nil? || public_shell_only?

    @projects = current_account.projects.includes(full_jev_assessments: :project_revision).order(updated_at: :desc).to_a
    @recent_project = @projects.first
    @upcoming_deliveries = view_context.upcoming_deliveries(@projects)
    @profile_complete = current_account.name.present? &&
      current_account.profile.values_at("institution", "course", "period", "shift").all?(&:present?)
    @has_projects = @projects.any?
    @has_delivery_dates = @projects.any? do |project|
      view_context.project_delivery_items(project).any?
    end
  end

  def metrics
    @projects = current_account.projects.includes(full_jev_assessments: :project_revision).order(updated_at: :desc).to_a
    @active_project_count = @projects.count { |project| !project.delivered? }
    progress = @projects.map(&:progress)
    completed_fields = progress.sum { |item| item["done"] }
    required_fields = progress.sum { |item| item["total"] }
    @project_completion_percent = required_fields.positive? ? (completed_fields * 100.0 / required_fields).round : 0
    @analytics_period = params[:period].to_s.in?(%w[30 90 all]) ? params[:period].to_s : "30"
    assessments = current_account.jev_assessments.includes(:project, :project_revision)
    assessments = assessments.where("jev_assessments.created_at >= ?", @analytics_period.to_i.days.ago) unless @analytics_period == "all"
    @recent_jev_assessments = assessments.order(created_at: :desc).limit(5)
    @jev_assessment_count = assessments.count
    @monthly_activity = monthly_revision_activity
  end

  def terms
  end

  def privacy
  end

  def ai_help
  end

  private

  def monthly_revision_activity
    months = 5.downto(0).map { |offset| Time.current.beginning_of_month - offset.months }
    revisions = ProjectRevision.where(project_id: @projects.map(&:id), created_at: months.first.beginning_of_month..Time.current.end_of_month)
    counts = revisions.pluck(:created_at).group_by { |created_at| created_at.beginning_of_month.to_date }.transform_values(&:length)
    months.map do |month|
      { label: "#{MONTH_LABELS[month.month - 1]}/#{month.year}", count: counts.fetch(month.to_date, 0) }
    end
  end
end
