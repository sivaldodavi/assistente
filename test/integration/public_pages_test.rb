require "test_helper"

class PublicPagesTest < ActionDispatch::IntegrationTest
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
end
