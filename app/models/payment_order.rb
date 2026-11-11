class PaymentOrder < ApplicationRecord
  belongs_to :account
  has_one :payment_grant, dependent: :destroy

  before_validation :assign_identifiers, on: :create

  validates :request_id, presence: true, length: { maximum: 100 }, uniqueness: { scope: :account_id }
  validates :external_reference, :idempotency_key, presence: true, uniqueness: true
  validates :package_code, inclusion: { in: PaymentPackages::DEFINITIONS.keys }
  validates :quantity, numericality: { only_integer: true, greater_than: 0, less_than_or_equal_to: PaymentPackages::MAX_QUANTITY }
  validates :project_credits, :ai_credits, :deepseek_credits, :amount_cents, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
  validates :status, inclusion: { in: %w[created provider_created reconciliation_required approved failed mismatch] }

  def public_status
    status
  end

  private

  def assign_identifiers
    self.external_reference ||= SecureRandom.uuid
    self.idempotency_key ||= SecureRandom.uuid
  end
end
