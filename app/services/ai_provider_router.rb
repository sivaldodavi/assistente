class AIProviderRouter
  RETRYABLE_ERRORS = %w[provider_busy provider_unreachable provider_quota].freeze

  def initialize(providers: nil)
    @providers = providers || default_providers
  end

  def complete_json(messages)
    last_retryable_error = nil

    @providers.each do |name, build_client|
      begin
        response = build_client.call.complete_json(messages)
        return response.merge("provider" => name)
      rescue AIProviderError => error
        next if error.code == "secret_unavailable"
        raise unless RETRYABLE_ERRORS.include?(error.code)

        last_retryable_error = error
      end
    end

    raise last_retryable_error || AIProviderError.new(
      "secret_unavailable",
      "A configuração dos serviços de IA está indisponível.",
      503
    )
  end

  private

  def default_providers
    [
      [ "deepseek", -> { deepseek_client } ],
      [ "gemini", -> { gemini_client } ],
      [ "claude", -> { claude_client } ]
    ]
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

  def gemini_client
    GeminiClient.new(
      api_key: AIProviderSecrets.load(
        env_name: "GEMINI_API_KEY",
        file_env_name: "GEMINI_API_KEY_FILE",
        default_file: "/run/secrets/gemini_api_key",
        credential_key: :gemini_api_key
      ),
      api_url: ENV["GEMINI_API_URL"].presence,
      model: ENV.fetch("GEMINI_MODEL", "gemini-2.5-flash"),
      timeout: ENV.fetch("GEMINI_TIMEOUT", 30)
    )
  end

  def claude_client
    ClaudeClient.new(
      api_key: AIProviderSecrets.load(
        env_name: "CLAUDE_API_KEY",
        file_env_name: "CLAUDE_API_KEY_FILE",
        default_file: "/run/secrets/claude_api_key",
        credential_key: :claude_api_key
      ),
      api_url: ENV.fetch("CLAUDE_API_URL", ClaudeClient::API_URL),
      model: ENV.fetch("CLAUDE_MODEL", "claude-sonnet-4-5"),
      timeout: ENV.fetch("CLAUDE_TIMEOUT", 30)
    )
  end
end
