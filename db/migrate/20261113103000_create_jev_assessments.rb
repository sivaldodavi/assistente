class CreateJevAssessments < ActiveRecord::Migration[8.1]
  def change
    create_table :jev_assessments do |t|
      t.references :account, null: false, foreign_key: true
      t.references :project, null: false, foreign_key: { on_delete: :cascade }
      t.references :project_revision, null: false,
        foreign_key: { to_table: :project_revisions, on_delete: :cascade }
      t.string :stage, null: false
      t.string :rubric_version, null: false
      t.string :model, null: false
      t.json :result, null: false, default: {}
      t.timestamps
    end

    add_index :jev_assessments, [ :project_id, :stage, :created_at ]
  end
end
