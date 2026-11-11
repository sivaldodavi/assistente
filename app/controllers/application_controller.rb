class ApplicationController < ActionController::Base
  protect_from_forgery with: :exception
  before_action :block_production_until_authentication
  before_action :load_current_account
  helper_method :current_account, :google_oauth_configured?

  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  # Changes to the importmap will invalidate the etag for HTML responses
  stale_when_importmap_changes

  private

  def current_account
    @current_account
  end

  def google_oauth_configured?
    Rails.application.config.x.google_oauth_client_id.present? &&
      Rails.application.config.x.google_oauth_client_secret.present?
  end

  def load_current_account
    @current_account = Account.find_by(id: session[:account_id]) if session[:account_id].present?
    if @current_account&.is_blocked?
      reset_session
      @current_account = nil
    end
  end

  def authenticate_account!
    return redirect_to login_path if current_account.nil?
    return unless current_account.is_blocked?

    reset_session
    redirect_to root_path, alert: "Esta conta está impedida de acessar o sistema."
  end

  def block_production_until_authentication
    return unless Rails.env.production? && !Rails.configuration.x.authentication_ready

    head :service_unavailable
  end
end
