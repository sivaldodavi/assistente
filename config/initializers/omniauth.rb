credentials = Rails.application.credentials
client_id = ENV["GOOGLE_CLIENT_ID"].presence || credentials.dig(:google, :client_id)
client_secret = ENV["GOOGLE_CLIENT_SECRET"].presence || credentials.dig(:google, :client_secret)
redirect_uri = ENV["GOOGLE_REDIRECT_URI"].presence || credentials.dig(:google, :redirect_uri)

Rails.application.config.x.google_oauth_client_id = client_id
Rails.application.config.x.google_oauth_client_secret = client_secret
Rails.application.config.x.google_oauth_redirect_uri = redirect_uri

OmniAuth.config.allowed_request_methods = [ :post ]
OmniAuth.config.silence_get_warning = true

Rails.application.config.middleware.use OmniAuth::Builder do
  provider :google_oauth2,
    client_id,
    client_secret,
    scope: "openid,email,profile",
    prompt: "select_account",
    access_type: "online",
    redirect_uri:
end
