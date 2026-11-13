require_relative "ai_assistance"
require_relative "rate_limitable"

class ProjectStudioController < ApplicationController
  include AIAssistance
  include RateLimitable

  before_action :authenticate_account!
  before_action :require_institution_profile
  before_action :require_ai_consent!, only: :draft
  before_action :limit_ai_requests, only: :draft

  def show
  end

  def draft
    unless current_account.admin? || current_account.project_credits_remaining.positive?
      return render_error("project_credit_required", "Você precisa de um crédito de projeto para criar o trabalho. Confira os pacotes disponíveis.", :payment_required)
    end

    body = request.request_parameters.deep_stringify_keys
    workflow = ProjectStudioWorkflow.new(
      project_type: body["project_type"],
      mode: body["mode"],
      prompt: body["prompt"],
      source_text: body["source_text"],
      messages: body["messages"]
    )
    request_id = SecureRandom.uuid
    reserved = false
    completed = false
    AIUsageService.reserve!(
      account: current_account,
      project: nil,
      request_id:,
      action: "studio:#{workflow_mode(body)}",
      credit_type: "deepseek"
    )
    reserved = true
    response = deepseek_client.complete_json(workflow.request_messages)
    result = workflow.validate_result(response["result"])
    AIUsageService.record_provider_usage!(
      account: current_account,
      request_id:,
      provider: "deepseek",
      operation: "studio:#{workflow_mode(body)}",
      model: response["model"],
      usage: response["usage"]
    )
    AIUsageService.finish!(request_id)
    completed = true
    render json: { ok: true, request_id:, model: response["model"], response: result }
  rescue AIUsageService::UsageError => error
    render_error(error.code, error.message, error.status)
  rescue AIProviderError => error
    render_error(error.code, error.message, error.status)
  rescue ArgumentError, TypeError
    render_error("invalid_ai_request", "A solicitação de orientação é inválida.", :bad_request)
  ensure
    AIUsageService.refund!(request_id) if reserved && !completed
  end

  private

  def workflow_mode(body)
    ProjectStudioWorkflow::MODES.include?(body["mode"].to_s) ? body["mode"].to_s : "guided"
  end

  def require_institution_profile
    return if current_account.profile["institution"].present?

    redirect_to account_settings_path(anchor: "profile"), alert: "Informe sua faculdade ou instituição antes de iniciar um projeto."
  end

  def limit_ai_requests
    return unless rate_limited?("ai", limit: 30)

    render_error("rate_limited", "Muitas solicitações de IA em pouco tempo. Aguarde alguns minutos.", :too_many_requests)
  end

  def render_error(code, message, status)
    render json: { error: code, message: }, status:
  end
end
