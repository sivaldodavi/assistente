# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_11_12_130000) do
  create_table "accounts", force: :cascade do |t|
    t.string "email", default: "", null: false
    t.string "google_sub"
    t.string "name", default: "", null: false
    t.json "profile", default: {}, null: false
    t.boolean "terms_accepted", default: false, null: false
    t.string "terms_version"
    t.boolean "ai_consent", default: false, null: false
    t.boolean "is_blocked", default: false, null: false
    t.string "role", default: "user", null: false
    t.boolean "deletion_request_pending", default: false, null: false
    t.datetime "last_login_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.datetime "terms_accepted_at"
    t.integer "ai_limit", default: 0, null: false
    t.integer "ai_used", default: 0, null: false
    t.string "plan_code", default: "livre", null: false
    t.integer "project_limit", default: 0, null: false
    t.integer "project_used", default: 0, null: false
    t.integer "deepseek_limit", default: 0, null: false
    t.integer "deepseek_used", default: 0, null: false
    t.index "lower(email)", name: "index_accounts_on_lower_email", unique: true
    t.index ["google_sub"], name: "index_accounts_on_google_sub", unique: true
  end

  create_table "admin_audit_events", force: :cascade do |t|
    t.integer "actor_account_id"
    t.integer "target_account_id"
    t.string "action", null: false
    t.json "details", default: {}, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["action"], name: "index_admin_audit_events_on_action"
    t.index ["actor_account_id"], name: "index_admin_audit_events_on_actor_account_id"
    t.index ["created_at"], name: "index_admin_audit_events_on_created_at"
    t.index ["target_account_id"], name: "index_admin_audit_events_on_target_account_id"
  end

  create_table "ai_usage_reservations", force: :cascade do |t|
    t.integer "account_id", null: false
    t.integer "project_id", null: false
    t.string "request_id", null: false
    t.string "action", null: false
    t.integer "units", default: 1, null: false
    t.string "status", default: "reserved", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.string "credit_type", default: "ai", null: false
    t.index ["account_id", "status"], name: "index_ai_usage_reservations_on_account_id_and_status"
    t.index ["account_id"], name: "index_ai_usage_reservations_on_account_id"
    t.index ["project_id"], name: "index_ai_usage_reservations_on_project_id"
    t.index ["request_id"], name: "index_ai_usage_reservations_on_request_id", unique: true
  end

  create_table "payment_grants", force: :cascade do |t|
    t.integer "account_id", null: false
    t.integer "payment_order_id", null: false
    t.string "payment_id", null: false
    t.string "package_code", null: false
    t.integer "project_credits", null: false
    t.integer "ai_credits", null: false
    t.integer "deepseek_credits", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["account_id"], name: "index_payment_grants_on_account_id"
    t.index ["payment_id"], name: "index_payment_grants_on_payment_id", unique: true
    t.index ["payment_order_id"], name: "index_payment_grants_on_payment_order_id", unique: true
  end

  create_table "payment_orders", force: :cascade do |t|
    t.integer "account_id", null: false
    t.string "request_id", null: false
    t.string "external_reference", null: false
    t.string "package_code", null: false
    t.integer "quantity", null: false
    t.integer "project_credits", null: false
    t.integer "ai_credits", null: false
    t.integer "deepseek_credits", null: false
    t.integer "amount_cents", null: false
    t.string "idempotency_key", null: false
    t.string "provider_payment_id"
    t.string "status", default: "created", null: false
    t.text "pix_copy_code"
    t.text "pix_qr_base64"
    t.datetime "expires_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["account_id", "request_id"], name: "index_payment_orders_on_account_id_and_request_id", unique: true
    t.index ["account_id"], name: "index_payment_orders_on_account_id"
    t.index ["external_reference"], name: "index_payment_orders_on_external_reference", unique: true
    t.index ["idempotency_key"], name: "index_payment_orders_on_idempotency_key", unique: true
    t.index ["provider_payment_id"], name: "index_payment_orders_on_provider_payment_id", unique: true, where: "provider_payment_id IS NOT NULL"
  end

  create_table "payment_webhook_events", force: :cascade do |t|
    t.string "event_key", null: false
    t.string "event_type", null: false
    t.string "payment_id"
    t.string "result", default: "received", null: false
    t.string "error_code"
    t.datetime "received_at", null: false
    t.datetime "processed_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["event_key"], name: "index_payment_webhook_events_on_event_key", unique: true
    t.index ["payment_id", "received_at"], name: "index_payment_webhook_events_on_payment_id_and_received_at"
  end

  create_table "project_revisions", force: :cascade do |t|
    t.integer "project_id", null: false
    t.integer "revision", null: false
    t.json "snapshot", default: {}, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["project_id", "revision"], name: "index_project_revisions_on_project_id_and_revision", unique: true
    t.index ["project_id"], name: "index_project_revisions_on_project_id"
  end

  create_table "projects", force: :cascade do |t|
    t.string "project_type", null: false
    t.string "title", default: "", null: false
    t.json "fields", default: {}, null: false
    t.json "checks", default: {}, null: false
    t.json "criteria", default: [], null: false
    t.json "development_sections", default: [], null: false
    t.json "source_ids", default: [], null: false
    t.json "deliveries", default: {}, null: false
    t.string "current_stage", null: false
    t.integer "lock_version", default: 0, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.integer "account_id"
    t.index ["account_id"], name: "index_projects_on_account_id"
    t.index ["project_type"], name: "index_projects_on_project_type"
  end

  create_table "provider_usages", force: :cascade do |t|
    t.integer "account_id", null: false
    t.string "request_id", null: false
    t.string "provider", null: false
    t.string "operation", null: false
    t.string "model", null: false
    t.integer "input_tokens"
    t.integer "output_tokens"
    t.string "status", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["account_id"], name: "index_provider_usages_on_account_id"
    t.index ["request_id"], name: "index_provider_usages_on_request_id"
  end

  create_table "sources", force: :cascade do |t|
    t.integer "account_id", null: false
    t.string "title", default: "", null: false
    t.string "author", default: "", null: false
    t.string "kind", default: "other", null: false
    t.string "reference", default: "", null: false
    t.text "notes", default: "", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.string "public_id", null: false
    t.index ["account_id", "updated_at"], name: "index_sources_on_account_id_and_updated_at"
    t.index ["account_id"], name: "index_sources_on_account_id"
    t.index ["public_id"], name: "index_sources_on_public_id", unique: true
  end

  add_foreign_key "admin_audit_events", "accounts", column: "actor_account_id", on_delete: :nullify
  add_foreign_key "admin_audit_events", "accounts", column: "target_account_id", on_delete: :nullify
  add_foreign_key "ai_usage_reservations", "accounts"
  add_foreign_key "ai_usage_reservations", "projects"
  add_foreign_key "payment_grants", "accounts"
  add_foreign_key "payment_grants", "payment_orders"
  add_foreign_key "payment_orders", "accounts"
  add_foreign_key "project_revisions", "projects"
  add_foreign_key "projects", "accounts"
  add_foreign_key "provider_usages", "accounts"
  add_foreign_key "sources", "accounts"
end
