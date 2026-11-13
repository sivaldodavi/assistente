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

  test "AI fallback to Gemini charges one credit and records the successful provider" do
    deepseek = Object.new
    deepseek.define_singleton_method(:complete_json) do |_messages|
      raise AIProviderError.new("provider_busy", "temporarily unavailable", 503)
    end
    gemini = Object.new
    gemini.define_singleton_method(:complete_json) do |_messages|
      {
        "model" => "fake-gemini",
        "result" => {
          "answer" => "Sugestão de análise.",
          "suggestions" => [],
          "rewrite" => "",
          "checklist" => []
        },
        "usage" => { "prompt_tokens" => 10, "completion_tokens" => 12 }
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, deepseek) do
        with_stub(GeminiClient, :new, gemini) do
          post "/projects/#{@project.id}/ai/action", params: { action: "suggest_problem" }, as: :json
        end
      end
    end

    assert_response :success
    assert_equal "gemini", response.parsed_body.dig("response", "provider")
    assert_equal 1, @account.reload.deepseek_used
    assert_equal 1, AIUsageReservation.count
    assert_equal "gemini", ProviderUsage.sole.provider
  end

  test "JEV section analysis uses the separate TypeSafe service and fixed questions" do
    @account.update!(ai_limit: 0, ai_used: 0)
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
    assert_equal 0, @account.reload.ai_used
    assert_equal 0, @account.deepseek_used
    assert_equal 0, AIUsageReservation.count
    assert_equal "case_section:case_description", JevAssessment.sole.stage
    assert_equal @project.revisions.sole, JevAssessment.sole.project_revision
  end

  test "formative assessments remain free of credit limits but retain a request rate limit" do
    @account.update!(ai_limit: 0, ai_used: 0)
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(JevClient, :new, fake_jev_client) do
        30.times do
          post "/projects/#{@project.id}/ai/jev-section", params: { section: "case_description" }, as: :json
          assert_response :success
        end
        post "/projects/#{@project.id}/ai/jev-section", params: { section: "case_description" }, as: :json
      end
    end

    assert_response :too_many_requests
    assert_equal 0, @account.reload.ai_used
    assert_equal 0, @account.deepseek_used
    assert_equal 0, AIUsageReservation.count
  ensure
    Rails.cache = original_cache
  end

  test "Paper Project assessment persists a revision-bound /3 subtotal and flags the declared /4 discrepancy" do
    project = @account.projects.create!(project_type: "paper_project")
    client = fake_jev_client

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(JevClient, :new, client) do
        post "/projects/#{project.id}/ai/jev-assessment",
          params: { stage: "paper_project", project_revision: project.lock_version },
          as: :json
      end
    end

    assert_response :success
    analysis = response.parsed_body.fetch("analysis")
    assert_equal "paper_project", analysis["stage"]
    assert_equal 3.0, analysis["assessable_points"]
    assert_equal 2.0, analysis["expected_points"]
    assert_equal 4.0, analysis["declared_points"]
    assert_equal true, analysis["points_discrepancy"]
    assert_nil analysis["grade_range"]
    assessment = JevAssessment.sole
    assert_equal project, assessment.project
    assert_equal project.revisions.sole, assessment.project_revision
    assert_equal analysis, assessment.result
  end

  test "Case report assessment calculates its /3.5 text-only subtotal without scoring debate or formatting" do
    client = fake_jev_client

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(JevClient, :new, client) do
        post "/projects/#{@project.id}/ai/jev-assessment",
          params: { stage: "case_report", project_revision: @project.lock_version },
          as: :json
      end
    end

    assert_response :success
    analysis = response.parsed_body.fetch("analysis")
    assert_equal 3.5, analysis["assessable_points"]
    assert_equal 2.33, analysis["expected_points"]
    assert_equal 0.5, analysis["unassessed_points"]
    assert_equal 2, analysis.dig("grade_range", "score")
    assert_equal "case_report", JevAssessment.sole.stage
  end

  test "Case dissertation assessment excludes the group debate and persists its own rubric" do
    client = fake_jev_client

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(JevClient, :new, client) do
        post "/projects/#{@project.id}/ai/jev-assessment",
          params: { stage: "case_dissertation", project_revision: @project.lock_version },
          as: :json
      end
    end

    assert_response :success
    analysis = response.parsed_body.fetch("analysis")
    assert_equal "case_dissertation", analysis["stage"]
    assert_equal 2.0, analysis["assessable_points"]
    assert_nil analysis["grade_range"]
    assert_equal %w[formal_standards legal_foundation structure_and_language],
      analysis["criteria"].map { |criterion| criterion["id"] }.sort
    assert_equal "case_dissertation", JevAssessment.sole.stage
  end

  test "AI consent is required before either provider can be called" do
    @account.update!(ai_consent: false)

    post "/projects/#{@project.id}/ai/action", params: { action: "suggest_problem" }, as: :json

    assert_response :forbidden
    assert_equal "ai_consent_required", response.parsed_body["error"]
    assert_equal 0, AIUsageReservation.count
  end

  private

  def fake_jev_client
    client = Object.new
    client.define_singleton_method(:score) do |_state, questions|
      {
        "model" => "fake-jev",
        "answers" => questions.keys.index_with do
          { "score" => 2, "confidence" => 0.8, "probabilities" => [ 0.05, 0.15, 0.55, 0.25 ], "observation" => "Evidência parcial." }
        end,
        "usage" => { "input_tokens" => 21 }
      }
    end
    client
  end

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end
end
