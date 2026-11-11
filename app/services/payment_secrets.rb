class PaymentSecrets
  class ConfigurationError < StandardError; end

  def self.access_token
    load_secret(
      env_name: "MERCADOPAGO_ACCESS_TOKEN",
      file_env_name: "MERCADOPAGO_ACCESS_TOKEN_FILE",
      default_file: "/run/secrets/mercadopago_access_token",
      credential_key: :access_token
    )
  end

  def self.webhook_secret
    load_secret(
      env_name: "MERCADOPAGO_WEBHOOK_SECRET",
      file_env_name: "MERCADOPAGO_WEBHOOK_SECRET_FILE",
      default_file: "/run/secrets/mercadopago_webhook_secret",
      credential_key: :webhook_secret
    )
  end

  def self.load_secret(env_name:, file_env_name:, default_file:, credential_key:)
    value = ENV[env_name].presence ||
      Rails.application.credentials.dig(:mercadopago, credential_key).presence
    value ||= File.read(ENV.fetch(file_env_name, default_file), 4097).strip if File.file?(ENV.fetch(file_env_name, default_file))
    unless value.is_a?(String) && value.present? && value.bytesize <= 4096 && !value.match?(/[\r\n]/)
      raise ConfigurationError, "#{env_name} não está configurada."
    end

    value
  rescue Errno::EACCES, Errno::EISDIR, Errno::EIO => error
    raise ConfigurationError, "Não foi possível ler o segredo #{env_name}: #{error.class}."
  end
  private_class_method :load_secret
end
