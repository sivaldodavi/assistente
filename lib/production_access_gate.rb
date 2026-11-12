class ProductionAccessGate
  PUBLIC_GET_PATHS = %w[
    /
    /planos
    /plans
    /termos
    /privacidade
    /ajuda-ia
    /up
    /icon.png
    /icon.svg
    /favicon.ico
    /robots.txt
  ].freeze
  PRODUCTION_WEBHOOK_PATH = "/webhooks/mercadopago"
  GOOGLE_OAUTH_TEST_GET_PATHS = %w[
    /login
    /auth/google_oauth2/callback
    /auth/failure
  ].freeze
  GOOGLE_OAUTH_TEST_POST_PATH = "/auth/google_oauth2"

  def initialize(app)
    @app = app
  end

  def call(env)
    return @app.call(env) unless Rails.env.production? && !Rails.configuration.x.authentication_ready
    return unavailable unless allowed_request?(env)

    @app.call(env)
  end

  private

  def allowed_request?(env)
    method = env["REQUEST_METHOD"]
    path = env["PATH_INFO"]
    return true if %w[GET HEAD].include?(method) && PUBLIC_GET_PATHS.include?(path)
    return true if %w[GET HEAD].include?(method) && path.start_with?("/assets/")
    return true if google_oauth_test_request?(method, path)

    method == "POST" && path == PRODUCTION_WEBHOOK_PATH
  end

  def google_oauth_test_request?(method, path)
    return false unless Rails.configuration.x.google_oauth_test_ready

    (%w[GET HEAD].include?(method) && GOOGLE_OAUTH_TEST_GET_PATHS.include?(path)) ||
      (method == "POST" && path == GOOGLE_OAUTH_TEST_POST_PATH)
  end

  def unavailable
    [
      503,
      { "content-type" => "text/plain; charset=utf-8", "cache-control" => "no-store" },
      [ "Service Unavailable" ]
    ]
  end
end
