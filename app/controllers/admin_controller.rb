class AdminController < ApplicationController
  before_action :authenticate_account!
  before_action :require_admin!

  MAX_MANUAL_CREDITS = 1_000
  PAGE_SIZE = 50

  def index
    redirect_to admin_accounts_path
  end

  def dashboard
    @summary = {
      accounts: Account.count,
      projects: Project.count,
      pending_payments: PaymentOrder.where(status: %w[created provider_created reconciliation_required]).count,
      ai_requests: AIUsageReservation.where(status: "complete").count
    }
  end

  def accounts
    scope = Account.left_joins(:projects)
      .select("accounts.*, COUNT(projects.id) AS projects_count")
      .group("accounts.id")
      .order(created_at: :desc)
    if params[:email].present?
      needle = Account.sanitize_sql_like(params[:email].to_s.strip.downcase)
      scope = scope.where("lower(accounts.email) LIKE ?", "%#{needle}%")
    end
    @total = scope.unscope(:select, :group, :order).distinct.count(:id)
    @page = [ Integer(params[:page] || "1", 10), 1 ].max
    @accounts = scope.offset((@page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
  rescue ArgumentError
    @page = 1
    @total = 0
    @accounts = Account.none
  end

  def update_plan
    account = Account.find(params[:id])
    plan_code = params[:plan_code].to_s
    return redirect_to admin_accounts_path, alert: "Pacote inválido." unless (PaymentPackages::PLAN_CODES + [ "livre" ]).include?(plan_code)

    account.with_lock do
      old_plan = account.plan_code
      account.update!(plan_code:)
      audit!(account, "plan", before: { plan_code: old_plan }, after: { plan_code: })
    end
    redirect_to admin_accounts_path, notice: "Pacote atualizado."
  end

  def update_credits
    account = Account.find(params[:id])
    remaining = {
      project_limit: parse_credits(params.dig(:credits, :projects)),
      ai_limit: parse_credits(params.dig(:credits, :ai)),
      deepseek_limit: parse_credits(params.dig(:credits, :deepseek))
    }
    exceeded_limit = false
    account.with_lock do
      before = {
        projects: account.project_credits_remaining,
        ai: [ account.ai_limit - account.ai_used, 0 ].max,
        deepseek: account.deepseek_credits_remaining
      }
      limits = {
        project_limit: account.project_used + remaining[:project_limit],
        ai_limit: account.ai_used + remaining[:ai_limit],
        deepseek_limit: account.deepseek_used + remaining[:deepseek_limit]
      }
      if limits.values.any? { |limit| limit > MAX_MANUAL_CREDITS }
        exceeded_limit = true
      else
        account.update!(limits)
        audit!(account, "credits", before:, after: remaining)
      end
    end
    return redirect_to admin_accounts_path, alert: "O saldo total não pode ultrapassar #{MAX_MANUAL_CREDITS} créditos por categoria." if exceeded_limit

    redirect_to admin_accounts_path, notice: "Créditos atualizados."
  rescue ArgumentError, TypeError
    redirect_to admin_accounts_path, alert: "Informe saldos inteiros entre 0 e #{MAX_MANUAL_CREDITS}."
  end

  def update_block
    account = Account.find(params[:id])
    blocked = case params[:blocked]
    when "1" then true
    when "0" then false
    else return redirect_to admin_accounts_path, alert: "Estado de bloqueio inválido."
    end
    if blocked && (account.id == current_account.id || account.admin?)
      return redirect_to admin_accounts_path, alert: "Não é permitido bloquear uma conta administrativa."
    end

    account.with_lock do
      previous = account.is_blocked?
      account.update!(is_blocked: blocked)
      audit!(account, blocked ? "block" : "unblock", before: { blocked: previous }, after: { blocked: })
    end
    redirect_to admin_accounts_path, notice: blocked ? "Conta bloqueada." : "Conta desbloqueada."
  end

  def audit
    @events = AdminAuditEvent.includes(:actor_account, :target_account)
      .order(created_at: :desc)
      .limit(PAGE_SIZE)
  end

  def usage
    render json: {
      accounts: Account.count,
      projects: Project.count,
      ai_by_provider: ProviderUsage.group(:provider).count,
      payments_by_status: PaymentOrder.group(:status).count
    }
  end

  def health
    ActiveRecord::Base.connection.select_value("SELECT 1")
    render json: { ok: true, database: "ok", checked_at: Time.current.iso8601 }
  end

  private

  def require_admin!
    head :forbidden unless current_account&.admin?
  end

  def parse_credits(value)
    text = value.to_s
    raise ArgumentError unless text.match?(/\A\d{1,4}\z/)

    Integer(text, 10).tap do |number|
      raise ArgumentError unless number.between?(0, MAX_MANUAL_CREDITS)
    end
  end

  def audit!(account, action, before:, after:)
    AdminAuditEvent.create!(
      actor_account: current_account,
      target_account: account,
      action:,
      details: { before:, after: }
    )
  end
end
