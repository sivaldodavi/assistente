class PaymentReconciliation
  MINIMUM_AGE = 5.minutes
  BATCH_SIZE = 100
  PENDING_STATUSES = %w[created provider_created reconciliation_required].freeze

  def initialize(gateway: MercadoPagoGateway.new, payment_service: PaymentService.new(gateway:))
    @gateway = gateway
    @payment_service = payment_service
  end

  def call(at: Time.current)
    stats = { checked: 0, reconciled: 0, pending: 0, missing: 0, failed: 0, mismatch: 0, errors: 0 }

    pending_orders(at:).each do |order|
      stats[:checked] += 1
      outcome = reconcile(order)
      stats[outcome] += 1
    rescue MercadoPagoGateway::GatewayError => error
      Rails.logger.error("payment_reconciliation_failed order_id=#{order.id} code=#{error.code}")
      stats[:errors] += 1
    ensure
      order.touch if PENDING_STATUSES.include?(order.reload.status)
    end

    stats
  end

  private

  def pending_orders(at:)
    PaymentOrder
      .where(status: PENDING_STATUSES)
      .where("updated_at <= ?", at - MINIMUM_AGE)
      .order(:updated_at, :id)
      .limit(BATCH_SIZE)
  end

  def reconcile(order)
    payment = if order.provider_payment_id.present?
      @gateway.fetch_payment(order.provider_payment_id)
    else
      matching_payments = @gateway.search_payments(external_reference: order.external_reference)
        .select { |candidate| value(candidate, "external_reference").to_s == order.external_reference }
      return :missing if matching_payments.empty?
      return mark_mismatch(order) unless matching_payments.one?

      matching_payments.first
    end

    payment_id = value(payment, "id").to_s
    unless payment_id.present? &&
        value(payment, "external_reference").to_s == order.external_reference &&
        (order.provider_payment_id.blank? || order.provider_payment_id.to_s == payment_id)
      return mark_mismatch(order)
    end

    order.with_lock do
      return :reconciled if order.status == "approved"

      order.update!(provider_payment_id: payment_id) if order.provider_payment_id.blank?
    end

    @payment_service.process_verified_payment(payment)
    status = order.reload.status
    return :reconciled if status == "approved"
    return :failed if status == "failed"
    return :mismatch if status == "mismatch"

    :pending
  end

  def mark_mismatch(order)
    order.with_lock do
      return :reconciled if order.status == "approved"
      return order.status.to_sym if %w[failed mismatch].include?(order.status)

      order.update!(status: "mismatch")
    end
    :mismatch
  end

  def value(hash, key)
    return unless hash.is_a?(Hash)

    hash[key] || hash[key.to_sym]
  end
end
