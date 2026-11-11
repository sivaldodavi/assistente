class AIProviderSecrets
  def self.load(env_name:, file_env_name:, default_file:, credential_key:)
    value = ENV[env_name].to_s.strip
    path = ENV[file_env_name].presence || default_file
    if value.blank? && path.present?
      value = File.read(path, encoding: "utf-8").strip
    end
    if value.blank?
      value = Rails.application.credentials.dig(:ai, credential_key).to_s.strip
    end
    unless value.present? && value.bytesize <= 4_096 && !value.match?(/[\r\n]/)
      raise AIProviderError.new("secret_unavailable", "A configuração do serviço de IA está indisponível.", 503)
    end

    value
  rescue Errno::ENOENT, Errno::EACCES, IOError, EncodingError
    raise AIProviderError.new("secret_unavailable", "A configuração do serviço de IA não pôde ser carregada.", 503)
  end
end
