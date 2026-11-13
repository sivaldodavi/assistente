require "test_helper"

class PublicPagesTest < ActionDispatch::IntegrationTest
  test "root is a focused public landing page" do
    get root_path

    assert_response :success
    assert_select "h1", "Seu trabalho, com método."
    assert_select "a[href='#{plans_path}']", text: "Pacotes"
    assert_select ".public-preview li", count: 3
  end

  test "root offers Google login when production credentials are configured" do
    previous_client_id = Rails.application.config.x.google_oauth_client_id
    previous_client_secret = Rails.application.config.x.google_oauth_client_secret
    Rails.application.config.x.google_oauth_client_id = "client-id"
    Rails.application.config.x.google_oauth_client_secret = "client-secret"

    get root_path

    assert_response :success
    assert_select "form[action='/auth/google_oauth2'][method='post'] button.header-link", count: 0
    assert_select "form[action='/auth/google_oauth2'][method='post'] button.button-primary", text: "Entrar com Google"
    assert_select "a[href='#{login_path}']", count: 0
    assert_select "body", text: /O acesso a contas está em preparação/, count: 0
  ensure
    Rails.application.config.x.google_oauth_client_id = previous_client_id
    Rails.application.config.x.google_oauth_client_secret = previous_client_secret
  end

  test "public pricing page shows package details without purchase controls" do
    get pricing_path

    assert_response :success
    assert_select ".package-card", 4
    assert_select "[data-buy-package]", 0
    assert_select "a[href='#{login_path}']", text: "Entrar para comprar", count: 4
    assert_select "a[href='#{terms_path}']"
    assert_select "a[href='#{privacy_path}']"
    assert_no_provider_names
  end

  test "public sign-in actions start Google OAuth directly when configured" do
    previous_client_id = Rails.application.config.x.google_oauth_client_id
    previous_client_secret = Rails.application.config.x.google_oauth_client_secret
    Rails.application.config.x.google_oauth_client_id = "client-id"
    Rails.application.config.x.google_oauth_client_secret = "client-secret"

    get pricing_path
    assert_response :success
    assert_select "form[action='/auth/google_oauth2'][method='post'] button", text: "Entrar para comprar", count: 4
    assert_select "a[href='#{login_path}']", count: 0

    get projects_path
    assert_redirected_to root_path
    follow_redirect!
    assert_response :success
    assert_select "form[action='/auth/google_oauth2'][method='post'] button", text: "Entrar com Google", count: 1
    assert_select "a[href='#{login_path}']", count: 0

    [ terms_path, privacy_path ].each do |path|
      get path
      assert_response :success
      assert_select "form[action='/auth/google_oauth2'][method='post'] button.header-link", text: "Entrar"
      assert_select "a[href='#{login_path}']", count: 0
    end
  ensure
    Rails.application.config.x.google_oauth_client_id = previous_client_id
    Rails.application.config.x.google_oauth_client_secret = previous_client_secret
  end

  test "public information pages explain privacy, consent, and AI providers" do
    get terms_path
    assert_response :success
    assert_select "h1", "Uso responsável do Assistente Acadêmico"
    assert_select "a[href='#{privacy_path}']"
    assert_includes response.body, "Mercado Pago"
    assert_no_provider_names

    get privacy_path
    assert_response :success
    assert_select "h1", "Como seus dados são tratados"
    assert_select "a[href='mailto:contato@sivaldodavi.com']", text: "contato@sivaldodavi.com"
    assert_includes response.body, "provedor responsável pelo processamento do pagamento"
    assert_not_includes response.body, "Mercado Pago"
    assert_no_provider_names

    get ai_help_path
    assert_response :success
    assert_select "h1", "Como usar o Assistente Acadêmico"
    assert_select "h2", "Primeiros passos"
    assert_select "h2", "Roteiros e documentos"
    assert_select "h2", "Ajuda com IA"
    assert_select "body", text: /Cada pedido de orientação usa um crédito de IA/
    assert_not_includes response.body, "não consomem créditos"
    assert_not_includes response.body, "excesso de solicitações"
    assert_no_provider_names
  end

  test "production gate allows only the public informational pages while authentication is disabled" do
    previous_authentication_ready = Rails.configuration.x.authentication_ready
    previous_google_oauth_test_ready = Rails.configuration.x.google_oauth_test_ready
    Rails.configuration.x.authentication_ready = false
    Rails.configuration.x.google_oauth_test_ready = false

    with_stub(Rails, :env, ActiveSupport::EnvironmentInquirer.new("production")) do
      get root_path
      assert_response :success

      get pricing_path
      assert_response :success

      get login_path
      assert_response :service_unavailable

      get "/auth/google_oauth2/callback"
      assert_response :service_unavailable

      get projects_path
      assert_response :service_unavailable

      get admin_path
      assert_response :service_unavailable

      post payments_path
      assert_response :service_unavailable
    end
  ensure
    Rails.configuration.x.authentication_ready = previous_authentication_ready
    Rails.configuration.x.google_oauth_test_ready = previous_google_oauth_test_ready
  end

  test "production gate allows Google OAuth test endpoints without opening private routes" do
    previous_authentication_ready = Rails.configuration.x.authentication_ready
    previous_google_oauth_test_ready = Rails.configuration.x.google_oauth_test_ready
    Rails.configuration.x.authentication_ready = false
    Rails.configuration.x.google_oauth_test_ready = true

    with_stub(Rails, :env, ActiveSupport::EnvironmentInquirer.new("production")) do
      get login_path
      assert_response :success

      post "/auth/google_oauth2"
      assert_response :redirect

      get projects_path
      assert_response :service_unavailable

      post payments_path
      assert_response :service_unavailable
    end
  ensure
    Rails.configuration.x.authentication_ready = previous_authentication_ready
    Rails.configuration.x.google_oauth_test_ready = previous_google_oauth_test_ready
  end

  private

  def assert_no_provider_names
    assert_not_includes response.body, "JEV"
    assert_not_includes response.body, "DeepSeek"
    assert_not_includes response.body, "TypeSafe"
  end

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end
end
