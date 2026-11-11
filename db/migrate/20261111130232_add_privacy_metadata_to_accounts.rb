class AddPrivacyMetadataToAccounts < ActiveRecord::Migration[8.1]
  def change
    add_column :accounts, :terms_accepted_at, :datetime
  end
end
