class GeminiClient < AIJsonProvider
  API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

  def initialize(api_key:, model: "gemini-2.5-flash", api_url: nil, timeout: 30)
    @model = model
    base_url = api_url.presence || "#{API_URL}/#{URI.encode_uri_component(model)}:generateContent"
    super(api_key:, api_url: base_url, timeout:, api_key_header: "x-goog-api-key", api_key_prefix: "")
  end

  def complete_json(messages, max_tokens: 2_200)
    system_parts = messages.filter_map do |message|
      content_text(message["content"]) if message["role"] == "system"
    end
    contents = messages.filter_map do |message|
      next if message["role"] == "system"

      role = message["role"] == "assistant" ? "model" : "user"
      { role:, parts: [ { text: content_text(message["content"]) } ] }
    end
    payload = {
      contents:,
      generationConfig: {
        responseMimeType: "application/json",
        maxOutputTokens: Integer(max_tokens).clamp(1, 4_000)
      }
    }
    payload[:systemInstruction] = { parts: system_parts.map { |text| { text: } } } if system_parts.any?
    response = post_json(payload)
    candidate = response["candidates"].first if response["candidates"].is_a?(Array)
    content = candidate.dig("content", "parts") if candidate.is_a?(Hash)
    text = content.filter_map { |part| part["text"] if part.is_a?(Hash) }.join if content.is_a?(Array)
    result = JSON.parse(text) if text.is_a?(String)
    raise AIProviderError.new("invalid_response", "O serviço de orientação não retornou uma resposta válida.", 502) unless result.is_a?(Hash)

    usage = response["usageMetadata"].is_a?(Hash) ? response["usageMetadata"] : {}
    {
      "model" => response["modelVersion"].presence || @model,
      "result" => result,
      "usage" => {
        "prompt_tokens" => usage["promptTokenCount"],
        "completion_tokens" => usage["candidatesTokenCount"]
      }
    }
  rescue JSON::ParserError
    raise AIProviderError.new("invalid_response", "O serviço de orientação não retornou uma resposta válida.", 502)
  end

  private

  def content_text(value)
    value.is_a?(String) ? value : JSON.generate(value)
  end
end
