require "test_helper"

class ProjectAssistTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "assist@example.test")
    @account.update!(terms_accepted: true, ai_consent: true)
    sign_in_as(@account)
    @project = @account.projects.create!(project_type: "case", fields: { "problem" => "Qual é a questão jurídica?" })
  end

  test "DeepSeek suggestions are validated and do not overwrite project fields" do
    client = Object.new
    client.define_singleton_method(:complete_json) do |messages|
      raise "missing field context" unless messages.last["content"]["project_context"].key?("problem")

      {
        "model" => "fake-deepseek",
        "result" => {
          "answer" => "Delimite a questão a partir dos fatos.",
          "suggestions" => [ { "field_id" => "problem", "text" => "Qual solução jurídica se aplica aos fatos?" } ],
          "rewrite" => "",
          "checklist" => []
        },
        "usage" => { "prompt_tokens" => 12, "completion_tokens" => 15 }
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, client) do
        post "/projects/#{@project.id}/ai/action", params: { action: "suggest_problem" }, as: :json
      end
    end

    assert_response :success
    assert_equal "deepseek", response.parsed_body.dig("response", "provider")
    assert_equal "problem", response.parsed_body.dig("response", "suggestions", 0, "field_id")
    assert_equal "Qual é a questão jurídica?", @project.reload.fields["problem"]
    assert_equal 1, @account.reload.deepseek_used
    assert_equal 1, ProviderUsage.where(account: @account, provider: "deepseek").count
  end

  test "DeepSeek rejects suggestions outside the current action contract and refunds quota" do
    client = Object.new
    client.define_singleton_method(:complete_json) do |_messages|
      {
        "model" => "fake-deepseek",
        "result" => {
          "answer" => "Confira o perfil.",
          "suggestions" => [ { "field_id" => "email", "text" => "Altere o e-mail." } ],
          "rewrite" => "",
          "checklist" => []
        },
        "usage" => {}
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, client) do
        post "/projects/#{@project.id}/ai/action", params: { action: "suggest_problem" }, as: :json
      end
    end

    assert_response :bad_request
    assert_equal 0, @account.reload.deepseek_used
    assert_equal "refunded", AIUsageReservation.sole.status
  end

  test "JEV section analysis uses the separate TypeSafe service and fixed questions" do
    client = Object.new
    client.define_singleton_method(:score) do |state, questions|
      raise "missing project facts" unless state["legal_question"] == "Qual é a questão jurídica?"

      {
        "model" => "fake-jev",
        "answers" => questions.keys.index_with do
          { "score" => 2, "confidence" => 0.8, "probabilities" => [ 0.05, 0.15, 0.55, 0.25 ], "observation" => "Evidência parcial." }
        end,
        "usage" => { "input_tokens" => 21 }
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(JevClient, :new, client) do
        post "/projects/#{@project.id}/ai/jev-section", params: { section: "case_description" }, as: :json
      end
    end

    assert_response :success
    analysis = response.parsed_body.fetch("analysis")
    assert_equal "fake-jev", analysis["model"]
    assert_equal "facts-neutral", analysis.dig("criteria", 0, "id")
    assert_equal 4, analysis["criteria"].length
    assert_equal 1, ProviderUsage.where(account: @account, provider: "jev").count
  end

  test "AI consent is required before either provider can be called" do
    @account.update!(ai_consent: false)

    post "/projects/#{@project.id}/ai/action", params: { action: "suggest_problem" }, as: :json

    assert_response :forbidden
    assert_equal "ai_consent_required", response.parsed_body["error"]
    assert_equal 0, AIUsageReservation.count
  end

  private

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end
end
