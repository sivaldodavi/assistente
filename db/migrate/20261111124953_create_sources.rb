class CreateSources < ActiveRecord::Migration[8.1]
  def change
    create_table :sources do |t|
      t.references :account, null: false, foreign_key: true
      t.string :title, null: false, default: ""
      t.string :author, null: false, default: ""
      t.string :kind, null: false, default: "other"
      t.string :reference, null: false, default: ""
      t.text :notes, null: false, default: ""

      t.timestamps
    end

    add_index :sources, [ :account_id, :updated_at ]
  end
end
