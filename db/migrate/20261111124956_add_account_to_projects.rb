class AddAccountToProjects < ActiveRecord::Migration[8.1]
  def change
    add_reference :projects, :account, null: true, foreign_key: true
  end
end
