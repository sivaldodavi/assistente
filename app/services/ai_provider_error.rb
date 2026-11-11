class AIProviderError < StandardError
  attr_reader :code, :status

  def initialize(code, message, status = 503)
    @code = code
    @status = status
    super(message)
  end
end
