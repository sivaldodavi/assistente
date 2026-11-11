require "test_helper"

class PaymentReconciliationTest < ActiveSupport::TestCase
  include AccountIntegrationTestHelper
  include ActiveSupport::Testing::TimeHelpers

  setup do
    @account = create_test_account(email: "reconciliation@example.test")
  end

  test "reconciles an approved payment found after the creation response was lost" do
    order = create_order
    gateway = FakeGateway.new(search_results: [ payment_for(order) ])

    travel 6.minutes do
      result = PaymentReconciliation.new(gateway:).call

      assert_equal 1, result[:reconciled]
      assert_equal "approved", order.reload.status
      assert_equal "mp-payment-1", order.provider_payment_id
      assert_equal 7, order.payment_grant.project_credits
      assert_equal [ order.external_reference ], gateway.search_references
      assert_equal 107, @account.reload.project_limit
    end
  end

  test "fetches an existing provider payment when a webhook was missed" do
    order = create_order(status: "provider_created", provider_payment_id: "mp-payment-1")
    gateway = FakeGateway.new(fetch_result: payment_for(order))

    travel 6.minutes do
      result = PaymentReconciliation.new(gateway:).call

      assert_equal 1, result[:reconciled]
      assert_equal 1, gateway.fetch_calls
      assert_equal "approved", order.reload.status
    end
  end

  test "keeps an order pending when the provider has no matching payment" do
    order = create_order(status: "reconciliation_required")
    gateway = FakeGateway.new(search_results: [])

    travel 6.minutes do
      result = PaymentReconciliation.new(gateway:).call

      assert_equal 1, result[:missing]
      assert_equal "reconciliation_required", order.reload.status
      assert_equal 0, PaymentGrant.count
    end
  end

  test "marks an order failed only after the provider reports a terminal status" do
    order = create_order(status: "provider_created", provider_payment_id: "mp-payment-1")
    gateway = FakeGateway.new(fetch_result: payment_for(order, status: "rejected"))

    travel 6.minutes do
      result = PaymentReconciliation.new(gateway:).call

      assert_equal 1, result[:failed]
      assert_equal "failed", order.reload.status
      assert_equal 0, PaymentGrant.count
    end
  end

  test "marks ambiguous provider search results as mismatch without granting credits" do
    order = create_order
    payment = payment_for(order)
    gateway = FakeGateway.new(search_results: [ payment, payment.merge("id" => "mp-payment-2") ])

    travel 6.minutes do
      result = PaymentReconciliation.new(gateway:).call

      assert_equal 1, result[:mismatch]
      assert_equal "mismatch", order.reload.status
      assert_equal 0, PaymentGrant.count
      assert_equal 100, @account.reload.project_limit
    end
  end

  test "does not reconcile a recently updated order" do
    order = create_order
    gateway = FakeGateway.new(search_results: [ payment_for(order) ])

    result = PaymentReconciliation.new(gateway:).call

    assert_equal 0, result[:checked]
    assert_equal "created", order.reload.status
  end

  test "moves attempted orders behind unprocessed orders in the bounded batch" do
    101.times { create_order }
    gateway = FakeGateway.new(search_results: [])

    travel 6.minutes do
      first_run = PaymentReconciliation.new(gateway:).call
      second_run = PaymentReconciliation.new(gateway:).call

      assert_equal 100, first_run[:checked]
      assert_equal 1, second_run[:checked]
    end
  end

  private

  def create_order(status: "created", provider_payment_id: nil)
    PaymentOrder.create!(
      account: @account,
      request_id: SecureRandom.uuid,
      package_code: "com_ia",
      quantity: 1,
      project_credits: 7,
      ai_credits: 20,
      deepseek_credits: 10,
      amount_cents: 6_990,
      status:,
      provider_payment_id:
    )
  end

  def payment_for(order, status: "approved")
    {
      "id" => "mp-payment-1",
      "external_reference" => order.external_reference,
      "status" => status,
      "currency_id" => "BRL",
      "transaction_amount" => 69.9
    }
  end

  class FakeGateway
    attr_reader :fetch_calls, :search_references

    def initialize(search_results: [], fetch_result: nil)
      @search_results = search_results
      @fetch_result = fetch_result
      @fetch_calls = 0
      @search_references = []
    end

    def search_payments(external_reference:)
      @search_references << external_reference
      @search_results
    end

    def fetch_payment(_payment_id)
      @fetch_calls += 1
      @fetch_result
    end
  end
end
