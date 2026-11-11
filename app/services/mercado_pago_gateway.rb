require "mercadopago"
require "uri"

class MercadoPagoGateway
  class GatewayError < StandardError
    attr_reader :code

    def initialize(code, message)
      @code = code
      super(message)
    end
  end

  def initialize(access_token: PaymentSecrets.access_token, sdk: nil)
    @sdk = sdk || Mercadopago::SDK.new(
      access_token,
      request_options: request_options
    )
  end

  def create_pix(order:, account:)
    payload = {
      transaction_amount: order.amount_cents / 100.0,
      description: "Assistente Acadêmico — pacote #{PaymentPackages.find(order.package_code).fetch(:label)}",
      payment_method_id: "pix",
      external_reference: order.external_reference,
      payer: {
        email: account.email,
        first_name: account.name.split.first.presence || "Cliente",
        last_name: account.name.split.drop(1).join.presence || "Assistente Acadêmico"
      }
    }
    payload[:notification_url] = webhook_url if webhook_url.present?

    response = @sdk.payment.create(
      payload,
      request_options: request_options(order.idempotency_key)
    )
    response.raise_for_status!
    body = response[:response] || response["response"]
    raise GatewayError.new("invalid_provider_response", "O Mercado Pago retornou uma resposta inválida.") unless body.is_a?(Hash)

    pix = fetch(fetch(body, "point_of_interaction"), "transaction_data")
    payment_id = fetch(body, "id").to_s
    qr_base64 = fetch(pix, "qr_code_base64").to_s
    copy_code = fetch(pix, "qr_code").to_s
    valid_qr = qr_base64.bytesize <= 2.megabytes && qr_base64.match?(/\A[A-Za-z0-9+\/=]+\z/)
    unless payment_id.present? && (valid_qr || copy_code.present?)
      raise GatewayError.new("invalid_provider_response", "O Mercado Pago não retornou os dados do Pix.")
    end

    {
      payment_id:,
      qr_base64: valid_qr ? qr_base64 : nil,
      copy_code: copy_code.presence
    }
  rescue Mercadopago::MercadoPagoError, Faraday::Error
    raise GatewayError.new("provider_unavailable", "O Mercado Pago não concluiu a solicitação.")
  end

  def fetch_payment(payment_id)
    response = @sdk.payment.get(payment_id, request_options: request_options)
    response.raise_for_status!
    body = response[:response] || response["response"]
    raise GatewayError.new("invalid_provider_response", "O Mercado Pago retornou uma resposta inválida.") unless body.is_a?(Hash)

    body
  rescue Mercadopago::MercadoPagoError, Faraday::Error
    raise GatewayError.new("provider_unavailable", "Não foi possível confirmar o pagamento no Mercado Pago.")
  end

  def search_payments(external_reference:)
    response = @sdk.payment.search(
      filters: { external_reference:, limit: 100 },
      request_options: request_options
    )
    response.raise_for_status!
    body = response[:response] || response["response"]
    results = fetch(body, "results")
    unless results.is_a?(Array) && results.all? { |payment| payment.is_a?(Hash) }
      raise GatewayError.new("invalid_provider_response", "O Mercado Pago retornou uma lista de pagamentos inválida.")
    end

    results
  rescue Mercadopago::MercadoPagoError, Faraday::Error
    raise GatewayError.new("provider_unavailable", "Não foi possível pesquisar o pagamento no Mercado Pago.")
  end

  private

  def request_options(idempotency_key = nil)
    custom_headers = { "X-Idempotency-Key" => idempotency_key } if idempotency_key
    Mercadopago::RequestOptions.new(
      connection_timeout: 15.0,
      max_retries: 0,
      custom_headers:
    )
  end

  def webhook_url
    configured = ENV["MERCADOPAGO_WEBHOOK_URL"].presence ||
      Rails.application.credentials.dig(:mercadopago, :webhook_url).presence
    base_url = ENV["BASE_URL"].presence
    value = configured
    value ||= "#{base_url.delete_suffix("/")}/webhooks/mercadopago" if base_url.present?
    uri = URI.parse(value.to_s)
    unless uri.scheme == "https" && uri.host.present? && uri.userinfo.nil? &&
        uri.query.nil? && uri.fragment.nil? && uri.path.present?
      raise GatewayError.new("payment_not_configured", "Configure a URL HTTPS para o webhook do Mercado Pago.")
    end

    uri.to_s
  rescue URI::InvalidURIError
    raise GatewayError.new("payment_not_configured", "Configure uma URL HTTPS válida para o webhook do Mercado Pago.")
  end

  def fetch(hash, key)
    return unless hash.is_a?(Hash)

    hash[key] || hash[key.to_sym]
  end
end
