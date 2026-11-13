require_relative "ai_assistance"
require_relative "rate_limitable"

class ProjectAssistController < ApplicationController
  include AIAssistance
  include RateLimitable

  before_action :authenticate_account!
  before_action :set_project
  before_action :require_ai_consent!
  before_action :limit_ai_requests, only: %i[action jev_report jev_section jev_assessment]

  def action
    body = body_parameters
    action_name = body["action"].to_s
    return render_error("invalid_ai_action", "Ação de assistência inválida.", :bad_request) unless AIWorkflow.action?(action_name)
    return render_error("invalid_ai_action", "O apoio ao debate só existe no Case.", :bad_request) if action_name == "debate_coach" && @project.project_type != "case"
    return render_error("invalid_ai_request", "Campo não permitido.", :bad_request) if action_name == "review" && !@project.fields.key?(body["field_id"])

    request_id = SecureRandom.uuid
    reserved = false
    completed = false
    AIUsageService.reserve!(account: current_account, project: @project, request_id:, action: action_name, credit_type: "deepseek")
    reserved = true
    if body["project_revision"].present? && Integer(body["project_revision"]) != @project.lock_version
      return render json: { error: "stale_project_revision", revision: @project.lock_version }, status: :conflict
    end

    sources = selected_sources
    context = AIWorkflow.action_context(@project, action_name, body, sources:)
    response = ai_provider_router.complete_json(AIWorkflow.action_messages(context))
    result = AIWorkflow.validate_action_result(response["result"], context)
    AIUsageService.record_provider_usage!(
      account: current_account,
      request_id:,
      provider: response["provider"],
      operation: "assistant:#{action_name}",
      model: response["model"],
      usage: response["usage"]
    )
    AIUsageService.finish!(request_id)
    completed = true
    render json: {
      ok: true,
      request_id:,
      response: result.merge("action" => action_name, "model" => response["model"], "provider" => response["provider"])
    }
  rescue AIUsageService::UsageError => error
    render_error(error.code, error.message, error.status)
  rescue AIProviderError => error
    render_error(error.code, error.message, error.status)
  rescue ArgumentError, TypeError
    render_error("invalid_ai_request", "A solicitação de assistência é inválida.", :bad_request)
  ensure
    AIUsageService.refund!(request_id) if reserved && !completed
  end

  def jev_report
    analyze_jev(stage: "case_report")
  end

  def jev_section
    section = body_parameters["section"].to_s
    return render_error("invalid_section", "Etapa de avaliação inválida.", :bad_request) unless JevRubric::CHECKLISTS.key?(section)

    analyze_jev(section:)
  end

  def jev_assessment
    body = body_parameters
    stage = body["stage"].to_s
    unless JevRubric::STAGES_BY_PROJECT.fetch(@project.project_type, []).include?(stage)
      return render_error("invalid_assessment_stage", "Etapa de avaliação inválida para este projeto.", :bad_request)
    end
    if body["project_revision"].present? && Integer(body["project_revision"]) != @project.lock_version
      return render json: { error: "stale_project_revision", revision: @project.lock_version }, status: :conflict
    end

    analyze_jev(stage:)
  end

  private

  def limit_ai_requests
    return unless rate_limited?("ai", limit: 30)

    render_error("rate_limited", "Muitas solicitações de IA em pouco tempo. Aguarde alguns minutos.", :too_many_requests)
  end

  def set_project
    @project = current_account.projects.find(params[:project_id])
  end

  def analyze_jev(section: nil, stage: nil)
    return render_error("assessment_case_only", "Esta etapa de avaliação está disponível apenas para Cases.", :bad_request) if section && @project.project_type != "case"

    request_id = SecureRandom.uuid
    raw = jev_client.score(
      AIWorkflow.prompt_state(@project, sources: selected_sources),
      AIWorkflow.jev_questions(section, stage:)
    )
    analysis = AIWorkflow.normalize_jev_result(raw, section:, stage:)
    assessment_stage = section ? "case_section:#{section}" : stage
    analysis["stage"] = assessment_stage
    analysis["rubric_version"] ||= JevRubric::VERSION
    AIUsageService.record_provider_usage!(
      account: current_account,
      request_id:,
      provider: "jev",
      operation: section ? "case-section:#{section}" : stage,
      model: analysis["model"],
      usage: raw["usage"]
    )
    revision = @project.revisions.find_by!(revision: @project.lock_version)
    JevAssessment.create!(
      account: current_account,
      project: @project,
      project_revision: revision,
      stage: assessment_stage,
      rubric_version: analysis["rubric_version"],
      model: analysis["model"],
      result: analysis
    )
    render json: { ok: true, request_id:, analysis: }
  rescue AIProviderError => error
    render_error(error.code, error.message, error.status)
  rescue ArgumentError, TypeError
    render_error("invalid_ai_request", "A solicitação de avaliação é inválida.", :bad_request)
  end

  def body_parameters
    request.request_parameters.deep_stringify_keys
  end

  def selected_sources
    current_account.sources.where(public_id: @project.source_ids).map do |source|
      source.attributes.merge("id" => source.public_id)
    end
  end

  def jev_client
    JevClient.new(
      api_key: AIProviderSecrets.load(
        env_name: "TYPESAFE_API_KEY",
        file_env_name: "TYPESAFE_API_KEY_FILE",
        default_file: "/run/secrets/typesafe_api_key",
        credential_key: :typesafe_api_key
      ),
      api_url: ENV.fetch("TYPESAFE_API_URL", JevClient::API_URL),
      model: ENV.fetch("TYPESAFE_MODEL", "jev-latest"),
      timeout: ENV.fetch("JEV_TIMEOUT", 60)
    )
  end

  def render_error(code, message, status)
    render json: { error: code, message: }, status:
  end
end
