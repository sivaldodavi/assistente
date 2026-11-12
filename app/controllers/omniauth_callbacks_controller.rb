class OmniauthCallbacksController < ApplicationController
  def google_oauth2
    auth = request.env["omniauth.auth"]
    unless valid_google_auth?(auth)
      return redirect_to login_path, alert: "Não foi possível verificar a conta Google."
    end

    account = Account.find_by(google_sub: auth.uid)
    account ||= Account.find_by(email: auth.info.email.to_s.strip.downcase)
    if account&.google_sub.present? && account.google_sub != auth.uid
      return redirect_to login_path, alert: "Esta conta já está vinculada a outro login Google."
    end

    account ||= Account.new
    account.assign_attributes(
      google_sub: auth.uid,
      email: auth.info.email.to_s.strip.downcase,
      name: auth.info.name.to_s.strip,
      last_login_at: Time.current
    )
    account.save!
    if account.is_blocked?
      reset_session
      return redirect_to root_path, alert: "Esta conta está impedida de acessar o sistema."
    end

    reset_session
    session[:account_id] = account.id
    if public_shell_only?
      return redirect_to root_path, notice: "Login Google validado. O acesso às áreas privadas e aos pagamentos continua fechado."
    end

    redirect_to projects_path, notice: "Sessão iniciada."
  rescue ActiveRecord::RecordInvalid, ActiveRecord::RecordNotUnique
    Rails.logger.warn("google_oauth_callback_failed")
    redirect_to login_path, alert: "Não foi possível iniciar sessão com o Google."
  end

  def failure
    if request.env["omniauth.error.type"].to_s == "csrf_detected"
      return redirect_to login_path,
        alert: "O navegador não preservou a sessão segura do login. " \
          "Inicie novamente pela página de login e permita cookies para este site."
    end

    redirect_to login_path, alert: "Não foi possível iniciar sessão com o Google."
  end

  private

  def valid_google_auth?(auth)
    return false unless auth.respond_to?(:provider)

    state = request.params["state"].to_s
    expected_nonce = consume_google_nonce(state)
    actual_nonce = auth.extra&.id_info&.nonce

    auth.provider == "google_oauth2" &&
      auth.uid.is_a?(String) &&
      auth.uid.present? &&
      auth.uid.bytesize <= 255 &&
      auth.info&.email.is_a?(String) &&
      auth.info.email.present? &&
      auth.extra&.id_info&.email_verified == true &&
      expected_nonce.is_a?(String) &&
      actual_nonce.is_a?(String) &&
      expected_nonce.bytesize == actual_nonce.bytesize &&
      ActiveSupport::SecurityUtils.secure_compare(expected_nonce, actual_nonce)
  end

  def consume_google_nonce(state)
    return if state.blank?

    nonces = session[OmniAuth::Strategies::GoogleOauth2WithNonce::NONCE_SESSION_KEY]
    return unless nonces.is_a?(Hash)

    expected_nonce = nonces.delete(state)
    session[OmniAuth::Strategies::GoogleOauth2WithNonce::NONCE_SESSION_KEY] = nonces
    expected_nonce
  end
end
