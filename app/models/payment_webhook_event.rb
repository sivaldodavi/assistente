class PaymentWebhookEvent < ApplicationRecord
  validates :event_key, :event_type, :result, :received_at, presence: true
end
