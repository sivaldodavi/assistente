require "test_helper"
require_relative "../../script/configure_production_mercadopago"
require "stringio"

class ConfigureProductionMercadoPagoTest < ActiveSupport::TestCase
  test "shows production values and transfers only after both confirmations" do
    values = [
      "APP_USR-production-token",
      "production-webhook-signature",
      "PRODUCAO",
      "SIM"
    ]
    output = StringIO.new
    transferred = nil

    result = ProductionMercadoPagoSetup.run(
      input: StringIO.new(values.join("\n")),
      output:,
      transfer: ->(**secrets) { transferred = secrets }
    )

    assert_equal :saved, result
    assert_equal(
      {
        access_token: "APP_USR-production-token",
        webhook_secret: "production-webhook-signature"
      },
      transferred
    )
    assert_includes output.string, "APP_USR-production-token"
    assert_includes output.string, "production-webhook-signature"
    assert_includes output.string, "O staging não foi alterado."
  end

  test "does not transfer when production environment confirmation is declined" do
    values = [ "token", "webhook-secret", "TESTE", "SIM" ]
    transferred = false

    result = ProductionMercadoPagoSetup.run(
      input: StringIO.new(values.join("\n")),
      output: StringIO.new,
      transfer: ->(**) { transferred = true }
    )

    assert_equal :cancelled, result
    assert_not transferred
  end

  test "does not transfer when final installation confirmation is declined" do
    values = [ "token", "webhook-secret", "PRODUCAO", "NAO" ]
    transferred = false

    result = ProductionMercadoPagoSetup.run(
      input: StringIO.new(values.join("\n")),
      output: StringIO.new,
      transfer: ->(**) { transferred = true }
    )

    assert_equal :cancelled, result
    assert_not transferred
  end

  test "rejects credentials that cannot be stored safely" do
    values = [ "t" * 4_097, "webhook-secret" ]

    assert_raises(RuntimeError) do
      ProductionMercadoPagoSetup.run(
        input: StringIO.new(values.join("\n")),
        output: StringIO.new,
        transfer: ->(**) { flunk "must not transfer invalid credentials" }
      )
    end
  end
end
