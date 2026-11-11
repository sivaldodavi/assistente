require "securerandom"

class AddPublicIdToSources < ActiveRecord::Migration[8.1]
  def up
    add_column :sources, :public_id, :string
    connection.select_values("SELECT id FROM sources WHERE public_id IS NULL").each do |source_id|
      public_id = connection.quote(SecureRandom.uuid)
      record_id = connection.quote(source_id)
      connection.execute(
        "UPDATE sources SET public_id = #{public_id} WHERE id = #{record_id}"
      )
    end
    change_column_null :sources, :public_id, false
    add_index :sources, :public_id, unique: true
  end

  def down
    remove_index :sources, :public_id
    remove_column :sources, :public_id
  end
end
