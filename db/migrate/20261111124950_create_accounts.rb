class CreateAccounts < ActiveRecord::Migration[8.1]
  def change
    create_table :accounts do |t|
      t.string :email, null: false, default: ""
      t.string :google_sub
      t.string :name, null: false, default: ""
      t.json :profile, null: false, default: {}
      t.boolean :terms_accepted, null: false, default: false
      t.string :terms_version
      t.boolean :ai_consent, null: false, default: false
      t.boolean :is_blocked, null: false, default: false
      t.string :role, null: false, default: "user"
      t.integer :sharing_preferences_version, null: false, default: 1
      t.boolean :sharing_allow_admin_view, null: false, default: false
      t.boolean :sharing_inherit_default, null: false, default: true
      t.boolean :deletion_request_pending, null: false, default: false

      t.timestamps
    end

    add_index :accounts, "lower(email)", unique: true, name: "index_accounts_on_lower_email"
    add_index :accounts, :google_sub, unique: true
  end
end
