class ProviderUsage < ApplicationRecord
  belongs_to :account

  validates :request_id, :provider, :operation, :model, :status, presence: true
  validates :provider, length: { maximum: 80 }
  validates :operation, length: { maximum: 120 }
  validates :model, length: { maximum: 160 }
  validates :status, length: { maximum: 40 }
end
