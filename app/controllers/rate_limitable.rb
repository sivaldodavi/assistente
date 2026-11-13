module RateLimitable
  extend ActiveSupport::Concern

  private

  # Conta solicitações por conta e janela de tempo. Com cache em memória, o limite vale por processo.
  def rate_limited?(scope, limit:, period: 10.minutes)
    window = Time.current.to_i / period.to_i
    key = "rate_limit:#{scope}:#{current_account.id}:#{window}"
    count = Rails.cache.increment(key)
    if count.nil?
      Rails.cache.write(key, 1, expires_in: period)
      count = 1
    end
    count > limit
  end
end
