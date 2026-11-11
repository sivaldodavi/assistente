require "test_helper"

class PublicPagesTest < ActionDispatch::IntegrationTest
  test "root is a public informational landing page" do
    get root_path

    assert_response :success
    assert_select "h1", "Organize seu trabalho acadêmico, etapa por etapa."
    assert_select "a[href='#{plans_path}']", text: "Conheça os pacotes"
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

    get privacy_path
    assert_response :success
    assert_select "h1", "Como seus dados são tratados"

    get ai_help_path
    assert_response :success
    assert_select "h1", "Como a assistência de IA funciona"
    assert_select "body", text: /DeepSeek/
    assert_select "body", text: /TypeSafe/
  end

  test "production gate allows only the public informational pages while authentication is disabled" do
    previous_authentication_ready = Rails.configuration.x.authentication_ready
    Rails.configuration.x.authentication_ready = false

    with_stub(Rails, :env, ActiveSupport::EnvironmentInquirer.new("production")) do
      get root_path
      assert_response :success

      get pricing_path
      assert_response :success

      get login_path
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
