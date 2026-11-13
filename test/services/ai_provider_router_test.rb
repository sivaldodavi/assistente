require "test_helper"

class AIProviderRouterTest < ActiveSupport::TestCase
  test "falls back in order and returns the provider that completed the request" do
    calls = []
    providers = [
      [ "deepseek", -> { fake_client("deepseek", calls, error: provider_error("provider_busy")) } ],
      [ "gemini", -> { fake_client("gemini", calls, result: { "model" => "gemini-test", "result" => { "answer" => "ok" } }) } ],
      [ "claude", -> { fake_client("claude", calls, result: {}) } ]
    ]

    response = AIProviderRouter.new(providers:).complete_json([])

    assert_equal %w[deepseek gemini], calls
    assert_equal "gemini", response["provider"]
    assert_equal "gemini-test", response["model"]
  end

  test "does not fall back for invalid provider responses" do
    calls = []
    providers = [
      [ "deepseek", -> { fake_client("deepseek", calls, error: provider_error("invalid_response")) } ],
      [ "gemini", -> { fake_client("gemini", calls, result: {}) } ]
    ]

    error = assert_raises(AIProviderError) do
      AIProviderRouter.new(providers:).complete_json([])
    end

    assert_equal "invalid_response", error.code
    assert_equal [ "deepseek" ], calls
  end

  test "skips providers without configured secrets and reports when none are available" do
    providers = [
      [ "deepseek", -> { raise provider_error("secret_unavailable") } ],
      [ "gemini", -> { raise provider_error("secret_unavailable") } ]
    ]

    error = assert_raises(AIProviderError) do
      AIProviderRouter.new(providers:).complete_json([])
    end

    assert_equal "secret_unavailable", error.code
  end

  private

  def fake_client(name, calls, result: nil, error: nil)
    Object.new.tap do |client|
      client.define_singleton_method(:complete_json) do |_messages|
        calls << name
        raise error if error

        result
      end
    end
  end

  def provider_error(code)
    AIProviderError.new(code, "Erro de teste", 503)
  end
end
