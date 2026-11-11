require "securerandom"

class Source < ApplicationRecord
  KINDS = %w[book article legislation case_law website other].freeze
  MAX_NOTES_LENGTH = 5_000

  belongs_to :account, inverse_of: :sources

  before_validation :normalize_source

  validates :public_id, presence: true, uniqueness: true
  validates :title, presence: true, length: { maximum: 240 }
  validates :author, length: { maximum: 240 }
  validates :kind, inclusion: { in: KINDS }
  validates :reference, length: { maximum: 500 }
  validates :notes, length: { maximum: MAX_NOTES_LENGTH }

  private

  def normalize_source
    self.public_id ||= SecureRandom.uuid
    self.title = title.to_s.strip
    self.author = author.to_s.strip
    self.kind = KINDS.include?(kind) ? kind : "other"
    self.reference = reference.to_s.strip
    self.notes = notes.to_s.strip
  end
end
