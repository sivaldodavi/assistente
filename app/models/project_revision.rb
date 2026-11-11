class ProjectRevision < ApplicationRecord
  belongs_to :project, inverse_of: :revisions

  validates :revision, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
  validates :snapshot, presence: true
end
