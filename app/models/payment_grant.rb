class PaymentGrant < ApplicationRecord
  belongs_to :account
  belongs_to :payment_order

  validates :payment_id, presence: true, uniqueness: true
  validates :payment_order_id, uniqueness: true
  validates :package_code, inclusion: { in: PaymentPackages::DEFINITIONS.keys }
  validates :project_credits, :ai_credits, :deepseek_credits, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
end
