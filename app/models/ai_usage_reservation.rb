class AIUsageReservation < ApplicationRecord
  belongs_to :account
  belongs_to :project

  validates :request_id, presence: true, uniqueness: true
  validates :action, presence: true, length: { maximum: 120 }
  validates :status, inclusion: { in: %w[reserved complete refunded] }
  validates :credit_type, inclusion: { in: %w[ai deepseek] }
end
