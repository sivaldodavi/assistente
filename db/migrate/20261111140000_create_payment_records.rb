class CreatePaymentRecords < ActiveRecord::Migration[8.1]
  def change
    change_table :accounts, bulk: true do |t|
      t.string :plan_code, null: false, default: "livre"
      t.integer :project_limit, null: false, default: 0
      t.integer :project_used, null: false, default: 0
      t.integer :deepseek_limit, null: false, default: 0
      t.integer :deepseek_used, null: false, default: 0
    end
    change_column_default :accounts, :ai_limit, from: 100, to: 0

    add_column :ai_usage_reservations, :credit_type, :string, null: false, default: "ai"

    create_table :payment_orders do |t|
      t.references :account, null: false, foreign_key: true
      t.string :request_id, null: false
      t.string :external_reference, null: false
      t.string :package_code, null: false
      t.integer :quantity, null: false
      t.integer :project_credits, null: false
      t.integer :ai_credits, null: false
      t.integer :deepseek_credits, null: false
      t.integer :amount_cents, null: false
      t.string :idempotency_key, null: false
      t.string :provider_payment_id
      t.string :status, null: false, default: "created"
      t.text :pix_copy_code
      t.text :pix_qr_base64
      t.datetime :expires_at
      t.timestamps
    end
    add_index :payment_orders, [ :account_id, :request_id ], unique: true
    add_index :payment_orders, :external_reference, unique: true
    add_index :payment_orders, :idempotency_key, unique: true
    add_index :payment_orders, :provider_payment_id, unique: true, where: "provider_payment_id IS NOT NULL"

    create_table :payment_grants do |t|
      t.references :account, null: false, foreign_key: true
      t.references :payment_order, null: false, foreign_key: true, index: { unique: true }
      t.string :payment_id, null: false
      t.string :package_code, null: false
      t.integer :project_credits, null: false
      t.integer :ai_credits, null: false
      t.integer :deepseek_credits, null: false
      t.timestamps
    end
    add_index :payment_grants, :payment_id, unique: true

    create_table :payment_webhook_events do |t|
      t.string :event_key, null: false
      t.string :event_type, null: false
      t.string :payment_id
      t.string :result, null: false, default: "received"
      t.string :error_code
      t.datetime :received_at, null: false
      t.datetime :processed_at
      t.timestamps
    end
    add_index :payment_webhook_events, :event_key, unique: true
    add_index :payment_webhook_events, [ :payment_id, :received_at ]
  end
end
