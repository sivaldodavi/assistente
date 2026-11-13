class AllowProjectFreeAIReservations < ActiveRecord::Migration[8.1]
  def change
    change_column_null :ai_usage_reservations, :project_id, true
  end
end
