class PaymentPackages
  MAX_QUANTITY = 99
  PLAN_CODES = %w[avulso_ai sem_ia com_ia].freeze
  DEFINITIONS = {
    "avulso_ai" => {
      label: "Avulso com IA",
      price_cents: 1_200,
      regular_price_cents: 2_400,
      project_credits: 1,
      ai_credits: 10,
      deepseek_credits: 5
    },
    "sem_ia" => {
      label: "Essencial",
      price_cents: 5_000,
      regular_price_cents: 10_000,
      project_credits: 7,
      ai_credits: 0,
      deepseek_credits: 0
    },
    "com_ia" => {
      label: "Completo",
      price_cents: 6_990,
      regular_price_cents: 13_980,
      project_credits: 7,
      ai_credits: 20,
      deepseek_credits: 10
    },
    "topup_jev" => {
      label: "Recarga de JEV",
      description: "20 avaliações formativas adicionais",
      price_cents: 990,
      project_credits: 0,
      ai_credits: 20,
      deepseek_credits: 0,
      kind: :topup
    },
    "topup_writing" => {
      label: "Recarga de IA",
      description: "20 orientações de escrita adicionais",
      price_cents: 990,
      project_credits: 0,
      ai_credits: 0,
      deepseek_credits: 20,
      kind: :topup
    }
  }.freeze

  def self.find(package_code)
    DEFINITIONS[package_code.to_s]
  end

  def self.tier(package_code)
    { "livre" => 0, "avulso_ai" => 1, "sem_ia" => 2, "com_ia" => 3 }.fetch(package_code.to_s, 0)
  end

  def self.discount_percent(definition)
    regular_price = definition.fetch(:regular_price_cents)
    price = definition.fetch(:price_cents)
    ((regular_price - price) * 100.0 / regular_price).round
  end
end
