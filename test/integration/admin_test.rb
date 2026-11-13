require "test_helper"

class AdminTest < ActionDispatch::IntegrationTest
  setup do
    @previous_admin_emails = Rails.application.config.x.admin_emails
    Rails.application.config.x.admin_emails = [ "admin@example.test" ]
    @admin = create_test_account(email: "admin@example.test")
    @target = create_test_account(email: "student@example.test")
    sign_in_as(@admin)
  end

  teardown do
    Rails.application.config.x.admin_emails = @previous_admin_emails
  end

  test "admin can manage plans, credit balances, and account blocks with an audit trail" do
    @target.update!(project_limit: 6, project_used: 1, ai_limit: 12, ai_used: 2, deepseek_limit: 8, deepseek_used: 3)

    get admin_accounts_path
    assert_response :success
    assert_select ".admin-account-card", minimum: 2
    assert_select ".admin-account-card", text: /5 disponíveis/

    patch admin_account_plan_path(@target), params: { plan_code: "com_ia" }
    assert_redirected_to admin_accounts_path
    @target.reload
    assert_equal "com_ia", @target.plan_code
    assert_equal 6, @target.project_limit
    assert_equal 12, @target.ai_limit

    patch admin_account_credits_path(@target), params: {
      credits: { projects: "3", ai: "10" }
    }
    assert_redirected_to admin_accounts_path
    @target.reload
    assert_equal 4, @target.project_limit
    assert_equal 12, @target.ai_limit
    assert_equal 13, @target.deepseek_limit

    patch admin_account_block_path(@target), params: { blocked: "1" }
    assert_redirected_to admin_accounts_path
    assert @target.reload.is_blocked?
    patch admin_account_block_path(@target), params: { blocked: "0" }
    assert_not @target.reload.is_blocked?
    assert_equal %w[plan credits block unblock], AdminAuditEvent.order(:id).pluck(:action)
  end

  test "admin account listing exposes metadata but not private project content" do
    @target.projects.create!(
      project_type: "case",
      title: "Projeto privado",
      fields: { "facts" => "conteúdo privado que não deve aparecer" }
    )

    get admin_accounts_path

    assert_response :success
    assert_includes response.body, "student@example.test"
    assert_not_includes response.body, "Projeto privado"
    assert_not_includes response.body, "conteúdo privado que não deve aparecer"
  end

  test "non-admins cannot access management actions" do
    sign_in_as(@target)

    get admin_accounts_path
    assert_response :forbidden
    patch admin_account_block_path(@admin), params: { blocked: "1" }
    assert_response :forbidden
    assert_not @admin.reload.is_blocked?
  end

  test "admins cannot block themselves or another administrator" do
    patch admin_account_block_path(@admin), params: { blocked: "1" }
    assert_redirected_to admin_accounts_path
    assert_not @admin.reload.is_blocked?
    assert_empty AdminAuditEvent.where(action: "block")
  end

  test "credit changes reject invalid and excessive balances" do
    patch admin_account_credits_path(@target), params: {
      credits: { projects: "-1", ai: "0" }
    }
    assert_redirected_to admin_accounts_path
    assert_equal 100, @target.reload.project_limit

    patch admin_account_credits_path(@target), params: {
      credits: { projects: "1001", ai: "0" }
    }
    assert_redirected_to admin_accounts_path
    assert_equal 100, @target.reload.project_limit
  end
end
