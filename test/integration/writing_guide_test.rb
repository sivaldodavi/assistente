require "test_helper"

class WritingGuideTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "guia@example.test")
    @account.update!(terms_accepted: true, ai_consent: true, deepseek_limit: 100)
  end

  test "guide requires sign in" do
    get writing_guide_path

    assert_redirected_to login_path
  end

  test "guide requires AI consent" do
    @account.update!(ai_consent: false)
    sign_in_as(@account)

    get writing_guide_path

    assert_response :forbidden
  end

  test "guide answers a question without creating or touching a project" do
    sign_in_as(@account)

    with_fake_guide_client("answer" => "A margem superior e a esquerda são de 3 cm.") do
      post writing_guide_questions_path, params: { question: "Quais são as margens?" }
    end

    assert_response :success
    assert_includes response.body, "margem superior"
    reservation = AIUsageReservation.find_by(action: "writing_guide")
    assert_nil reservation.project_id
    assert_equal "complete", reservation.status
  end

  test "guide rejects empty and overlong questions" do
    sign_in_as(@account)

    post writing_guide_questions_path, params: { question: "   " }
    assert_response :unprocessable_entity

    post writing_guide_questions_path, params: { question: "x" * (WritingGuide::MAX_QUESTION_LENGTH + 1) }
    assert_response :unprocessable_entity
  end

  test "guide limits how many questions an account can send in a window" do
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new
    sign_in_as(@account)

    with_fake_guide_client("answer" => "Resposta.") do
      30.times { post writing_guide_questions_path, params: { question: "Como citar a CLT?" } }
      post writing_guide_questions_path, params: { question: "Como citar a CLT?" }
    end

    assert_response :too_many_requests
  ensure
    Rails.cache = original_cache
  end

  private

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end

  def with_fake_guide_client(result)
    client = Object.new
    client.define_singleton_method(:complete_json) do |messages|
      raise "pergunta ausente" unless messages.last["content"]["pergunta"].present?

      { "model" => "fake-deepseek", "result" => result, "usage" => { "prompt_tokens" => 10, "completion_tokens" => 12 } }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, client) do
        yield
      end
    end
  end
end
