require "omniauth/strategies/google_oauth2"
require "securerandom"

module OmniAuth
  module Strategies
    class GoogleOauth2WithNonce < GoogleOauth2
      NONCE_SESSION_KEY = "google_oauth2.nonces"
      MAX_STORED_NONCES = 10

      option :name, "google_oauth2"
      option :pkce, true

      def authorize_params
        super.tap do |params|
          state = params.fetch(:state).to_s
          nonce = SecureRandom.hex(32)
          params[:nonce] = nonce

          nonces = session[NONCE_SESSION_KEY].is_a?(Hash) ? session[NONCE_SESSION_KEY].dup : {}
          nonces[state] = nonce
          session[NONCE_SESSION_KEY] = nonces.to_a.last(MAX_STORED_NONCES).to_h
        end
      end
    end
  end
end
