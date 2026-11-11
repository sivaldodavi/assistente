namespace :payments do
  desc "Reconcile pending Mercado Pago orders"
  task reconcile: :environment do
    result = PaymentReconciliation.new.call
    puts result.inspect
    abort "Payment reconciliation failed for #{result[:errors]} order(s)" if result[:errors].positive?
  end
end
