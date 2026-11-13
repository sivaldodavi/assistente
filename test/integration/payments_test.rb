require "test_helper"
require "openssl"

class PaymentsTest < ActionDispatch::IntegrationTest
  setup do
    @account = create_test_account(email: "payments@example.test")
    sign_in_as(@account)
  end

  test "public package page displays the Pix-only offerings" do
    get plans_path

    assert_response :success
    assert_select ".app-shell"
    assert_select "header.site-header", count: 0
    assert_select "[data-package-card='avulso_ai']"
    assert_select "[data-package-card='sem_ia']"
    assert_select "[data-package-card='com_ia']"
    assert_select "[data-package-card='topup_ai']"
    assert_select "[data-package-card='topup_jev']", count: 0
    assert_select "[data-package-card='topup_writing']", count: 0
    assert_select "h1", "Pacotes"
    assert_not_includes response.body, "Pagamento único por Pix."
    assert_select ".discount-badge", text: "50% de desconto", count: 3
    assert_includes response.body, "R$ 100,00"
    assert_includes response.body, "R$ 50,00"
    assert_includes response.body, "R$ 9,90"
    assert_includes response.body, "20 créditos de IA adicionais"
    assert_not_includes response.body, "Avaliações formativas não descontam créditos"
    assert_select "[data-package-card='sem_ia'][data-price-cents='5000'] [data-buy-package]", text: /R\$ 50,00/
    assert_equal 1, PaymentPackages::DEFINITIONS.values.count { |package| package[:kind] == :topup }
    assert_not_includes response.body, "Mercado Pago"
  end

  test "Essencial charges the approved promotional price" do
    gateway = fake_gateway
    with_stub(MercadoPagoGateway, :new, gateway) do
      post payments_path, params: {
        package_code: "sem_ia",
        quantity: 1,
        request_id: "c4f6b49b-8786-41f0-81d1-1b3c719d04a2"
      }, as: :json
    end

    assert_response :success
    assert_equal 5_000, PaymentOrder.sole.amount_cents
    assert_equal 0, PaymentOrder.sole.ai_credits
    assert_equal 0, PaymentOrder.sole.deepseek_credits
  end

  test "legacy evaluation top-up cannot be bought after evaluations stop consuming credits" do
    post payments_path, params: {
      package_code: "topup_jev",
      quantity: 1,
      request_id: "831deae8-6eaa-4ca6-9759-5dd2f1eabc95"
    }, as: :json

    assert_response :unprocessable_entity
    assert_equal "invalid_package", response.parsed_body["error"]
    assert_equal 0, PaymentOrder.count
  end

  test "legacy evaluation top-up preserves its paid value as AI credits" do
    @account.update!(
      plan_code: "sem_ia",
      project_limit: 14,
      ai_limit: 3,
      deepseek_limit: 6
    )
    order = PaymentService.new(gateway: fake_gateway).create_order!(
      account: @account,
      package_code: "topup_jev",
      quantity: 1,
      request_id: "cc27061a-9428-46c1-8cde-240cc66f8081"
    )
    payment = approved_payment(order).merge("transaction_amount" => 9.9)

    result = PaymentService.new.process_verified_payment(payment)
    duplicate_result = PaymentService.new.process_verified_payment(payment)

    assert_equal :approved, result
    assert_equal :duplicate, duplicate_result
    @account.reload
    assert_equal "sem_ia", @account.plan_code
    assert_equal 14, @account.project_limit
    assert_equal 3, @account.ai_limit
    assert_equal 26, @account.deepseek_limit
    assert_equal 20, PaymentGrant.sole.ai_credits
  end

  test "AI top-up adds only AI credits and preserves the account plan" do
    @account.update!(
      plan_code: "sem_ia",
      project_limit: 14,
      ai_limit: 3,
      deepseek_limit: 6
    )
    order = PaymentService.new(gateway: fake_gateway).create_order!(
      account: @account,
      package_code: "topup_ai",
      quantity: 1,
      request_id: "3878de49-2b9f-45e8-9d6d-b0a87613d6a8"
    )
    payment = approved_payment(order).merge("transaction_amount" => 9.9)
    service = PaymentService.new

    assert_equal :approved, service.process_verified_payment(payment)
    assert_equal :duplicate, service.process_verified_payment(payment)
    @account.reload
    assert_equal "sem_ia", @account.plan_code
    assert_equal 14, @account.project_limit
    assert_equal 3, @account.ai_limit
    assert_equal 26, @account.deepseek_limit
    assert_equal 20, PaymentGrant.sole.deepseek_credits
  end

  test "Mercado Pago gateway uses the official SDK with a stable idempotency key" do
    order = PaymentOrder.create!(
      account: @account,
      request_id: "c4f6b49b-8786-41f0-81d1-1b3c719d04a2",
      package_code: "com_ia",
      quantity: 1,
      project_credits: 7,
      ai_credits: 20,
      deepseek_credits: 10,
      amount_cents: 6_990
    )
    api = Object.new
    api.define_singleton_method(:create) do |payload, request_options:|
      @payload = payload
      @request_options = request_options
      Struct.new(:body) do
        def [](key)
          key == :response ? body : nil
        end

        def raise_for_status!
          true
        end
      end.new({
        "id" => "mp-payment-1",
        "point_of_interaction" => { "transaction_data" => { "qr_code_base64" => "cXJjb2Rl", "qr_code" => "pix-copy-code" } }
      })
    end
    sdk = Struct.new(:payment).new(api)

    with_env("MERCADOPAGO_WEBHOOK_URL", "https://example.test/webhooks/mercadopago") do
      result = MercadoPagoGateway.new(access_token: "test-token", sdk:).create_pix(order:, account: @account)

      assert_equal "mp-payment-1", result[:payment_id]
      assert_equal 69.9, api.instance_variable_get(:@payload)[:transaction_amount]
      assert_equal "https://example.test/webhooks/mercadopago", api.instance_variable_get(:@payload)[:notification_url]
      options = api.instance_variable_get(:@request_options)
      assert_equal order.idempotency_key, options.custom_headers["X-Idempotency-Key"]
      assert_equal 0, options.max_retries
    end
  end

  test "Mercado Pago gateway searches payments by the saved external reference" do
    api = Object.new
    api.define_singleton_method(:search) do |filters:, request_options:|
      @filters = filters
      @request_options = request_options
      Struct.new(:body) do
        def [](key)
          key == :response ? body : nil
        end

        def raise_for_status!
          true
        end
      end.new({ "results" => [ { "id" => "mp-payment-1" } ] })
    end
    sdk = Struct.new(:payment).new(api)

    payments = MercadoPagoGateway.new(access_token: "test-token", sdk:).search_payments(
      external_reference: "order-reference"
    )

    assert_equal [ { "id" => "mp-payment-1" } ], payments
    assert_equal({ external_reference: "order-reference", limit: 100 }, api.instance_variable_get(:@filters))
  end

  test "Mercado Pago webhook URL can be configured through encrypted credentials" do
    credentials = Object.new
    credentials.define_singleton_method(:dig) do |*keys|
      "https://example.test/webhooks/mercadopago" if keys == [ :mercadopago, :webhook_url ]
    end
    gateway = MercadoPagoGateway.new(access_token: "test-token", sdk: Object.new)

    with_stub(Rails.application, :credentials, credentials) do
      with_env("MERCADOPAGO_WEBHOOK_URL", nil) do
        with_env("BASE_URL", nil) do
          assert_equal "https://example.test/webhooks/mercadopago", gateway.send(:webhook_url)
        end
      end
    end
  end

  test "Mercado Pago credentials use the configured access token and webhook secret keys" do
    credentials = Object.new
    credentials.define_singleton_method(:dig) do |*keys|
      {
        [ :mercadopago, :access_token ] => "test-access-token",
        [ :mercadopago, :webhook_secret ] => "test-webhook-secret"
      }[keys]
    end

    with_stub(Rails.application, :credentials, credentials) do
      with_env("MERCADOPAGO_ACCESS_TOKEN", nil) do
        with_env("MERCADOPAGO_WEBHOOK_SECRET", nil) do
          assert_equal "test-access-token", PaymentSecrets.access_token
          assert_equal "test-webhook-secret", PaymentSecrets.webhook_secret
        end
      end
    end
  end

  test "Pix creation persists server-calculated amounts and reuses the idempotent order" do
    gateway = fake_gateway
    with_stub(MercadoPagoGateway, :new, gateway) do
      2.times do
        post payments_path, params: {
          package_code: "com_ia",
          quantity: 2,
          request_id: "c4f6b49b-8786-41f0-81d1-1b3c719d04a2"
        }, as: :json
        assert_response :success
      end
    end

    assert_equal 1, PaymentOrder.count
    order = PaymentOrder.sole
    assert_equal 13_980, order.amount_cents
    assert_equal 14, order.project_credits
    assert_equal 40, order.ai_credits
    assert_equal 20, order.deepseek_credits
    assert_equal "provider_created", order.status
    assert_equal "pix-copy-code", response.parsed_body["pix_copy_code"]
    assert_equal 1, gateway.create_calls
  end

  test "same idempotency key cannot be reused with different package details" do
    gateway = fake_gateway
    with_stub(MercadoPagoGateway, :new, gateway) do
      post payments_path, params: {
        package_code: "avulso_ai",
        quantity: 1,
        request_id: "c4f6b49b-8786-41f0-81d1-1b3c719d04a2"
      }, as: :json
      assert_response :success

      post payments_path, params: {
        package_code: "sem_ia",
        quantity: 1,
        request_id: "c4f6b49b-8786-41f0-81d1-1b3c719d04a2"
      }, as: :json
    end

    assert_response :conflict
    assert_equal "idempotency_conflict", response.parsed_body["error"]
    assert_equal 1, gateway.create_calls
  end

  test "signed approved webhook grants credits once" do
    order = create_order
    payment = approved_payment(order)
    gateway = fake_gateway(payment)
    with_stub(PaymentSecrets, :webhook_secret, "test-webhook-secret") do
      with_stub(MercadoPagoGateway, :new, gateway) do
        2.times { post_webhook(payment.fetch("id")) }
      end
    end

    assert_response :ok
    assert_equal 1, PaymentGrant.count
    assert_equal "approved", order.reload.status
    @account.reload
    assert_equal 107, @account.project_limit
    assert_equal 100, @account.ai_limit
    assert_equal 130, @account.deepseek_limit
  end

  test "webhook does not grant credits when provider amount differs" do
    order = create_order
    payment = approved_payment(order).merge("transaction_amount" => 1.0)
    gateway = fake_gateway(payment)
    with_stub(PaymentSecrets, :webhook_secret, "test-webhook-secret") do
      with_stub(MercadoPagoGateway, :new, gateway) do
        post_webhook(payment.fetch("id"))
      end
    end

    assert_response :ok
    assert_equal 0, PaymentGrant.count
    assert_equal "mismatch", order.reload.status
    assert_equal 100, @account.reload.project_limit
  end

  test "invalid webhook signature is rejected before fetching the provider payment" do
    order = create_order
    gateway = fake_gateway
    with_stub(PaymentSecrets, :webhook_secret, "test-webhook-secret") do
      with_stub(MercadoPagoGateway, :new, gateway) do
        post "/webhooks/mercadopago?data.id=mp-payment-1",
          params: { type: "payment", data: { id: "mp-payment-1" } },
          headers: { "X-Signature" => "ts=1,v1=invalid", "X-Request-Id" => "request-1" },
          as: :json
      end
    end

    assert_response :unauthorized
    assert_equal 0, gateway.fetch_calls
    assert_equal "provider_created", order.reload.status
  end

  private

  def create_order
    PaymentService.new(gateway: fake_gateway).create_order!(
      account: @account,
      package_code: "com_ia",
      quantity: 1,
      request_id: "ab51776b-92c7-4a2d-b04e-f498639c9cd8"
    )
  end

  def approved_payment(order)
    {
      "id" => "mp-payment-1",
      "external_reference" => order.external_reference,
      "status" => "approved",
      "currency_id" => "BRL",
      "transaction_amount" => 69.9
    }
  end

  test "webhook records an error code only for reconciliation mismatches" do
    order = create_order
    payment = approved_payment(order).merge("transaction_amount" => 1.0)
    gateway = fake_gateway(payment)
    with_stub(PaymentSecrets, :webhook_secret, "test-webhook-secret") do
      with_stub(MercadoPagoGateway, :new, gateway) do
        post_webhook(payment.fetch("id"))
      end
    end

    event = PaymentWebhookEvent.last
    assert_equal "mismatch", event.result
    assert_equal "mismatch", event.error_code
  end

  test "pending payments are recorded without an error code" do
    order = create_order
    payment = approved_payment(order).merge("status" => "pending")
    gateway = fake_gateway(payment)
    with_stub(PaymentSecrets, :webhook_secret, "test-webhook-secret") do
      with_stub(MercadoPagoGateway, :new, gateway) do
        post_webhook(payment.fetch("id"))
      end
    end

    event = PaymentWebhookEvent.last
    assert_equal "not_approved", event.result
    assert_nil event.error_code
  end

  def post_webhook(payment_id, path: "/webhooks/mercadopago")
    request_id = SecureRandom.uuid
    timestamp = Time.current.to_i
    manifest = "id:#{payment_id};request-id:#{request_id};ts:#{timestamp};"
    signature = OpenSSL::HMAC.hexdigest("SHA256", "test-webhook-secret", manifest)
    post "#{path}?data.id=#{payment_id}",
      params: { type: "payment", action: "payment.updated", data: { id: payment_id } },
      headers: { "X-Signature" => "ts=#{timestamp},v1=#{signature}", "X-Request-Id" => request_id },
      as: :json
  end

  def fake_gateway(payment = nil)
    gateway = Object.new
    gateway.instance_variable_set(:@create_calls, 0)
    gateway.instance_variable_set(:@fetch_calls, 0)
    gateway.define_singleton_method(:create_calls) { @create_calls }
    gateway.define_singleton_method(:fetch_calls) { @fetch_calls }
    gateway.define_singleton_method(:create_pix) do |order:, account:|
      @create_calls += 1
      { payment_id: "mp-payment-1", qr_base64: "cXJjb2Rl", copy_code: "pix-copy-code" }
    end
    gateway.define_singleton_method(:fetch_payment) do |_payment_id|
      @fetch_calls += 1
      payment
    end
    gateway
  end

  def with_stub(receiver, method_name, value)
    original = receiver.method(method_name)
    receiver.define_singleton_method(method_name) { |*args, **kwargs| value }
    yield
  ensure
    receiver.define_singleton_method(method_name, original)
  end

  def with_env(name, value)
    original = ENV[name]
    ENV[name] = value
    yield
  ensure
    ENV[name] = original
  end
end
