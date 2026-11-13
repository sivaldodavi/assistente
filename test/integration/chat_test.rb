require "test_helper"

class ChatTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "chat@example.test")
    @account.update!(terms_accepted: true, ai_consent: true, deepseek_limit: 20)
    sign_in_as(@account)
  end

  test "chat requires sign in" do
    delete logout_path

    get chat_path

    assert_redirected_to login_path
  end

  test "chat is a focused single-column workspace and offers an optional refinement step" do
    get chat_path(mode: "guided")

    assert_response :success
    assert_select ".chat-layout aside", count: 0
    assert_select ".chat-workspace", count: 1
    assert_select "button[type='submit']", text: "Gerar sugestões"
    assert_select "[data-studio-refinement] summary", text: "Refinar proposta com respostas"
    assert_not_includes response.body, "Continuar com minhas respostas"
  end

  test "chat remembers the selected project and stage but does not save the transcript" do
    project = @account.projects.create!(project_type: "case", title: "Case de contexto")

    get chat_path(project_id: project.id, scope: "description")

    assert_response :success
    assert_select "select#chat-project option[selected][value='#{project.id}']"
    assert_select "select#chat-scope option[selected][value='description']"

    client = fake_chat_client("Resposta temporária.")
    with_stub(AIProviderRouter, :new, client) do
      post chat_ask_path, params: {
        project_id: project.id,
        scope: "description",
        message: "O que devo revisar?",
        messages: []
      }, as: :json
    end

    assert_response :success
    assert_equal "Resposta temporária.", response.parsed_body["answer"]

    get chat_path

    assert_response :success
    assert_select "select#chat-project option[selected][value='#{project.id}']"
    assert_select "select#chat-scope option[selected][value='description']"
    assert_not_includes response.body, "Resposta temporária."
  end

  test "chat sends only the selected stage fields to the AI provider" do
    project = @account.projects.create!(
      project_type: "case",
      fields: {
        "facts" => "Fatos relevantes do caso.",
        "problem" => "Qual é a questão jurídica?",
        "dissertation" => "Conteúdo de outra etapa."
      }
    )
    client = Object.new
    client.define_singleton_method(:complete_json) do |messages|
      context = messages.last.dig("content", "contexto_do_projeto")
      raise "stage fields missing" unless context.dig("campos", "facts") == "Fatos relevantes do caso."
      raise "unselected field leaked" if context.fetch("campos").values.any? { |value| value.include?("outra etapa") }

      { "provider" => "deepseek", "model" => "fake-chat", "result" => { "answer" => "Revise a relação entre fatos e problema." }, "usage" => {} }
    end

    with_stub(AIProviderRouter, :new, client) do
      post chat_ask_path, params: {
        project_id: project.id,
        scope: "description",
        message: "O que revisar?",
        messages: [ { role: "user", content: "Pergunta anterior" }, { role: "assistant", content: "Resposta anterior" } ]
      }, as: :json
    end

    assert_response :success
    assert_equal 1, @account.reload.deepseek_used
    assert_equal "chat", AIUsageReservation.sole.action
    assert_equal project, AIUsageReservation.sole.project
  end

  test "chat rejects another account's project and invalid stages" do
    other_account = create_test_account(email: "other-chat@example.test")
    other_project = other_account.projects.create!(project_type: "case")

    post chat_ask_path, params: { project_id: other_project.id, scope: "description", message: "Pergunta" }, as: :json

    assert_response :not_found
    assert_equal 0, @account.reload.deepseek_used

    project = @account.projects.create!(project_type: "case")
    post chat_ask_path, params: { project_id: project.id, scope: "not-a-stage", message: "Pergunta" }, as: :json

    assert_response :bad_request
    assert_equal 0, @account.reload.deepseek_used
  end

  test "chat requires consent and available AI credits" do
    @account.update!(ai_consent: false)
    post chat_ask_path, params: { message: "Como organizar a introdução?" }, as: :json
    assert_response :forbidden

    @account.update!(ai_consent: true, deepseek_limit: 0)
    post chat_ask_path, params: { message: "Como organizar a introdução?" }, as: :json
    assert_response :too_many_requests
    assert_equal 0, @account.reload.deepseek_used
  end

  private

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end

  def fake_chat_client(answer)
    client = Object.new
    client.define_singleton_method(:complete_json) do |_messages|
      { "provider" => "deepseek", "model" => "fake-chat", "result" => { "answer" => answer }, "usage" => {} }
    end
    client
  end
end
