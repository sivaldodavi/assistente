class PaymentsController < ApplicationController
  wrap_parameters false
  before_action :authenticate_payment_account!, only: %i[create status]

  def plans
    @packages = PaymentPackages::PUBLIC_DEFINITIONS
  end

  def create
    body = request.request_parameters.except("controller", "action", "format").deep_stringify_keys
    unless body.keys.sort == %w[package_code quantity request_id]
      return render json: { error: "invalid_payload", message: "Envie somente pacote, quantidade e identificador da solicitação." }, status: :bad_request
    end
    unless PaymentPackages::PUBLIC_DEFINITIONS.key?(body["package_code"])
      return render json: { error: "invalid_package", message: "Este pacote não está disponível." }, status: :unprocessable_entity
    end

    @order = PaymentService.new.create_order!(
      account: current_account,
      package_code: body["package_code"],
      quantity: body["quantity"],
      request_id: body["request_id"]
    )
    render json: {
      ok: true,
      order_id: @order.external_reference,
      status: @order.public_status,
      package_code: @order.package_code,
      quantity: @order.quantity,
      amount_cents: @order.amount_cents,
      qr_code_base64: @order.pix_qr_base64,
      pix_copy_code: @order.pix_copy_code
    }
  rescue PaymentService::RequestError => error
    render json: { error: error.code, message: error.message }, status: error.status
  rescue MercadoPagoGateway::GatewayError => error
    render json: { error: error.code, message: error.message }, status: :service_unavailable
  rescue PaymentSecrets::ConfigurationError
    render json: { error: "payment_not_configured", message: "Os pagamentos ainda não estão configurados." }, status: :service_unavailable
  rescue ActiveRecord::RecordInvalid
    render json: { error: "invalid_payment_order", message: "Não foi possível registrar esta compra." }, status: :unprocessable_entity
  end

  def status
    order = current_account.payment_orders.find_by!(external_reference: params[:id])
    render json: { order_id: order.external_reference, status: order.public_status }
  end

  private

  def authenticate_payment_account!
    return if current_account

    render json: { error: "unauthenticated", message: "Entre na sua conta para continuar." }, status: :unauthorized
  end
end
