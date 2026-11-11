module AccountIntegrationTestHelper
  def create_test_account(email: "test-#{SecureRandom.hex(8)}@example.test", name: "Conta de teste")
    Account.create!(email:, name:, project_limit: 100, ai_limit: 100, deepseek_limit: 100)
  end

  def sign_in_as(account)
    post dev_login_path, params: { email: account.email, name: account.name }
    assert_response :redirect
  end
end
