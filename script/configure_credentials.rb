require "uri"
require "yaml"

module CredentialSetup
  FIELDS = [
    { label: "Google OAuth — Client ID", path: %w[google client_id] },
    { label: "Google OAuth — Client Secret", path: %w[google client_secret] },
    { label: "Google OAuth — Redirect URI", path: %w[google redirect_uri], kind: :callback },
    { label: "DeepSeek — API key", path: %w[ai deepseek_api_key] },
    { label: "Gemini — API key de fallback", path: %w[ai gemini_api_key] },
    { label: "Claude — API key de fallback", path: %w[ai claude_api_key] },
    { label: "TypeSafe JEV — API key", path: %w[ai typesafe_api_key] },
    { label: "Mercado Pago — Access Token de TESTE", path: %w[mercadopago access_token] },
    { label: "Mercado Pago — segredo de assinatura do webhook", path: %w[mercadopago webhook_secret] },
    { label: "Mercado Pago — URL HTTPS do webhook", path: %w[mercadopago webhook_url], kind: :webhook }
  ].freeze

  def self.run(input: $stdin, output: $stdout, credentials: Rails.application.credentials)
    raise "Não configure credenciais por este script em production." if Rails.env.production?

    current = credentials.config.deep_stringify_keys
    changes = {}

    output.puts "As entradas ficarão visíveis neste terminal. Use credenciais de teste/sandbox."
    output.puts "Deixe vazio para manter o valor atual ou pular esse item."

    FIELDS.each do |field|
      configured = field[:path].reduce(current) { |hash, key| hash.is_a?(Hash) ? hash[key] : nil }.present?
      output.puts "\n#{field[:label]} (#{configured ? "já configurado" : "não configurado"}):"
      output.print "> "
      value = input.gets
      raise "Entrada encerrada antes de concluir." unless value

      value = value.chomp.strip
      next if value.empty?

      validate!(field, value)
      changes.deep_merge!(nested_hash(field[:path], value))
    end

    if changes.empty?
      output.puts "\nNenhuma alteração. As credenciais foram mantidas."
      return :unchanged
    end

    output.puts "\nConfira o que será salvo (os valores aparecem apenas neste terminal):"
    FIELDS.each do |field|
      value = field[:path].reduce(changes) { |hash, key| hash.is_a?(Hash) ? hash[key] : nil }
      output.puts "#{field[:label]}: #{value}" if value
    end
    output.print "\nDigite SIM para gravar criptografado; qualquer outra resposta cancela: "
    return :cancelled unless input.gets&.chomp == "SIM"

    credentials.write(YAML.dump(current.deep_merge(changes)))
    output.puts "Credenciais salvas em config/credentials.yml.enc."
    :saved
  end

  def self.validate!(field, value)
    raise "#{field[:label]} excede o limite de tamanho." if value.bytesize > 4_096
    return unless field[:kind]

    uri = URI.parse(value)
    valid_uri = uri.host.present? && uri.userinfo.nil? && uri.query.nil? && uri.fragment.nil?
    valid_callback = field[:kind] == :callback &&
      %w[http https].include?(uri.scheme) &&
      uri.path == "/auth/google_oauth2/callback" &&
      (uri.scheme == "https" || uri.host == "localhost")
    valid_webhook = field[:kind] == :webhook &&
      uri.scheme == "https" &&
      uri.path == "/webhooks/mercadopago"
    return if valid_uri && (valid_callback || valid_webhook)

    expected = field[:kind] == :callback ?
      "Use http://localhost ou HTTPS e termine em /auth/google_oauth2/callback." :
      "Use HTTPS e termine em /webhooks/mercadopago."
    raise "#{field[:label]} inválida. #{expected}"
  rescue URI::InvalidURIError
    raise "#{field[:label]} não é uma URL válida."
  end
  private_class_method :validate!

  def self.nested_hash(path, value)
    path.reverse.reduce(value) { |nested, key| { key => nested } }
  end
  private_class_method :nested_hash
end

CredentialSetup.run if $PROGRAM_NAME == __FILE__
