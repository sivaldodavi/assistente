credentials = Rails.application.credentials
client_id = ENV["GOOGLE_CLIENT_ID"].presence || credentials.dig(:google, :client_id)
client_secret = ENV["GOOGLE_CLIENT_SECRET"].presence || credentials.dig(:google, :client_secret)
redirect_uri = ENV["GOOGLE_REDIRECT_URI"].presence || credentials.dig(:google, :redirect_uri)
production_redirect_uri = "https://trab.sivaldodavi.com.br/auth/google_oauth2/callback"

if Rails.env.production?
  if redirect_uri.present? && redirect_uri != production_redirect_uri
    raise "GOOGLE_REDIRECT_URI must be #{production_redirect_uri} in production"
  end
  redirect_uri ||= production_redirect_uri
end

require Rails.root.join("lib/omni_auth/strategies/google_oauth2_with_nonce")
require Rails.root.join("lib/production_access_gate")

Rails.application.config.x.google_oauth_client_id = client_id
Rails.application.config.x.google_oauth_client_secret = client_secret
Rails.application.config.x.google_oauth_redirect_uri = redirect_uri

OmniAuth.config.allowed_request_methods = [ :post ]
OmniAuth.config.silence_get_warning = true
OmniAuth.config.full_host = Rails.env.production? ? "https://trab.sivaldodavi.com.br" : "http://localhost:3000"

Rails.application.config.middleware.use OmniAuth::Builder do
  provider OmniAuth::Strategies::GoogleOauth2WithNonce,
    client_id,
    client_secret,
    scope: "openid,email,profile",
    prompt: "select_account",
    access_type: "online",
    redirect_uri:,
    pkce: true
end

Rails.application.config.middleware.insert_before OmniAuth::Builder, ProductionAccessGate
