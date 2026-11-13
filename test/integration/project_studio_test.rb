require "test_helper"

class ProjectStudioTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "studio@example.test")
    @account.update!(terms_accepted: true, ai_consent: true)
    sign_in_as(@account)
  end

  test "studio page explains editable proposals and offers guided and import modes" do
    get project_assistant_path

    assert_response :success
    assert_select "[data-project-studio]"
    assert_select "[data-studio-mode] option[value='guided']"
    assert_select "[data-studio-mode] option[value='import']"
    assert_select "[data-studio-prompt-suggestion]", minimum: 3
    assert_select "[data-guided-only]:not([hidden])", count: 2
    assert_select "[data-studio-source-field][hidden]"
    assert_select "[data-studio-source][maxlength='24000']"
    assert_select "a[href='https://www.instagram.com/sivaldo.davi/']", text: "Suporte"
  end

  test "guided proposal validates field IDs and returns editable provenance labels" do
    client = Object.new
    client.define_singleton_method(:complete_json) do |messages|
      context = messages.last.fetch("content")
      raise "missing user prompt" unless context["initial_request"].include?("meio ambiente")

      {
        "model" => "fake-deepseek",
        "result" => {
          "answer" => "Vamos delimitar a questão.",
          "questions" => [ { "id" => "scope", "prompt" => "Qual período será analisado?" } ],
          "suggestions" => [
            { "field_id" => "problem", "text" => "Como a norma incide no tema informado?", "origin" => "from_user_input" }
          ]
        },
        "usage" => { "prompt_tokens" => 40, "completion_tokens" => 30 }
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, client) do
        post project_assistant_draft_path, params: {
          project_type: "case",
          mode: "guided",
          prompt: "Quero escrever sobre meio ambiente.",
          source_text: "",
          messages: []
        }, as: :json
      end
    end

    assert_response :success
    suggestion = response.parsed_body.dig("response", "suggestions", 0)
    assert_equal "problem", suggestion["field_id"]
    assert_equal "Pergunta-problema", suggestion["label"]
    assert_equal "from_user_input", suggestion["origin"]
    assert_equal 1, @account.reload.deepseek_used
    assert_equal 1, ProviderUsage.where(account: @account, operation: "studio:guided").count
  end

  test "selected and edited studio fields are stored only when the project is created" do
    post projects_path, params: {
      project: {
        project_type: "case",
        fields: {
          "title" => "Rascunho revisado",
          "problem" => "Problema editado pela pessoa",
          "not_a_workflow_field" => "Ignorar"
        }
      }
    }

    assert_response :redirect
    project = @account.projects.sole
    assert_equal "Rascunho revisado", project.fields["title"]
    assert_equal "Problema editado pela pessoa", project.fields["problem"]
    refute project.fields.key?("not_a_workflow_field")
  end

  test "text import sends the supplied text to the provider and rejects invented field IDs" do
    client = Object.new
    client.define_singleton_method(:complete_json) do |messages|
      raise "missing imported text" unless messages.last.dig("content", "text_to_organize").include?("texto antigo")

      {
        "model" => "fake-deepseek",
        "result" => {
          "answer" => "O texto precisa ser revisado.",
          "questions" => [],
          "suggestions" => [
            { "field_id" => "institution", "text" => "Instituição inventada", "origin" => "ai_suggestion" }
          ]
        },
        "usage" => {}
      }
    end

    with_stub(AIProviderSecrets, :load, "fake-secret") do
      with_stub(DeepSeekClient, :new, client) do
        post project_assistant_draft_path, params: {
          project_type: "case",
          mode: "import",
          prompt: "Organize este rascunho.",
          source_text: "Este é um texto antigo.",
          messages: []
        }, as: :json
      end
    end

    assert_response :bad_request
    assert_equal 0, @account.reload.deepseek_used
    assert_equal "refunded", AIUsageReservation.sole.status
  end

  test "studio draft rejects missing project credits before consuming AI credits" do
    @account.update!(project_limit: 0)

    post project_assistant_draft_path, params: {
      project_type: "case",
      mode: "guided",
      prompt: "Começar um Case",
      messages: []
    }, as: :json

    assert_response :payment_required
    assert_equal "project_credit_required", response.parsed_body["error"]
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
