require "test_helper"

class AuthenticationTest < ActionDispatch::IntegrationTest
  setup do
    Rails.application.config.x.google_oauth_client_id = "client-id"
    Rails.application.config.x.google_oauth_client_secret = "client-secret"
    OmniAuth.config.test_mode = true
  end

  teardown do
    Rails.application.config.x.google_oauth_client_id = nil
    Rails.application.config.x.google_oauth_client_secret = nil
    OmniAuth.config.test_mode = false
    OmniAuth.config.mock_auth.clear
  end

  test "login page starts Google OAuth with a CSRF-protected POST" do
    previous_forgery_protection = ActionController::Base.allow_forgery_protection
    ActionController::Base.allow_forgery_protection = true
    get login_path

    assert_response :success
    assert_select "form[action='/auth/google_oauth2'][method='post']"
    token = Nokogiri::HTML(response.body).at_css("input[name='authenticity_token']")&.[]("value")
    assert token.present?

    post "/auth/google_oauth2", params: { authenticity_token: token }
    assert_response :redirect
    assert_match %r{/auth/google_oauth2/callback}, response.headers["Location"]
  ensure
    ActionController::Base.allow_forgery_protection = previous_forgery_protection
  end

  test "development login creates an account and logout clears its session" do
    post dev_login_path, params: { email: "local@example.test", name: "Local" }
    assert_redirected_to projects_path
    assert_response :redirect
    assert Account.exists?(email: "local@example.test")

    delete logout_path
    assert_response :see_other
    get new_project_path
    assert_redirected_to login_path
  end

  test "a project is not visible to a different account" do
    owner = create_test_account(email: "owner-auth@example.test")
    sign_in_as(owner)
    post projects_path, params: { project: { project_type: "case" } }
    project = owner.projects.sole

    other = create_test_account(email: "other-auth@example.test")
    sign_in_as(other)
    get project_path(project)

    assert_response :not_found
    assert_equal 0, other.projects.count
  end

  private
end
