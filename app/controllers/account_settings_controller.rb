class AccountSettingsController < ApplicationController
  before_action :authenticate_account!

  def show
    @account = current_account
  end

  def update_profile
    current_account.update_profile!(
      name: params[:name],
      profile: {
        "institution" => params[:institution],
        "city" => params[:city],
        "disciplines" => params[:disciplines].to_s.lines,
        "teachers" => params[:teachers].to_s.lines,
        "course" => params[:course],
        "period" => params[:period],
        "shift" => params[:shift]
      }
    )
    redirect_to account_settings_path(saved: "profile"), notice: "Perfil atualizado."
  rescue ActiveRecord::RecordInvalid
    @account = current_account
    @account.profile = @account.profile.merge("institution" => params[:institution].to_s)
    render :show, status: :unprocessable_entity
  end

  def accept_terms
    accepted = %w[on 1 true].include?(params[:accept].to_s)
    ai_consent = %w[on 1 true].include?(params[:ai_consent].to_s)
    current_account.accept_terms!(accept: accepted, ai_consent:)
    redirect_to account_settings_path(saved: "terms"), notice: "Consentimentos salvos."
  rescue ArgumentError => error
    redirect_to account_settings_path(error: "terms"), alert: error.message
  end

  def delete_account
    unless params[:confirmation].to_s == current_account.email
      return redirect_to account_settings_path(anchor: "delete-account"), alert: "Digite seu e-mail para confirmar a exclusão."
    end

    account = current_account
    account.destroy!
    reset_session
    redirect_to root_path, notice: "Sua conta e seus dados foram excluídos."
  end
end
