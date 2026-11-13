module AIAssistance
  extend ActiveSupport::Concern

  private

  def require_ai_consent!
    return if current_account.terms_accepted? && current_account.ai_consent?

    code = current_account.terms_accepted? ? "ai_consent_required" : "terms_required"
    message = current_account.terms_accepted? ? "Autorize o uso de IA nas configurações da conta." : "Aceite os termos antes de usar a assistência."
    render_error(code, message, :forbidden)
  end

  def ai_provider_router
    AIProviderRouter.new
  end
end
