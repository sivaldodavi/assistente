require "bigdecimal"

class PaymentService
  class RequestError < StandardError
    attr_reader :code, :status

    def initialize(code, message, status = :bad_request)
      @code = code
      @status = status
      super(message)
    end
  end

  REQUEST_ID_FORMAT = /\A[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/i
  TERMINAL_FAILURES = %w[rejected cancelled expired refunded charged_back].freeze

  def initialize(gateway: nil)
    @gateway = gateway
  end

  def create_order!(account:, request_id:, package_code:, quantity:)
    definition = PaymentPackages.find(package_code)
    raise RequestError.new("invalid_package", "Pacote inválido.") unless definition
    unless quantity.is_a?(Integer) && quantity.between?(1, PaymentPackages::MAX_QUANTITY)
      raise RequestError.new("invalid_quantity", "A quantidade deve ser um inteiro entre 1 e #{PaymentPackages::MAX_QUANTITY}.")
    end
    unless request_id.is_a?(String) && request_id.match?(REQUEST_ID_FORMAT)
      raise RequestError.new("invalid_request_id", "Identificador da solicitação inválido.")
    end

    order = account.with_lock do
      current = account.payment_orders.find_or_initialize_by(request_id:)
      if current.persisted?
        unless current.package_code == package_code && current.quantity == quantity
          raise RequestError.new("idempotency_conflict", "Este identificador já foi usado em outra compra.", :conflict)
        end
      else
        current.assign_attributes(
          package_code:,
          quantity:,
          project_credits: definition.fetch(:project_credits) * quantity,
          ai_credits: definition.fetch(:ai_credits) * quantity,
          deepseek_credits: definition.fetch(:deepseek_credits) * quantity,
          amount_cents: definition.fetch(:price_cents) * quantity
        )
        current.save!
      end
      current
    end

    return order if %w[provider_created approved].include?(order.status)
    raise RequestError.new("order_not_retryable", "Este pedido não pode ser tentado novamente.", :conflict) if %w[failed mismatch].include?(order.status)

    begin
      provider_result = gateway.create_pix(order:, account:)
    rescue MercadoPagoGateway::GatewayError
      order.with_lock do
        order.update!(status: "reconciliation_required") unless order.status == "approved"
      end
      raise
    end

    order.with_lock do
      order.update!(
        provider_payment_id: provider_result.fetch(:payment_id),
        pix_copy_code: provider_result[:copy_code],
        pix_qr_base64: provider_result[:qr_base64],
        status: "provider_created"
      ) unless order.status == "approved"
    end
    order
  end

  def process_verified_payment(payment)
    payment = payment.to_h.deep_stringify_keys
    payment_id = payment["id"].to_s
    order = PaymentOrder.find_by(external_reference: payment["external_reference"])
    return :unknown_order unless payment_id.present? && order

    expected = expected_credits(order)
    unless expected && PaymentPackages.find(order.package_code) &&
        order.project_credits == expected[:project_credits] &&
        order.ai_credits == expected[:ai_credits] &&
        order.deepseek_credits == expected[:deepseek_credits] &&
        order.amount_cents == expected[:amount_cents]
      order.update!(status: "mismatch") unless order.status == "approved"
      return :mismatch
    end

    unless payment["currency_id"] == "BRL" && amount_matches?(payment["transaction_amount"], order.amount_cents)
      order.update!(status: "mismatch", provider_payment_id: payment_id) unless order.status == "approved"
      return :mismatch
    end

    unless payment["status"] == "approved"
      if TERMINAL_FAILURES.include?(payment["status"]) && order.status != "approved"
        order.update!(status: "failed", provider_payment_id: payment_id)
      end
      return :not_approved
    end

    PaymentOrder.transaction do
      order.account.lock!
      order.lock!
      if order.payment_grant
        :duplicate
      elsif %w[failed mismatch].include?(order.status) ||
          (order.provider_payment_id.present? && order.provider_payment_id != payment_id)
        order.update!(status: "mismatch") unless order.status == "failed"
        :mismatch
      else
        grant = PaymentGrant.create!(
          account: order.account,
          payment_order: order,
          payment_id:,
          package_code: order.package_code,
          project_credits: order.project_credits,
          ai_credits: order.ai_credits,
          deepseek_credits: order.deepseek_credits
        )
        account = order.account
        account.update!(
          project_limit: account.project_limit + grant.project_credits,
          deepseek_limit: account.deepseek_limit + grant.ai_credits + grant.deepseek_credits,
          plan_code: higher_plan(account.plan_code, order.package_code)
        )
        order.update!(provider_payment_id: payment_id, status: "approved")
        :approved
      end
    end
  end

  private

  def gateway
    @gateway ||= MercadoPagoGateway.new
  end

  def expected_credits(order)
    definition = PaymentPackages.find(order.package_code)
    return unless definition

    {
      project_credits: definition.fetch(:project_credits) * order.quantity,
      ai_credits: definition.fetch(:ai_credits) * order.quantity,
      deepseek_credits: definition.fetch(:deepseek_credits) * order.quantity,
      amount_cents: definition.fetch(:price_cents) * order.quantity
    }
  end

  def amount_matches?(amount, expected_cents)
    BigDecimal(amount.to_s).round(2) * 100 == expected_cents
  rescue ArgumentError
    false
  end

  def higher_plan(current, purchased)
    PaymentPackages.tier(purchased) > PaymentPackages.tier(current) ? purchased : current
  end
end
