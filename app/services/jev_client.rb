class JevClient < AIJsonProvider
  API_URL = "https://api.typesafe.ai/v1/systemone"

  def initialize(api_key:, api_url: API_URL, model: "jev-latest", timeout: 60)
    @model = model
    super(api_key:, api_url:, timeout:)
  end

  def score(state, questions)
    response = post_json({ state:, model: @model, questions: })
    raise AIProviderError.new("invalid_response", "O serviço de avaliação não retornou respostas estruturadas.", 502) unless response["answers"].is_a?(Hash)

    { "model" => response["model"].presence || @model, "answers" => response["answers"], "usage" => response["usage"].is_a?(Hash) ? response["usage"] : {} }
  end
end
