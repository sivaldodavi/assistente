class CreateAIUsage < ActiveRecord::Migration[8.1]
  def change
    add_column :accounts, :ai_limit, :integer, null: false, default: 100
    add_column :accounts, :ai_used, :integer, null: false, default: 0

    create_table :ai_usage_reservations do |t|
      t.references :account, null: false, foreign_key: true
      t.references :project, null: false, foreign_key: true
      t.string :request_id, null: false
      t.string :action, null: false
      t.integer :units, null: false, default: 1
      t.string :status, null: false, default: "reserved"
      t.timestamps
    end
    add_index :ai_usage_reservations, :request_id, unique: true
    add_index :ai_usage_reservations, [ :account_id, :status ]

    create_table :provider_usages do |t|
      t.references :account, null: false, foreign_key: true
      t.string :request_id, null: false
      t.string :provider, null: false
      t.string :operation, null: false
      t.string :model, null: false
      t.integer :input_tokens
      t.integer :output_tokens
      t.string :status, null: false
      t.timestamps
    end
    add_index :provider_usages, :request_id
  end
end
