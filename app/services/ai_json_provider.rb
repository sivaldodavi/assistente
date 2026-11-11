require "json"
require "net/http"
require "openssl"
require "uri"

class AIJsonProvider
  MAX_RESPONSE_BYTES = 4.megabytes

  def initialize(api_key:, api_url:, timeout: 30)
    @api_key = api_key
    @api_url = URI.parse(api_url)
    @timeout = Integer(timeout).clamp(1, 60)
    raise AIProviderError.new("provider_config", "A configuração do serviço de IA é inválida.") unless valid_endpoint?
  rescue URI::InvalidURIError, ArgumentError, TypeError
    raise AIProviderError.new("provider_config", "A configuração do serviço de IA é inválida.")
  end

  private

  def post_json(payload, headers: {})
    request = Net::HTTP::Post.new(@api_url)
    request["Accept"] = "application/json"
    request["Authorization"] = "Bearer #{@api_key}"
    request["Content-Type"] = "application/json"
    headers.each { |key, value| request[key] = value }
    request.body = JSON.generate(payload)

    response = nil
    raw = +""
    Net::HTTP.start(
      @api_url.host,
      @api_url.port,
      use_ssl: true,
      verify_mode: OpenSSL::SSL::VERIFY_PEER,
      open_timeout: 5,
      read_timeout: @timeout,
      write_timeout: @timeout
    ) do |http|
      response = http.request(request) do |incoming|
        incoming.read_body do |chunk|
          raw << chunk
          if raw.bytesize > MAX_RESPONSE_BYTES
            raise AIProviderError.new("response_too_large", "A resposta do serviço de IA é grande demais.", 502)
          end
        end
      end
    end
    unless response.is_a?(Net::HTTPSuccess)
      status = response.code.to_i
      code = status == 401 ? "provider_auth" : status == 402 ? "provider_quota" : status == 429 || status >= 500 ? "provider_busy" : "provider_error"
      safe_status = code == "provider_busy" ? 503 : 502
      raise AIProviderError.new(code, "O serviço de IA não concluiu a solicitação.", safe_status)
    end

    parsed = JSON.parse(raw)
    raise AIProviderError.new("invalid_response", "O serviço de IA retornou uma resposta inválida.", 502) unless parsed.is_a?(Hash)

    parsed
  rescue Net::OpenTimeout, Net::ReadTimeout, SocketError, IOError, SystemCallError, OpenSSL::SSL::SSLError
    raise AIProviderError.new("provider_unreachable", "Não foi possível conectar ao serviço de IA.", 503)
  rescue JSON::ParserError
    raise AIProviderError.new("invalid_response", "O serviço de IA retornou uma resposta inválida.", 502)
  end

  def valid_endpoint?
    @api_key.is_a?(String) &&
      @api_key.present? &&
      @api_key.bytesize <= 4096 &&
      !@api_key.match?(/[\r\n]/) &&
      @api_url.scheme == "https" &&
      @api_url.host.present? &&
      @api_url.userinfo.nil? &&
      @api_url.fragment.nil?
  end
end
