require "test_helper"
require "rack/mock"

class GoogleOauth2StrategyTest < ActiveSupport::TestCase
  test "authorization request includes state nonce and S256 PKCE challenge" do
    session = {}
    strategy = OmniAuth::Strategies::GoogleOauth2WithNonce.new(
      ->(_env) { [ 404, {}, [] ] },
      "client-id",
      "client-secret",
      name: "google_oauth2",
      scope: "openid,email,profile",
      redirect_uri: "https://trab.sivaldodavi.com.br/auth/google_oauth2/callback"
    )
    env = Rack::MockRequest.env_for(
      "http://localhost:3000/auth/google_oauth2",
      method: "POST"
    )
    env["rack.session"] = session

    response = strategy.call(env)
    authorization_uri = URI(response[1].fetch("Location"))
    params = Rack::Utils.parse_query(authorization_uri.query)

    assert_equal "S256", params.fetch("code_challenge_method")
    assert_match(/\A[A-Za-z0-9_-]{43}\z/, params.fetch("code_challenge"))
    assert_match(/\A[0-9a-f]{48}\z/, params.fetch("state"))
    assert_match(/\A[0-9a-f]{64}\z/, params.fetch("nonce"))
    assert_equal params.fetch("nonce"), session.dig(
      OmniAuth::Strategies::GoogleOauth2WithNonce::NONCE_SESSION_KEY,
      params.fetch("state")
    )
  end
end
