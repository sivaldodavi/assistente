require_relative "ai_assistance"
require_relative "rate_limitable"

class ChatController < ApplicationController
  include AIAssistance
  include RateLimitable

  before_action :authenticate_account!
  before_action :limit_ai_requests, only: :ask

  def show
    @mode = %w[guided import].include?(params[:mode].to_s) ? params[:mode].to_s : "chat"
    @project_type = %w[case paper_project].include?(params[:project_type].to_s) ? params[:project_type].to_s : "case"
    @projects = current_account.projects.order(updated_at: :desc)
    stored_context = session[:chat_context].respond_to?(:to_h) ? session[:chat_context].to_h.stringify_keys : {}
    project_id = params.key?(:project_id) ? params[:project_id] : stored_context["project_id"]
    @project = current_account.projects.find_by(id: project_id) if project_id.present?
    if project_id.present? && @project.nil?
      session.delete(:chat_context)
      flash.now[:alert] = "O projeto escolhido não está disponível."
    end

    requested_scope = params[:scope].presence || params[:stage].presence || stored_context["scope"]
    @scope = valid_scope?(@project, requested_scope) ? requested_scope : "project"
    @stages = @project ? @project.sections.map { |section| [ section["title"], section["id"] ] } : []
    if @project
      session[:chat_context] = { "project_id" => @project.id, "scope" => @scope }
    else
      session.delete(:chat_context)
    end
    @ai_ready = current_account.terms_accepted? && current_account.ai_consent?
    @has_credits = current_account.admin? || current_account.deepseek_credits_remaining.positive?
    @has_project_credit = current_account.admin? || current_account.project_credits_remaining.positive?
  end

  def ask
    return render_error("ai_consent_required", "Autorize o uso de IA nas configurações da conta.", :forbidden) unless current_account.terms_accepted? && current_account.ai_consent?

    body = request.request_parameters.deep_stringify_keys
    message = body["message"].to_s.strip
    return render_error("empty_message", "Escreva uma pergunta para continuar.", :unprocessable_entity) if message.blank?
    if message.length > ProjectChatWorkflow::MAX_MESSAGE_LENGTH
      return render_error("message_too_long", "A pergunta pode ter até #{ProjectChatWorkflow::MAX_MESSAGE_LENGTH} caracteres.", :unprocessable_entity)
    end

    project_id = body["project_id"].presence
    project = current_account.projects.find_by(id: project_id) if project_id
    return render_error("project_not_found", "O projeto escolhido não está disponível.", :not_found) if project_id && !project

    scope = body["scope"].presence || "project"
    return render_error("invalid_scope", "Escolha uma etapa válida do projeto.", :bad_request) unless valid_scope?(project, scope)

    if project
      session[:chat_context] = { "project_id" => project.id, "scope" => scope }
    else
      session.delete(:chat_context)
    end
    workflow = ProjectChatWorkflow.new(project:, scope:, message:, messages: body["messages"])
    request_id = SecureRandom.uuid
    reserved = false
    completed = false
    AIUsageService.reserve!(account: current_account, project:, request_id:, action: "chat", credit_type: "deepseek")
    reserved = true
    response = ai_provider_router.complete_json(workflow.request_messages)
    answer = workflow.validate_result(response["result"])
    AIUsageService.record_provider_usage!(
      account: current_account,
      request_id:,
      provider: response["provider"],
      operation: "chat",
      model: response["model"],
      usage: response["usage"]
    )
    AIUsageService.finish!(request_id)
    completed = true
    render json: { ok: true, answer: }
  rescue AIUsageService::UsageError, AIProviderError => error
    render_error(error.code, error.message, error.status)
  rescue ArgumentError, TypeError
    render_error("invalid_chat_request", "Não foi possível processar a pergunta.", :bad_request)
  ensure
    AIUsageService.refund!(request_id) if reserved && !completed
  end

  private

  def valid_scope?(project, scope)
    return scope == "project" unless project
    return true if scope == "project"

    project.sections.any? { |section| section["id"] == scope.to_s }
  end

  def limit_ai_requests
    return unless rate_limited?("ai", limit: 30)

    render_error("rate_limited", "Não foi possível enviar agora. Tente novamente em alguns instantes.", :too_many_requests)
  end

  def render_error(code, message, status)
    render json: { error: code, message: }, status:
  end
end
