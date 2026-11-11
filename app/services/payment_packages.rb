class PaymentPackages
  MAX_QUANTITY = 99
  DEFINITIONS = {
    "avulso_ai" => {
      label: "Avulso com IA",
      price_cents: 1_200,
      project_credits: 1,
      ai_credits: 10,
      deepseek_credits: 5
    },
    "sem_ia" => {
      label: "Essencial",
      price_cents: 3_500,
      project_credits: 7,
      ai_credits: 0,
      deepseek_credits: 0
    },
    "com_ia" => {
      label: "Completo",
      price_cents: 6_990,
      project_credits: 7,
      ai_credits: 20,
      deepseek_credits: 10
    }
  }.freeze

  def self.find(package_code)
    DEFINITIONS[package_code.to_s]
  end

  def self.tier(package_code)
    { "livre" => 0, "avulso_ai" => 1, "sem_ia" => 2, "com_ia" => 3 }.fetch(package_code, 0)
  end
end
