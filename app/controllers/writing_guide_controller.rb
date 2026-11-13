require_relative "ai_assistance"
require_relative "rate_limitable"

class WritingGuideController < ApplicationController
  include AIAssistance
  include RateLimitable

  before_action :authenticate_account!
  before_action :require_ai_consent!
  before_action :limit_questions, only: :ask

  def show
    @question = nil
    @answer = nil
  end

  def ask
    question = params[:question].to_s.strip
    return render_guide_error("Escreva uma dúvida sobre elaboração ou formatação.") if question.blank?
    if question.length > WritingGuide::MAX_QUESTION_LENGTH
      return render_guide_error("A pergunta pode ter até #{WritingGuide::MAX_QUESTION_LENGTH} caracteres.")
    end

    request_id = SecureRandom.uuid
    reserved = false
    completed = false
    AIUsageService.reserve!(account: current_account, project: nil, request_id:, action: "writing_guide", credit_type: "deepseek")
    reserved = true
    response = deepseek_client.complete_json(WritingGuide.messages(question))
    AIUsageService.record_provider_usage!(
      account: current_account,
      request_id:,
      provider: "deepseek",
      operation: "writing_guide",
      model: response["model"],
      usage: response["usage"]
    )
    AIUsageService.finish!(request_id)
    completed = true
    @question = question
    @answer = WritingGuide.answer_from(response["result"])
    render :show
  rescue AIUsageService::UsageError, AIProviderError => error
    render_guide_error(error.message, status: error.status)
  ensure
    AIUsageService.refund!(request_id) if reserved && !completed
  end

  private

  def require_ai_consent!
    return if current_account.terms_accepted? && current_account.ai_consent?

    flash.now[:alert] = current_account.terms_accepted? ? "Autorize o uso de IA nas configurações da conta." : "Aceite os termos antes de usar esta ajuda."
    @question = nil
    @answer = nil
    render :show, status: :forbidden
  end

  def limit_questions
    return unless rate_limited?("writing_guide", limit: 30)

    render_guide_error("Muitas perguntas em pouco tempo. Aguarde alguns minutos.", status: :too_many_requests)
  end

  def render_guide_error(message, status: :unprocessable_entity)
    flash.now[:alert] = message
    @question = params[:question].to_s.strip.first(WritingGuide::MAX_QUESTION_LENGTH)
    @answer = nil
    render :show, status: status
  end
end
