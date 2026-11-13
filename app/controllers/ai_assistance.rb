module AIAssistance
  extend ActiveSupport::Concern

  private

  def require_ai_consent!
    return if current_account.terms_accepted? && current_account.ai_consent?

    code = current_account.terms_accepted? ? "ai_consent_required" : "terms_required"
    message = current_account.terms_accepted? ? "Autorize o uso de IA nas configurações da conta." : "Aceite os termos antes de usar a assistência."
    render_error(code, message, :forbidden)
  end

  def deepseek_client
    DeepSeekClient.new(
      api_key: AIProviderSecrets.load(
        env_name: "DEEPSEEK_API_KEY",
        file_env_name: "DEEPSEEK_API_KEY_FILE",
        default_file: "/run/secrets/deepseek_api_key",
        credential_key: :deepseek_api_key
      ),
      api_url: ENV.fetch("DEEPSEEK_API_URL", DeepSeekClient::API_URL),
      model: ENV.fetch("DEEPSEEK_MODEL", "deepseek-flash"),
      timeout: ENV.fetch("DEEPSEEK_TIMEOUT", 30)
    )
  end
end
