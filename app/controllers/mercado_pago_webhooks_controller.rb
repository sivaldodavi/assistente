require "mercadopago"
require "mercadopago/webhook/validator"

class MercadoPagoWebhooksController < ActionController::Base
  wrap_parameters false
  skip_forgery_protection

  def create
    event = request.request_parameters.deep_stringify_keys
    return head :ok unless event["type"] == "payment"

    payment_id = request.query_parameters["data.id"].to_s
    return head :unauthorized if payment_id.blank?
    body_payment_id = event.dig("data", "id").to_s
    return head :unauthorized if body_payment_id.present? && body_payment_id != payment_id

    Mercadopago::Webhook::Validator.validate(
      request.headers["x-signature"],
      request.headers["x-request-id"],
      payment_id,
      PaymentSecrets.webhook_secret,
      tolerance_seconds: 300
    )

    payment = MercadoPagoGateway.new.fetch_payment(payment_id)
    result = PaymentService.new.process_verified_payment(payment)
    record_event(payment_id, event, result)
    head :ok
  rescue PaymentSecrets::ConfigurationError
    head :service_unavailable
  rescue Mercadopago::Webhook::InvalidWebhookSignatureError => error
    Rails.logger.warn("Webhook Mercado Pago rejeitado: #{error.reason}")
    head :unauthorized
  rescue MercadoPagoGateway::GatewayError
    head :service_unavailable
  end

  private

  def record_event(payment_id, event, result)
    key = [ "payment", payment_id, event.dig("data", "status").presence || "notification" ].join(":")
    record = PaymentWebhookEvent.create_or_find_by!(event_key: key) do |entry|
      entry.event_type = event["action"].presence || "payment"
      entry.payment_id = payment_id
      entry.received_at = Time.current
    end
    record.update!(result: result.to_s, processed_at: Time.current, error_code: result.to_s == "approved" ? nil : result.to_s)
  end
end
