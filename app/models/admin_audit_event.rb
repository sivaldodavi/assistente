class AdminAuditEvent < ApplicationRecord
  belongs_to :actor_account, class_name: "Account", optional: true
  belongs_to :target_account, class_name: "Account", optional: true

  validates :action, presence: true, length: { maximum: 80 }
  validate :details_are_hash

  private

  def details_are_hash
    errors.add(:details, "deve ser um objeto") unless details.is_a?(Hash)
  end
end
