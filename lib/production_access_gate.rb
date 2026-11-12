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

    method == "POST" && path == PRODUCTION_WEBHOOK_PATH
  end

  def unavailable
    [
      503,
      { "content-type" => "text/plain; charset=utf-8", "cache-control" => "no-store" },
      [ "Service Unavailable" ]
    ]
  end
end
