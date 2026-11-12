class RemoveScheduleFromProjects < ActiveRecord::Migration[8.1]
  def change
    remove_column :projects, :schedule, :json, default: {}, null: false
  end
end
