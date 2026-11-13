class PublicPagesController < ApplicationController
  def home
    return if current_account.nil? || public_shell_only?

    @projects = current_account.projects.order(updated_at: :desc).to_a
    @recent_project = @projects.first
    @upcoming_deliveries = view_context.upcoming_deliveries(@projects)
    @profile_complete = current_account.name.present? &&
      current_account.profile.values_at("course", "period", "shift").all?(&:present?)
    @has_projects = @projects.any?
    @has_delivery_dates = @projects.any? do |project|
      view_context.project_delivery_items(project).any?
    end
  end

  def terms
  end

  def privacy
  end

  def ai_help
  end
end
