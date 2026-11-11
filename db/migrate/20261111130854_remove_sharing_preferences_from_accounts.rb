class RemoveSharingPreferencesFromAccounts < ActiveRecord::Migration[8.1]
  def change
    remove_column :accounts, :sharing_preferences_version, :integer, default: 1, null: false
    remove_column :accounts, :sharing_allow_admin_view, :boolean, default: false, null: false
    remove_column :accounts, :sharing_inherit_default, :boolean, default: true, null: false
  end
end
