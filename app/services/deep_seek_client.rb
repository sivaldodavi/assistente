class DeepSeekClient < AIJsonProvider
  API_URL = "https://api.deepseek.com/chat/completions"

  def initialize(api_key:, api_url: API_URL, model: "deepseek-chat", timeout: 30)
    @model = model
    super(api_key:, api_url:, timeout:)
  end

  def complete_json(messages, max_tokens: 2_200)
    response = post_json({
      model: @model,
      messages:,
      response_format: { type: "json_object" },
      max_tokens: Integer(max_tokens).clamp(1, 4_000),
      stream: false
    })
    choices = response["choices"]
    content = choices.first.dig("message", "content") if choices.is_a?(Array) && choices.one?
    result = JSON.parse(content) if content.is_a?(String)
    raise AIProviderError.new("invalid_response", "DeepSeek não retornou JSON válido.", 502) unless result.is_a?(Hash)

    { "model" => response["model"].presence || @model, "result" => result, "usage" => response["usage"].is_a?(Hash) ? response["usage"] : {} }
  rescue JSON::ParserError
    raise AIProviderError.new("invalid_response", "DeepSeek não retornou JSON válido.", 502)
  end
end
