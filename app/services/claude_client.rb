class ClaudeClient < AIJsonProvider
  API_URL = "https://api.anthropic.com/v1/messages"
  API_VERSION = "2023-06-01"

  def initialize(api_key:, model: "claude-sonnet-4-5", api_url: API_URL, timeout: 30)
    @model = model
    super(api_key:, api_url:, timeout:, api_key_header: "x-api-key", api_key_prefix: "")
  end

  def complete_json(messages, max_tokens: 2_200)
    system = messages.filter_map do |message|
      content_text(message["content"]) if message["role"] == "system"
    end.join("\n\n")
    conversation = messages.filter_map do |message|
      next if message["role"] == "system"
      next unless %w[user assistant].include?(message["role"])

      { role: message["role"], content: content_text(message["content"]) }
    end
    payload = {
      model: @model,
      max_tokens: Integer(max_tokens).clamp(1, 4_000),
      messages: conversation
    }
    payload[:system] = system if system.present?
    response = post_json(payload, headers: { "anthropic-version" => API_VERSION })
    blocks = response["content"]
    text = blocks.filter_map { |block| block["text"] if block.is_a?(Hash) && block["type"] == "text" }.join if blocks.is_a?(Array)
    result = JSON.parse(text) if text.is_a?(String)
    raise AIProviderError.new("invalid_response", "O serviço de orientação não retornou uma resposta válida.", 502) unless result.is_a?(Hash)

    usage = response["usage"].is_a?(Hash) ? response["usage"] : {}
    {
      "model" => response["model"].presence || @model,
      "result" => result,
      "usage" => {
        "prompt_tokens" => usage["input_tokens"],
        "completion_tokens" => usage["output_tokens"]
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
