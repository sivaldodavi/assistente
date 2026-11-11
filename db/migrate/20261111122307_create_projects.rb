class CreateProjects < ActiveRecord::Migration[8.1]
  def change
    create_table :projects do |t|
      t.string :project_type, null: false
      t.string :title, null: false, default: ""
      t.json :fields, null: false, default: {}
      t.json :checks, null: false, default: {}
      t.json :criteria, null: false, default: []
      t.json :development_sections, null: false, default: []
      t.json :source_ids, null: false, default: []
      t.json :deliveries, null: false, default: {}
      t.string :current_stage, null: false
      t.integer :lock_version, null: false, default: 0

      t.timestamps
    end

    add_index :projects, :project_type
  end
end
