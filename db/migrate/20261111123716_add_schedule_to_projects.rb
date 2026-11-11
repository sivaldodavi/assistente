class AddScheduleToProjects < ActiveRecord::Migration[8.1]
  def change
    add_column :projects, :schedule, :json, null: false, default: {}
  end
end
