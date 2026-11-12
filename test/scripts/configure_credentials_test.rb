require "test_helper"
require_relative "../../script/configure_credentials"
require "stringio"

class ConfigureCredentialsTest < ActiveSupport::TestCase
  class FakeCredentials
    attr_reader :config, :written

    def initialize(config)
      @config = config
    end

    def write(contents)
      @written = contents
    end
  end

  test "shows entered values, preserves existing credentials, and writes only after confirmation" do
    credentials = FakeCredentials.new({ "secret_key_base" => "preserved" })
    values = [
      "client-id",
      "client-secret",
      "http://localhost:3000/auth/google_oauth2/callback",
      "deepseek-key",
      "typesafe-key",
      "TEST-access-token",
      "webhook-secret",
      "https://trab.sivaldodavi.com.br/webhooks/mercadopago",
      "SIM"
    ]
    output = StringIO.new

    result = CredentialSetup.run(input: StringIO.new(values.join("\n")), output:, credentials:)

    assert_equal :saved, result
    assert_includes output.string, "TEST-access-token"
    saved = YAML.safe_load(credentials.written)
    assert_equal "preserved", saved.fetch("secret_key_base")
    assert_equal "client-secret", saved.dig("google", "client_secret")
    assert_equal "deepseek-key", saved.dig("ai", "deepseek_api_key")
    assert_equal "TEST-access-token", saved.dig("mercadopago", "access_token")
    assert_equal "https://trab.sivaldodavi.com.br/webhooks/mercadopago", saved.dig("mercadopago", "webhook_url")
  end

  test "does not write credentials when confirmation is declined" do
    credentials = FakeCredentials.new({})
    values = [ "client-id", *Array.new(7, ""), "NAO" ]

    result = CredentialSetup.run(input: StringIO.new(values.join("\n")), output: StringIO.new, credentials:)

    assert_equal :cancelled, result
    assert_nil credentials.written
  end
end
