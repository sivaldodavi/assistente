class AIUsageService
  class UsageError < StandardError
    attr_reader :code, :status

    def initialize(code, message, status)
      @code = code
      @status = status
      super(message)
    end
  end

  def self.reserve!(account:, project:, request_id:, action:, credit_type: "ai")
    raise UsageError.new("project_not_found", "Projeto não encontrado.", :not_found) unless project.account_id == account.id
    fields = credit_fields(credit_type)

    account.with_lock do
      if AIUsageReservation.exists?(request_id:)
        raise UsageError.new("duplicate_usage_request", "Esta solicitação já foi processada.", :conflict)
      end
      if !account.admin? && account.public_send(fields[:used]) >= account.public_send(fields[:limit])
        code = credit_type == "deepseek" ? "deepseek_quota_exhausted" : "ai_quota_exhausted"
        message = credit_type == "deepseek" ? "Os créditos de assistência DeepSeek desta conta foram esgotados." : "Os créditos de avaliação JEV desta conta foram esgotados."
        raise UsageError.new(code, message, :too_many_requests)
      end

      AIUsageReservation.create!(account:, project:, request_id:, action:, credit_type:, units: 1, status: "reserved")
      account.update!(fields[:used] => account.public_send(fields[:used]) + 1)
    end
  end

  def self.finish!(request_id)
    reservation = AIUsageReservation.find_by(request_id:)
    return unless reservation

    reservation.with_lock do
      reservation.update!(status: "complete") if reservation.status == "reserved"
    end
  end

  def self.refund!(request_id)
    reservation = AIUsageReservation.find_by(request_id:)
    return unless reservation&.status == "reserved"

    reservation.with_lock do
      next unless reservation.status == "reserved"

      reservation.update!(status: "refunded")
      reservation.account.with_lock do
        used_field = credit_fields(reservation.credit_type)[:used]
        reservation.account.update!(used_field => [ reservation.account.public_send(used_field) - reservation.units, 0 ].max)
      end
    end
  end

  def self.record_provider_usage!(account:, request_id:, provider:, operation:, model:, usage:)
    usage = usage.is_a?(Hash) ? usage : {}
    ProviderUsage.create!(
      account:,
      request_id:,
      provider: provider.to_s.first(80),
      operation: operation.to_s.first(120),
      model: model.to_s.presence&.first(160) || "unknown",
      input_tokens: token_count(usage["prompt_tokens"] || usage["input_tokens"]),
      output_tokens: token_count(usage["completion_tokens"] || usage["output_tokens"]),
      status: "complete"
    )
  end

  def self.token_count(value)
    value if value.is_a?(Integer) && value >= 0
  end
  private_class_method :token_count

  def self.credit_fields(credit_type)
    case credit_type
    when "ai" then { used: :ai_used, limit: :ai_limit }
    when "deepseek" then { used: :deepseek_used, limit: :deepseek_limit }
    else raise ArgumentError, "tipo de crédito inválido"
    end
  end
  private_class_method :credit_fields
end
