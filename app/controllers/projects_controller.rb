class ProjectsController < ApplicationController
  before_action :authenticate_account!, except: :index
  before_action :set_project, only: %i[show update destroy paper_mode export]

  def index
    @projects = current_account ? current_account.projects.order(updated_at: :desc) : Project.none
    @upcoming_schedule = AcademicSchedule.upcoming(@projects)
  end

  def new
    @project = current_account.projects.new
  end

  def create
    project_type = params.dig(:project, :project_type).to_s
    unless AcademicWorkflow.editable_types.include?(project_type)
      @project = current_account.projects.new
      @project.errors.add(:project_type, "selecione Case ou Projeto de Paper")
      return render :new, status: :unprocessable_entity
    end

    @project = current_account.projects.new(project_type:)
    current_account.with_lock do
      if !current_account.admin? && current_account.project_used >= current_account.project_limit
        @project.errors.add(:base, "Você não tem créditos de projeto disponíveis. Escolha um pacote para continuar.")
      elsif @project.save
        current_account.update!(project_used: current_account.project_used + 1) unless current_account.admin?
      end
    end
    if @project.persisted?
      redirect_to project_path(@project, stage: @project.current_stage), notice: "Projeto criado."
    else
      render :new, status: :unprocessable_entity
    end
  end

  def show
    prepare_editor_state
  end

  def update
    persist_project_changes
  end

  def paper_mode
    return head :conflict unless @project.project_type == "paper_project"

    persist_project_changes(convert_to_final: true)
  end

  def export
    phase = params[:phase].presence || "report"
    if @project.project_type == "case" && !%w[report debate dissertation].include?(phase)
      return head :bad_request
    end

    sources = current_account.sources.where(public_id: @project.source_ids).map(&:attributes)
    case params[:format].presence || "html"
    when "html"
      html = DocumentExport.build_project_html(@project, sources:, phase:)
      send_data html, type: "text/html; charset=utf-8", disposition: "inline"
    when "pdf"
      pdf = DocumentExport.render_pdf(@project, sources:, phase:)
      send_data pdf, type: "application/pdf", disposition: "attachment", filename: "assistente-academico.pdf"
    else
      head :bad_request
    end
  rescue DocumentExport::ExportError => error
    render plain: error.message, status: :service_unavailable
  end

  def destroy
    @project.destroy!
    redirect_to projects_path, notice: "Projeto removido.", status: :see_other
  end

  private

  def set_project
    @project = current_account.projects.find(params[:id])
  end

  def persist_project_changes(convert_to_final: false)
    input = params.require(:project)
    submitted_lock_version = Integer(input[:lock_version], 10)
    submitted_stage_id = input[:current_stage].presence || @project.current_stage
    active_section = @project.section_for(submitted_stage_id)

    @project.lock_version = submitted_lock_version
    @project.fields = AcademicWorkflow.normalize_fields(
      @project.project_type,
      @project.fields.merge(hash_parameter(input[:fields]))
    )
    update_stage_checks(active_section, hash_parameter(input[:checks]))
    @project.criteria = AcademicWorkflow.normalize_criteria(hash_parameter(input[:criteria])) if input.key?(:criteria)
    @project.development_sections = AcademicWorkflow.normalize_development_sections(hash_parameter(input[:development_sections])) if input.key?(:development_sections)
    if input.key?(:source_ids)
      requested_ids = AcademicWorkflow.normalize_source_ids(input[:source_ids])
      @project.source_ids = current_account.sources.where(public_id: requested_ids).pluck(:public_id)
    end
    @project.schedule = AcademicSchedule.normalize_schedule(
      hash_parameter(input[:schedule]),
      project_type: @project.project_type,
      fallback_date: @project.fields["deliveryDate"]
    ) if input.key?(:schedule)
    update_delivery(active_section) if params[:mark_delivered] == "1"

    target_type = convert_to_final ? "paper_final" : @project.project_type
    target_stage = params[:go_to_stage].presence || submitted_stage_id
    @project.project_type = target_type
    @project.current_stage = valid_stage_id?(target_type, target_stage) ? target_stage : AcademicWorkflow.first_stage_id(target_type)
    @project.save!
    @project.record_revision!

    notice = convert_to_final ? "Projeto convertido em Paper Final." : "Alterações salvas."
    redirect_to project_path(@project, stage: @project.current_stage), notice:
  rescue ActiveRecord::StaleObjectError
    @project.reload
    prepare_editor_state
    flash.now[:alert] = "Este projeto mudou em outra sessão. Confira a versão atual antes de salvar novamente."
    render :show, status: :conflict
  rescue ArgumentError, TypeError
    head :bad_request
  rescue ActiveRecord::RecordInvalid
    prepare_editor_state
    render :show, status: :unprocessable_entity
  end

  def update_stage_checks(section, submitted_checks)
    checks = @project.checks.dup
    section.fetch("checks", []).each do |key, _label|
      checks[key] = submitted_checks[key].to_s == "1" || submitted_checks[key] == true
    end
    @project.checks = AcademicWorkflow.normalize_checks(@project.project_type, checks)
  end

  def update_delivery(section)
    key = @project.delivery_key(section)
    @project.deliveries = @project.deliveries.merge(
      key => { "delivered" => true, "at" => Time.current.to_i }
    )
  end

  def valid_stage_id?(project_type, stage_id)
    AcademicWorkflow.sections(project_type).any? { |section| section["id"] == stage_id.to_s }
  end

  def hash_parameter(value)
    return {} unless value.respond_to?(:to_unsafe_h)

    value.to_unsafe_h
  end

  def prepare_editor_state
    @stages = @project.sections
    @stage = @project.section_for(params[:stage].presence || @project.current_stage)
    @stage_index = @project.stage_index(@stage["id"])
    @previous_stage = @stages[@stage_index - 1] if @stage_index.positive?
    @next_stage = @stages[@stage_index + 1]
    @progress = @project.progress(@stage["phase"])
    @review_summary = @project.review_summary(@stage["phase"])
    @schedule_summary = @project.schedule_summary
    @sources = current_account.sources.order(:title)
  end
end
