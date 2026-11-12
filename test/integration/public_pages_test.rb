require "test_helper"

class PublicPagesTest < ActionDispatch::IntegrationTest
  test "root is a public informational landing page" do
    get root_path

    assert_response :success
    assert_select "h1", "Organize seu trabalho acadêmico, etapa por etapa."
    assert_select "a[href='#{plans_path}']", text: "Conheça os pacotes"
  end

  test "root offers Google login when production credentials are configured" do
    previous_client_id = Rails.application.config.x.google_oauth_client_id
    previous_client_secret = Rails.application.config.x.google_oauth_client_secret
    Rails.application.config.x.google_oauth_client_id = "client-id"
    Rails.application.config.x.google_oauth_client_secret = "client-secret"

    get root_path

    assert_response :success
    assert_select "a[href='#{login_path}']", text: "Entrar"
    assert_select "a[href='#{login_path}']", text: "Entrar com Google"
    assert_select "body", text: /O acesso a contas está em preparação/, count: 0
  ensure
    Rails.application.config.x.google_oauth_client_id = previous_client_id
    Rails.application.config.x.google_oauth_client_secret = previous_client_secret
  end

  test "public pricing page shows package details without purchase controls" do
    get pricing_path

    assert_response :success
    assert_select ".package-card", 3
    assert_select "[data-buy-package]", 0
    assert_select "a[href='#{login_path}']", text: "Entrar para comprar", count: 3
    assert_select "a[href='#{terms_path}']"
    assert_select "a[href='#{privacy_path}']"
  end

  test "public information pages explain privacy, consent, and AI providers" do
    get terms_path
    assert_response :success
    assert_select "h1", "Uso responsável do Assistente Acadêmico"
    assert_select "a[href='#{privacy_path}']"
    assert_includes response.body, "Mercado Pago"

    get privacy_path
    assert_response :success
    assert_select "h1", "Como seus dados são tratados"
    assert_select "a[href='mailto:contato@sivaldodavi.com']", text: "contato@sivaldodavi.com"
    assert_includes response.body, "provedor responsável pelo processamento do pagamento"
    assert_not_includes response.body, "Mercado Pago"

    get ai_help_path
    assert_response :success
    assert_select "h1", "Como a assistência de IA funciona"
    assert_select "body", text: /DeepSeek/
    assert_select "body", text: /TypeSafe/
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

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end
end
