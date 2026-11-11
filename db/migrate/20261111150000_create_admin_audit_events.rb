class CreateAdminAuditEvents < ActiveRecord::Migration[8.1]
  def change
    create_table :admin_audit_events do |t|
      t.references :actor_account, foreign_key: { to_table: :accounts, on_delete: :nullify }
      t.references :target_account, foreign_key: { to_table: :accounts, on_delete: :nullify }
      t.string :action, null: false
      t.json :details, null: false, default: {}
      t.timestamps
    end
    add_index :admin_audit_events, :created_at
    add_index :admin_audit_events, :action
  end
end
