class SessionsController < ApplicationController
  def new
  end

  def dev_login
    return head :not_found unless Rails.env.development? || Rails.env.test?

    email = params[:email].to_s.strip.downcase.presence || "dev@example.test"
    name = params[:name].to_s.strip.presence || "Conta de desenvolvimento"
    account = Account.find_or_initialize_by(email:)
    account.name = name if account.new_record? || account.name.blank?
    account.save!
    return head :forbidden if account.is_blocked?

    reset_session
    session[:account_id] = account.id
    redirect_to projects_path, notice: "Sessão local iniciada."
  end

  def destroy
    reset_session
    redirect_to root_path, notice: "Sessão encerrada.", status: :see_other
  end
end
