require "test_helper"

class PublicPagesTest < ActionDispatch::IntegrationTest
  test "root is a focused public landing page" do
    get root_path

    assert_response :success
    assert_select "h1", "Seu trabalho, com método."
    assert_select ".public-hero-actions a[href='#{plans_path}']", text: "Ver pacotes"
    assert_select "a[href='#{ai_help_path}']", text: "Como funciona a IA"
    assert_select "a[href='#{plans_path}']", text: "Pacotes"
    assert_select ".public-preview li", count: 3
    assert_select "link[rel='icon'][href='/icon.svg']"
    assert_select "meta[property='og:title'][content='Assistente Acadêmico']"
    assert_select "meta[property='og:image'][content*='social-preview.png']"
    assert_select "meta[property='og:image:type'][content='image/png']"
    assert_select "meta[property='og:image:width'][content='1200']"
    assert_select "meta[property='og:image:height'][content='630']"
    assert_select "meta[name='twitter:card'][content='summary_large_image']"
    assert File.exist?(Rails.root.join("public/icon.png"))
    assert File.exist?(Rails.root.join("public/apple-touch-icon.png"))
    assert File.exist?(Rails.root.join("public/social-preview.png"))
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

  test "metrics activity chart includes saved revisions from the full project history" do
    account = create_test_account(email: "metrics@example.test")
    sign_in_as(account)
    project = account.projects.create!(project_type: "case")
    old_revision = 9.months.ago.beginning_of_month + 1.day
    project.revisions.sole.update_column(:created_at, old_revision)

    get metrics_path

    assert_response :success
    assert_select ".activity-month", minimum: 10
    assert_select ".activity-month[data-count='1']", count: 1
    old_month_label = "#{PublicPagesController::MONTH_LABELS[old_revision.month - 1]}/#{old_revision.year}"
    assert_select ".activity-month[data-activity-month='#{old_month_label}'][data-count='1']", count: 1
    assert_includes response.body, "todo o histórico"
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
