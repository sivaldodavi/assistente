require "test_helper"

class OmniauthCallbacksControllerTest < ActionController::TestCase
  tests OmniauthCallbacksController

  setup do
    @state = "google-state"
    @nonce = "google-nonce"
    @request.session[OmniAuth::Strategies::GoogleOauth2WithNonce::NONCE_SESSION_KEY] = {
      @state => @nonce
    }
    @request.env["omniauth.auth"] = google_auth
  end

  test "Google callback creates a verified account using the OmniAuth auth hash" do
    get :google_oauth2, params: { state: @state }

    account = Account.find_by!(google_sub: "google-1")
    assert_equal "ana@example.test", account.email
    assert_equal "Ana", account.name
    assert_redirected_to projects_path
  end

  test "Google callback rejects an unverified email" do
    @request.env["omniauth.auth"] = google_auth(email_verified: false)

    get :google_oauth2, params: { state: @state }

    assert_redirected_to login_path
    assert_nil Account.find_by(email: "ana@example.test")
  end

  test "Google login cannot replace an account's existing Google identity" do
    Account.create!(email: "ana@example.test", name: "Ana", google_sub: "different-sub")

    get :google_oauth2, params: { state: @state }

    assert_redirected_to login_path
    assert_equal "different-sub", Account.find_by!(email: "ana@example.test").google_sub
  end

  test "Google callback rejects a missing or mismatched OIDC nonce" do
    @request.env["omniauth.auth"] = google_auth(nonce: "different-nonce")

    get :google_oauth2, params: { state: @state }

    assert_redirected_to login_path
    assert_nil Account.find_by(email: "ana@example.test")
  end

  test "Google callback rejects an ID token without a nonce" do
    @request.env["omniauth.auth"] = google_auth(nonce: nil)

    get :google_oauth2, params: { state: @state }

    assert_redirected_to login_path
    assert_nil Account.find_by(email: "ana@example.test")
  end

  test "Google callback consumes the nonce so it cannot be replayed" do
    get :google_oauth2, params: { state: @state }
    assert_redirected_to projects_path

    get :google_oauth2, params: { state: @state }
    assert_redirected_to login_path
  end

  private

  def google_auth(email_verified: true, nonce: @nonce)
    OmniAuth::AuthHash.new(
      provider: "google_oauth2",
      uid: "google-1",
      info: { email: "ana@example.test", name: "Ana" },
      extra: { id_info: { email_verified:, nonce: } }
    )
  end
end
