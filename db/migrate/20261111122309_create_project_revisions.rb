class CreateProjectRevisions < ActiveRecord::Migration[8.1]
  def change
    create_table :project_revisions do |t|
      t.references :project, null: false, foreign_key: true
      t.integer :revision, null: false
      t.json :snapshot, null: false, default: {}

      t.timestamps
    end

    add_index :project_revisions, [ :project_id, :revision ], unique: true
  end
end
