class Account < ApplicationRecord
  TERMS_VERSION = "2026-10"
  PROFILE_TEXT_LIMIT = 160
  PROFILE_LIST_LIMIT = 40
  PROFILE_PERIODS = (1..10).map(&:to_s).freeze
  PROFILE_SHIFTS = %w[matutino noturno].freeze

  has_many :projects, dependent: :destroy, inverse_of: :account
  has_many :sources, dependent: :destroy, inverse_of: :account
  has_many :ai_usage_reservations, dependent: :destroy
  has_many :provider_usages, dependent: :destroy
  has_many :payment_orders, dependent: :destroy
  has_many :payment_grants, dependent: :destroy

  before_validation :normalize_identity

  validates :email, presence: true, length: { maximum: 240 }, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :email, uniqueness: { case_sensitive: false }
  validates :name, length: { maximum: 160 }
  validates :google_sub, length: { maximum: 255 }, allow_blank: true
  validates :google_sub, uniqueness: true, allow_blank: true
  validates :role, inclusion: { in: %w[user admin] }
  validates :plan_code, inclusion: { in: PaymentPackages::DEFINITIONS.keys + [ "livre" ] }
  validates :project_limit, :project_used, :deepseek_limit, :deepseek_used,
    numericality: { only_integer: true, greater_than_or_equal_to: 0 }

  def deepseek_credits_remaining
    [ deepseek_limit - deepseek_used, 0 ].max
  end

  def admin?
    configured_admins = Array(Rails.application.config.x.admin_emails).map(&:downcase)
    role == "admin" || configured_admins.include?(email)
  end

  def project_credits_remaining
    [ project_limit - project_used, 0 ].max
  end

  def consume_project_credit!
    with_lock do
      raise ActiveRecord::RecordInvalid, self if !admin? && project_used >= project_limit

      update!(project_used: project_used + 1) unless admin?
    end
  end

  def update_profile!(profile:, name:)
    update!(name: name.to_s.strip.first(PROFILE_TEXT_LIMIT), profile: normalize_profile(profile))
  end

  def accept_terms!(accept:, ai_consent:)
    raise ArgumentError, "os termos precisam ser aceitos" unless accept

    update!(
      terms_accepted: true,
      terms_version: TERMS_VERSION,
      terms_accepted_at: Time.current,
      ai_consent:
    )
  end

  private

  def normalize_identity
    self.email = email.to_s.strip.downcase
    self.name = name.to_s.strip
    self.google_sub = google_sub.to_s.strip.presence
    self.profile = profile.is_a?(Hash) ? profile : {}
  end

  def normalize_profile(profile)
    source = profile.respond_to?(:to_h) ? profile.to_h : {}
    text = %w[city course].index_with do |key|
      source[key].to_s.strip.first(PROFILE_TEXT_LIMIT)
    end
    text["period"] = PROFILE_PERIODS.include?(source["period"].to_s) ? source["period"].to_s : ""
    text["shift"] = PROFILE_SHIFTS.include?(source["shift"].to_s) ? source["shift"].to_s : ""
    lists = {
      "disciplines" => normalized_profile_list(source["disciplines"]),
      "teachers" => normalized_profile_list(source["teachers"])
    }
    text.merge(lists)
  end

  def normalized_profile_list(values)
    Array(values).filter_map do |value|
      value.to_s.strip.first(PROFILE_TEXT_LIMIT).presence
    end.uniq.first(PROFILE_LIST_LIMIT)
  end
end
